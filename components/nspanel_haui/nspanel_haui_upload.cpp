#include "esphome/core/application.h"
#include "esphome/core/defines.h"
#include "esphome/core/util.h"
#include "esphome/core/log.h"
#include "esphome/components/network/util.h"

#include "nspanel_haui.h"
#include <esp_heap_caps.h>

namespace esphome {
namespace nspanel_haui {

  static const char* TAG = "nspanel_haui_upload";

  // Guide: https://unofficialnextion.com/t/nextion-upload-protocol-v1-2-the-fast-one/1044/2
  // https://github.com/espressif/arduino-esp32/blob/master/libraries/HTTPClient/src/HTTPClient.h
  // https://github.com/UNUF/nxt-doc/blob/main/Protocols/Upload%20Protocol%20v1.2.md
  // https://nextion.tech/instruction-set/

  /*
  Uploader for NSPanel HAUI

  currently the code works as follows:

    1. start uploading by calling upload_tft, the url set by setURL will be used
    2. resolve url (this is messy, due to HTTPClient and mixed protocols)
    3. send command to upload
    4. start uploading upload_by_chunks_ by sending chunks of data, see upload protocol v1.2 description for response codes and meaning
    5. end uploading by calling upload_end_
       when done, send command to reset device

  TODO this needs to be refactored to make the code more pleasant
  TODO get the HTTPClient to work with reuse connection (this will most likely be fixed in HTTPClient at some point, see github esp32 HTTPClient issues for more info)
  */

