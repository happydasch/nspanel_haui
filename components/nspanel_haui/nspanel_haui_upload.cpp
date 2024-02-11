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
  Uploader for NSPanel HAUI (renamed nextion upload)
  */

  void NSPanelHAUI::upload_tft() {

    if (this->is_updating_) {
      ESP_LOGD(TAG, "Currently updating");
      return;
    }

    if (!network::is_connected()) {
      ESP_LOGD(TAG, "Network is not connected");
      return;
    }

    this->is_updating_ = true;
    HTTPClient http;
    bool begin_status = false;
    begin_status = http.begin(this->tft_url_.c_str());

    if (!begin_status) {
      this->is_updating_ = false;
      ESP_LOGD(TAG, "Connection failed");
      ExternalRAMAllocator<uint8_t> allocator(ExternalRAMAllocator<uint8_t>::ALLOW_FAILURE);
      allocator.deallocate(this->transfer_buffer_, this->transfer_buffer_size_);
      return;
    } else {
      ESP_LOGD(TAG, "Connected");
    }

    http.addHeader("Range", "bytes=0-255");
    const char *header_names[] = {"Content-Range"};
    http.collectHeaders(header_names, 1);
    ESP_LOGD(TAG, "Requesting URL: %s", this->tft_url_.c_str());

    http.setReuse(true);
    // try up to 5 times. DNS sometimes needs a second try or so
    int tries = 1;
    int code = http.GET();
    delay(100);  // NOLINT

    App.feed_wdt();
    while (code != 200 && code != 206 && tries <= 5) {
      ESP_LOGW(TAG, "HTTP Request failed; URL: %s; Error: %s, retrying (%d/5)", this->tft_url_.c_str(),
              HTTPClient::errorToString(code).c_str(), tries);
      delay(250);  // NOLINT
      App.feed_wdt();
      code = http.GET();
      ++tries;
    }

    if ((code != 200 && code != 206) || tries > 5) {
      return this->upload_end_(false);
    }

    String content_range_string = http.header("Content-Range");
    content_range_string.remove(0, 12);
    this->content_length_ = content_range_string.toInt();
    this->tft_size_ = content_length_;
    http.end();

    if (this->content_length_ < 4096) {
      ESP_LOGE(TAG, "Failed to get file size");
      return this->upload_end_(false);
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

    // Nextion display will, if it's ready to accept data, send a 0x05 byte.
    ESP_LOGD(TAG, "Upgrade response is %s %zu", response.c_str(), response.length());
    for (size_t i = 0; i < response.length(); i++) {
      ESP_LOGD(TAG, "Available %d : 0x%02X", i, response[i]);
    }
    if (response.find(0x05) != std::string::npos) {
      ESP_LOGD(TAG, "preparation for tft update done");
    } else {
      ESP_LOGD(TAG, "preparation for tft update failed %d \"%s\"", response[0], response.c_str());
      return this->upload_end_(false);
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
          return this->upload_end_(false);
      }
      this->transfer_buffer_size_ = chunk_size;
    }

    ESP_LOGD(TAG, "Updating tft from \"%s\" with a file size of %d using %zu chunksize, Heap Size %d",
            this->tft_url_.c_str(), this->content_length_, this->transfer_buffer_size_, ESP.getFreeHeap());
    int result = 0;
    while (this->content_length_ > 0) {
      result = this->upload_by_chunks_(&http, result);
      if (result < 0) {
        ESP_LOGD(TAG, "Error updating Nextion!");
        return this->upload_end_(false);
      }
      App.feed_wdt();
      // NOLINTNEXTLINE(readability-static-accessed-through-instance)
      ESP_LOGD(TAG, "Heap Size %d, Bytes left %d", ESP.getFreeHeap(), this->content_length_);
    }

    ESP_LOGD(TAG, "Successfully updated NSPanel HAUI!");
    return this->upload_end_(true);
  }

  int NSPanelHAUI::upload_by_chunks_(HTTPClient *http, int range_start) {
    int range_end = 0;
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
      begin_status = http->begin(this->tft_url_.c_str());

      ++tries;
      if (!begin_status) {
        ESP_LOGD(TAG, "upload_by_chunks_: connection failed");
        continue;
      }

      http->addHeader("Range", range_header);
      code = http->GET();
      if (code == 200 || code == 206) {
        break;
      }
      ESP_LOGW(TAG, "HTTP Request failed; URL: %s; Status Code: %d, retries(%d/5)",
        this->tft_url_.c_str(), code, tries);
      http->end();
      App.feed_wdt();
      delay(500);  // NOLINT
    }

    if (tries > 5) {
      return -1;
    }

    std::string recv_string;
    size_t size = 0;
    int fetched = 0;
    int range = range_end - range_start;

    while (fetched < range) {
      size = http->getStreamPtr()->available();
      if (!size) {
        App.feed_wdt();
        delay(0);
        continue;
      }
      int c = http->getStreamPtr()->readBytes(
          &this->transfer_buffer_[fetched], ((size > this->transfer_buffer_size_) ? this->transfer_buffer_size_ : size));
      fetched += c;
    }
    http->end();
    ESP_LOGD(TAG, "Fetched %d of %d bytes", fetched, this->content_length_);

    // upload fetched segments to the display in 4KB chunks
    int write_len;
    for (int i = 0; i < range; i += 4096) {
      App.feed_wdt();
      write_len = this->content_length_ < 4096 ? this->content_length_ : 4096;
      this->write_array(&this->transfer_buffer_[i], write_len);
      this->content_length_ -= write_len;
      ESP_LOGD(TAG, "Uploaded %0.2f %%; %d bytes remaining",
                100.0 * (this->tft_size_ - this->content_length_) / this->tft_size_, this->content_length_);

      if (!this->upload_first_chunk_sent_) {
        this->upload_first_chunk_sent_ = true;
        delay(500);  // NOLINT
      }

      this->recv_response_(recv_string, 4096, true, true);

      if (recv_string[0] != 0x05) {  // 0x05 == "ok"
        ESP_LOGD(TAG, "recv_string [%s]",
                  format_hex_pretty(reinterpret_cast<const uint8_t *>(recv_string.data()), recv_string.size()).c_str());
      }

      // handle partial upload request
      if (recv_string[0] == 0x08 && recv_string.size() == 5) {
        uint32_t result = 0;
        for (int j = 0; j < 4; ++j) {
          result += static_cast<uint8_t>(recv_string[j + 1]) << (8 * j);
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

  void NSPanelHAUI::upload_end_(bool successful) {
    this->is_updating_ = false;
    ExternalRAMAllocator<uint8_t> allocator(ExternalRAMAllocator<uint8_t>::ALLOW_FAILURE);
    allocator.deallocate(this->transfer_buffer_, this->transfer_buffer_size_);
    this->hard_reset();
    ESP_LOGD(TAG, "Restarting Nextion");
    this->soft_reset();
    if (successful) {
      delay(1500);  // NOLINT
      ESP_LOGD(TAG, "Restarting ESPHome");
      ESP.restart();  // NOLINT(readability-static-accessed-through-instance)
    }
  }

}  // namespace nspanel_haui
}  // namespace esphome