  void NSPanelHAUI::upload_tft() {

    if (this->is_updating_) {
      ESP_LOGD(TAG, "Currently updating");
      return;
    }

    if (!network::is_connected()) {
      ESP_LOGD(TAG, "network is not connected");
      return;
    }

    this->is_updating_ = true;
    // make sure to exit active parsing mode
    this->send_command_("DRAKJHSUYDGBNCJHGJKSHBDN");
    const char *header_names[] = {"Content-Range", "Content-Length"};
    int tries = 1;
    int code;
    bool begin_status;
    String location = this->tft_url_.c_str();
    while (tries <= 5) {
      // always create a new instance when trying to connect
      // because when forwarding from http -> https the connection
      // will not work (there are bugs related to WiFiClientSecure it seems)
      HTTPClient http;
      //http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
      http.collectHeaders(header_names, 2);
      http.setReuse(false);
      ESP_LOGD(TAG, "Connecting URL: %s", location.c_str());
      begin_status = http.begin(location.c_str());
      if (!begin_status) {
        ESP_LOGD(TAG, "Connecting: connection failed");
        break;
      }
      ESP_LOGD(TAG, "Requesting URL: %s", location.c_str());
      code = http.GET();
      delay(100);  // NOLINT
      if (code == 200) {
        ESP_LOGW(TAG, "HTTP Request successful (%d) %s", code, location.c_str());
        String content_length_string = http.header("Content-Length");
        ESP_LOGD(TAG, "Content Length String: %s", content_length_string.c_str());
        this->content_length_ = content_length_string.toInt();
        this->tft_size_ = content_length_;
        http.end();
        break;
      } else if (code == 301 || code == 302) {
        if (http.getLocation().length() > 0) {
          ESP_LOGW(TAG, "Redirecting %s->%s (%d)", location.c_str(), http.getLocation().c_str(), code);
          location = http.getLocation();
        } else {
          ESP_LOGW(TAG, "Not Redirecting %s, %s (%d)", location.c_str(), http.getLocation().c_str(), code);
        }
      } else if (code > 0) {
        ESP_LOGW(TAG, "HTTP Request failed; URL (%d) retrying (%d/5)", code, tries);
      } else {
        ESP_LOGW(TAG, "HTTP Request failed; URL (%d): %s retrying (%d/5)", code, http.errorToString(code).c_str(), tries);
      }
      App.feed_wdt();
      ++tries;
    }
    if ((code != 200 && code != 206) || tries > 5) {
      ESP_LOGW(TAG, "HTTP Request failed; URL (%d): %d", code, tries);
      return this->upload_end_();
    } else if (this->content_length_ < 4096) {
      ESP_LOGE(TAG, "Failed to get file size");
      return this->upload_end_();
    }

    ESP_LOGW(TAG, "Updating NSPanel HAUI %s...", this->device_model_.c_str());
    // Nextion will ignore the update command if it is sleeping
    this->send_command_("sleep=0", true);
    this->send_command_("dim=100", true);
    delay(250);  // NOLINT
    App.feed_wdt();
    char command[128];
    // Tells the Nextion the content length of the tft file and baud rate it will be sent at
    // Once the Nextion accepts the command it will wait until the file is successfully uploaded
    // If it fails for any reason a power cycle of the display will be needed
    sprintf(command, "whmi-wris %d,%d,1", this->content_length_, this->parent_->get_baud_rate());
    // Clear serial receive buffer
    uint8_t d;
    while (this->available()) {
      this->read_byte(&d);
    };
    App.feed_wdt();

    std::string response;
    this->send_command_(command, false);
    ESP_LOGD(TAG, "Waiting for upgrade response");
    this->recv_response_(response, 2000, true, true);  // This can take some time to return
    App.feed_wdt();

    // Nextion display will, if it's ready to accept data, send a 0x05 byte.
    ESP_LOGD(TAG, "Upgrade response is %s %zu", response.c_str(), response.length());
    for (size_t i = 0; i < response.length(); i++) {
      ESP_LOGD(TAG, "Available %d : 0x%02X", i, response[i]);
    }
    if (response.find(0x05) != std::string::npos) {
      ESP_LOGD(TAG, "preparation for tft update done");
    } else {
      ESP_LOGD(TAG, "preparation for tft update failed %d \"%s\"", response[0], response.c_str());
      //return this->upload_end_();
    }

    // Nextion wants 4096 bytes at a time. Make chunk_size a multiple of 4096
    uint32_t chunk_size = 8192;
    if (heap_caps_get_free_size(MALLOC_CAP_SPIRAM) > 0) {
      chunk_size = this->content_length_;
    } else {
      if (ESP.getFreeHeap() > 40960) {  // 32K to keep on hand
        int chunk = int((ESP.getFreeHeap() - 32768) / 4096);
        chunk_size = chunk * 4096;
        chunk_size = chunk_size > 65536 ? 65536 : chunk_size;
      } else if (ESP.getFreeHeap() < 10240) {
        chunk_size = 4096;
      }
    }

    if (this->transfer_buffer_ == nullptr) {
      ExternalRAMAllocator<uint8_t> allocator(ExternalRAMAllocator<uint8_t>::ALLOW_FAILURE);
      ESP_LOGD(TAG, "Allocating buffer size %d, Heap size is %u", chunk_size, ESP.getFreeHeap());
      this->transfer_buffer_ = allocator.allocate(chunk_size);
      if (this->transfer_buffer_ == nullptr) {  // Try a smaller size
        ESP_LOGD(TAG, "Could not allocate buffer size: %d trying 4096 instead", chunk_size);
        chunk_size = 4096;
        ESP_LOGD(TAG, "Allocating %d buffer", chunk_size);
        this->transfer_buffer_ = allocator.allocate(chunk_size);
        if (!this->transfer_buffer_)
          return this->upload_end_();
      }
      this->transfer_buffer_size_ = chunk_size;
    }

    ESP_LOGD(TAG, "Updating tft from \"%s\" with a file size of %d using %zu chunksize, Heap Size %d",
            location.c_str(), this->content_length_, this->transfer_buffer_size_, ESP.getFreeHeap());
    int result = 0;
    HTTPClient http;
    http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
    http.setReuse(true);
    http.collectHeaders(header_names, 2);
    while (this->content_length_ > 0) {
      result = this->upload_by_chunks_(location, result);
      if (result < 0) {
        ESP_LOGD(TAG, "Error updating NSPanel HAUI!");
        return this->upload_end_();
      }
      App.feed_wdt();
      ESP_LOGD(TAG, "Heap Size %d, Bytes left %d", ESP.getFreeHeap(), this->content_length_);
    }

    ESP_LOGD(TAG, "Successfully updated NSPanel HAUI!");
    this->upload_end_();
  }

  int NSPanelHAUI::upload_by_chunks_(String location, int range_start) {
    int range_end = 0;
    const char *header_names[] = {"Content-Range", "Content-Length"};
    HTTPClient http;
    http.collectHeaders(header_names, 2);
    http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
    if (range_start == 0 && this->transfer_buffer_size_ > 16384) {  // Start small at the first run in case of a big skip
      range_end = 16384 - 1;
    } else {
      range_end = range_start + this->transfer_buffer_size_ - 1;
    }

    if (range_end > this->tft_size_)
      range_end = this->tft_size_;

    char range_header[64];
    sprintf(range_header, "bytes=%d-%d", range_start, range_end);

    ESP_LOGD(TAG, "Requesting range: %s", range_header);

    int tries = 1;
    int code = 0;
    bool begin_status = false;
    while (tries <= 5) {
      ESP_LOGD(TAG, "upload_by_chunks_: trying to connect %s", location.c_str());
      begin_status = http.begin(location.c_str());
      ++tries;
      if (!begin_status) {
        ESP_LOGD(TAG, "upload_by_chunks_: connection failed");
        continue;
      }

      http.addHeader("Range", range_header);
      code = http.GET();
      if (code == 200 || code == 206) {
        break;
      }
      ESP_LOGW(TAG, "HTTP Request failed; URL: %s; Status Code: %d, retries(%d/5)",
        code, location.c_str(), code, tries);
      http.end();
      App.feed_wdt();
      delay(500);  // NOLINT
    }

    if (tries > 5) {
      return -1;
    }

    std::string recv_string;
    size_t size = 0;
    int sent = 0;
    int range = range_end - range_start;

    while (sent < range) {
      size = http.getStreamPtr()->available();
      if (!size) {
        App.feed_wdt();
        delay(0);
        continue;
      }
      int c = http.getStreamPtr()->readBytes(
          &this->transfer_buffer_[sent], ((size > this->transfer_buffer_size_) ? this->transfer_buffer_size_ : size));
      sent += c;
    }
    http.end();
    ESP_LOGD(TAG, "this->content_length_ %d sent %d", this->content_length_, sent);
    for (int i = 0; i < range; i += 4096) {
      this->write_array(&this->transfer_buffer_[i], 4096);
      this->content_length_ -= 4096;
      ESP_LOGD(TAG, "this->content_length_ %d range %d (%d-%d)", this->content_length_, range,
              range_start, range_end);

      if (!this->upload_first_chunk_sent_) {
        this->upload_first_chunk_sent_ = true;
        delay(500);  // NOLINT
        App.feed_wdt();
      }

      this->recv_response_(recv_string, 2048, true, true);
      if (recv_string[0] == 0x08) {
        uint32_t result = 0;
        for (int i = 0; i < 4; ++i) {
          result += static_cast<uint8_t>(recv_string[i + 1]) << (8 * i);
        }
        if (result > 0) {
          ESP_LOGD(TAG, "Nextion reported new range %d", result);
          this->content_length_ = this->tft_size_ - result;
          return result;
        }
      }
      recv_string.clear();
    }
    return range_end + 1;
  }

  void NSPanelHAUI::upload_end_() {
    this->is_updating_ = false;
    ExternalRAMAllocator<uint8_t> allocator(ExternalRAMAllocator<uint8_t>::ALLOW_FAILURE);
    allocator.deallocate(this->transfer_buffer_, this->transfer_buffer_size_);
    this->hard_reset();
  }

}  // namespace nspanel_haui
}  // namespace esphome
