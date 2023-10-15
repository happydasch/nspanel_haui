#include "nspanel_haui.h"
#include "esphome/core/util.h"
#include "esphome/core/log.h"
#include "esphome/core/application.h"

namespace esphome {
namespace nspanel_haui {


  static const char* TAG = "nspanel_haui";

  void NSPanelHAUI::setup() {
    ESP_LOGD(TAG, "Setting up NSPanel HAUI...");
    // Wakeup and restart the display
    this->send_command_("bkcmd=0");
    this->send_command_("sleep=0");
    this->reset_();
  }

  void NSPanelHAUI::dump_config() {
    ESP_LOGCONFIG(TAG, "NSPanel HAUI - Nextion:");
    ESP_LOGCONFIG(TAG, "  Device Model:     %s", this->device_model_.c_str());
    ESP_LOGCONFIG(TAG, "  Firmware Version: %s", this->firmware_version_.c_str());
    ESP_LOGCONFIG(TAG, "  Serial Number:    %s", this->serial_number_.c_str());
    ESP_LOGCONFIG(TAG, "  Flash Size:       %s", this->flash_size_.c_str());
  }

  void NSPanelHAUI::update() {
    if (this->writer_.has_value()) {
      (*this->writer_)(*this);
    }
  }

  float NSPanelHAUI::get_setup_priority() const {
      return setup_priority::HARDWARE;
  }

  void NSPanelHAUI::set_writer(const haui_writer_t &writer) {
    this->writer_ = writer;
  }

  void NSPanelHAUI::loop() {
    // if updating just return to not to interfere
    if (this->is_updating_) {
      return;
    }

    // process all commands in buffer
    this->process_commands_();

    // connect if not connected
    if (!this->is_connected_) {
      this->connect_();
    // check if not set up
    } else if (!this->is_setup_) {
      this->setup_();
    // check if not ready
    } else if (!this->is_ready_) {
      // if connected and set up then it is ready
      this->is_ready_ = true;
    }

    // check if manually set ready after amount of time
    if (!this->is_ready_) {
      if (this->started_ms_ == 0)
        this->started_ms_ = millis();
      if (this->started_ms_ + this->startup_override_ms_ < millis()) {
        ESP_LOGI(TAG, "Manually set as ready");
        this->is_ready_ = true;
      }
    }
  }

  void NSPanelHAUI::soft_reset() {
    this->send_command_("rest", false);
  }

  void NSPanelHAUI::hard_reset() {
    ESP_LOGD(TAG, "Restarting Nextion");
    this->soft_reset();
    delay(1500);  // NOLINT
    ESP_LOGD(TAG, "Restarting esphome");
    ESP.restart();  // NOLINT(readability-static-accessed-through-instance)
  }

  bool NSPanelHAUI::sleep() {
    if (this->send_command_("sleep=1", false)) {
      this->is_sleeping_ = true;
      return true;
    }
    return false;
  }

  bool NSPanelHAUI::wakeup() {
    if (this->send_command_("sleep=0", false)) {
      this->is_sleeping_ = false;
      return true;
    }
    return false;
  }

  bool NSPanelHAUI::goto_page(std::string page) {
    const std::string command = this->get_command("page %s", page.c_str());
    return this->send_command(command, true);
  }

  bool NSPanelHAUI::set_backlight_brightness(float brightness) {
    if (brightness < 0 || brightness > 1.0) {
      ESP_LOGW(TAG, "Brightness out of bounds, percentage range 0.0-1.0");
      return false;
    }
    std::string command = this->get_command("dim=%d", static_cast<int>(brightness * 100));
    return this->send_command(command, true);
  }

  std::string NSPanelHAUI::get_command(const char *format, ...) {
    char buffer[256];
    va_list arg;
    va_start(arg, format);
    int ret = vsnprintf(buffer, sizeof(buffer), format, arg);
    va_end(arg);
    ESP_LOGV("get_command: %s", buffer);
    return buffer;
  }

  bool NSPanelHAUI::send_command(const std::string &command, bool check_response) {
    if (!this->is_ready_ || this->is_sleeping_ || this->is_updating_) {
      ESP_LOGW(TAG, "send_command %s is not available", command.c_str());
      return false;
    }
    return send_command_(command.c_str(), check_response);
  };

  bool NSPanelHAUI::set_component_txt(const std::string &component, const std::string &value) {
    if (!this->is_ready_ || this->is_sleeping_ || this->is_updating_) {
      ESP_LOGW(TAG, "set_component_txt %s (%s) is not available - is_ready:%d is_sleeping:%d is_updating:%d",
        component.c_str(), value.c_str(), this->is_ready_, this->is_sleeping_, this->is_updating_);
      return false;
    }
    std::string command = this->get_command("%s.txt=\"%s\"", component.c_str(), value.c_str());
    return this->send_command(command, true);
  }

  bool NSPanelHAUI::set_component_int(const std::string &component, int value) {
    if (!this->is_ready_ || this->is_sleeping_ || this->is_updating_) {
      ESP_LOGW(TAG, "set_component_int %s (%d) is not available - is_ready:%d is_sleeping:%d is_updating:%d",
        component.c_str(), value, this->is_ready_, this->is_sleeping_, this->is_updating_);
      return false;
    }
    std::string command = this->get_command("%s.val=%d", component.c_str(), value);
    return this->send_command(command, true);
  }

  int NSPanelHAUI::get_int_value(const std::string &variable_name, const int default_value) {
    if (!this->is_ready_ || this->is_sleeping_ || this->is_updating_) {
      ESP_LOGW(TAG, "get_int_value %s (%d) is not available - is_ready:%d is_sleeping:%d is_updating:%d",
        variable_name.c_str(), default_value, this->is_ready_, this->is_sleeping_, this->is_updating_);
      return default_value;
    }
    int value = 0;
    std::string command = this->get_command("get %s", variable_name.c_str());
    if (this->send_command(command, false)) {
      if (!this->recv_int_value_(value, RECV_TIMEOUT_MS, true)) {
        value = default_value;
      }
    }
    ESP_LOGV(TAG, "get_int_value %s: %d", variable_name.c_str(), value);
    return value;
  }

  std::string NSPanelHAUI::get_txt_value(const std::string &variable_name, const std::string default_value) {
    if (!this->is_ready_ || this->is_sleeping_ || this->is_updating_) {
      ESP_LOGW(TAG, "get_txt_value %s (%s) is not available - is_ready:%d is_sleeping:%d is_updating:%d",
        variable_name.c_str(), default_value.c_str(), this->is_ready_, this->is_sleeping_, this->is_updating_);
      return default_value;
    }
    std::string value = "";
    std::string command = this->get_command("get %s", variable_name.c_str());
    if (this->send_command(command, false)) {
      if (!this->recv_txt_value_(value, RECV_TIMEOUT_MS, true)) {
        value = default_value;
      }
    }
    ESP_LOGV(TAG, "get_txt_value %s: %s", variable_name.c_str(), value.c_str());
    return value;
  }

  std::string NSPanelHAUI::get_component_txt(const std::string &component, const std::string default_value) {
    if (!this->is_ready_ || this->is_sleeping_ || this->is_updating_) {
      ESP_LOGW(TAG, "get_component_txt %s (%s) is not available - is_ready:%d is_sleeping:%d is_updating:%d",
        component.c_str(), default_value.c_str(), this->is_ready_, this->is_sleeping_, this->is_updating_);
      return default_value;
    }
    std::string value = "";
    std::string command = this->get_command("get %s.txt", component.c_str());
    if (this->send_command(command, false)) {
      if (!this->recv_txt_value_(value, RECV_TIMEOUT_MS, true)) {
        value = default_value;
      }
    }
    ESP_LOGV(TAG, "get_component_txt %s: %s", component.c_str(), value.c_str());
    return value;
  }

  int NSPanelHAUI::get_component_int(const std::string &component, int default_value) {
    if (!this->is_ready_ || this->is_sleeping_ || this->is_updating_) {
      ESP_LOGW(TAG, "get_component_int %s (%d) is not available - is_ready:%d is_sleeping:%d is_updating:%d",
        component.c_str(), default_value, this->is_ready_, this->is_sleeping_, this->is_updating_);
      return default_value;
    }
    int value = 0;
    if (this->send_command(this->get_command("get %s.val", component.c_str()), false)) {
      if (!this->recv_int_value_(value, RECV_TIMEOUT_MS, true)) {
        value = default_value;
      }
    }
    ESP_LOGV(TAG, "get_component_int %s: %d", component.c_str(), int(value));
    return value;
  }

  void NSPanelHAUI::connect_() {
    if (this->is_connected_)
      return;
    this->send_command_("connect");
    std::string response;
    this->recv_response_(response, RECV_TIMEOUT_MS);
    if (response.empty() || response.find("comok") == std::string::npos) {
      ESP_LOGW(TAG, "Nextion is not connected!");
      return;
    }
    ESP_LOGI(TAG, "Nextion is connected");
    this->is_connected_ = true;

    ESP_LOGD(TAG, "Connect request %s", response.c_str());
    size_t start;
    size_t end = 0;
    std::vector<std::string> connect_info;
    while ((start = response.find_first_not_of(',', end)) != std::string::npos) {
      end = response.find(',', start);
      connect_info.push_back(response.substr(start, end - start));
    }
    if (connect_info.size() == 7) {
      ESP_LOGD(TAG, "Received connect_info %zu", connect_info.size());
      this->device_model_ = connect_info[2];
      this->firmware_version_ = connect_info[3];
      this->serial_number_ = connect_info[5];
      this->flash_size_ = connect_info[6];
    } else {
      ESP_LOGE(TAG, "Nextion returned bad connect value \"%s\"", response.c_str());
    }
    this->dump_config();
    return;
  }

  bool NSPanelHAUI::send_command_(const std::string &command, bool check_response) {
    ESP_LOGD(TAG, "send_command %s", command.c_str());
    bool ret = false;

    // process all pending serial data
    if (this->available()) {
      this->process_commands_();
    }
    // send command
    this->write_str(command.c_str());
    this->write_str(COMMAND_DELIMITER.c_str());
    // check response
    if (check_response) {
      std::string res = "";
      if (this->recv_response_(res, RECV_TIMEOUT_MS)) {
        if (!res.empty() && res[0] == RES_CMD_FINISHED) {
          ret = true;
        }
      }
    } else {
      ret = true;
    }

    return ret;
  }

  void NSPanelHAUI::setup_() {
    if (this->is_setup_)
      return;
    ESP_LOGD(TAG, "Setup");
    // bkcmd, return for every command a response
    if (!this->send_command_("bkcmd=3", true)) {
      if (this->get_int_value("bkcmd", 0) != 3) {
        ESP_LOGW(TAG, "Setup bkcmd failed");
      }
    }
    // if needed also set sendxy=1
    if (this->use_touch_callback_) {
      if (!this->send_command_("sendxy=1", true)) {
        if (this->get_int_value("sendxy", 0) != 1) {
          ESP_LOGW(TAG, "Setup sendxy failed");
        }
      }
    }
    this->set_backlight_brightness(this->brightness_);
    this->setup_callback_.call();
    ESP_LOGD(TAG, "Setup finished");
    this->is_setup_ = true;
  }

  void NSPanelHAUI::reset_() {
    this->is_ready_ = false;
    this->is_connected_ = false;
    this->is_setup_ = false;
    this->started_ms_ = 0;
  }

  bool NSPanelHAUI::conv_txt_value_(const std::string value, std::string &res, bool check_first_byte) {
    if (value.length() == 0) {
      ESP_LOGE(TAG, "ERROR: Text value to convert is empty!");
      return false;
    }
    if (check_first_byte) {
      uint8_t d = value[0];
      if (d != RES_TXT_VALUE)
        return false;
      res = value.substr(1, value.length());
    } else {
      res = value;
    }
    return true;
  }

  bool NSPanelHAUI::conv_int_value_(const std::string value, int &res, bool check_first_byte) {
    if (value.length() == 0) {
      ESP_LOGE(TAG, "ERROR: Numeric value to convert is empty!");
      return false;
    }
    std::string conv_value;
    if (check_first_byte) {
      uint8_t d = value[0];
      if (d != RES_INT_VALUE)
        return false;
      conv_value = value.substr(1, value.length());
    } else {
      conv_value = value;
    }
    for (int i = 0; i < 4; ++i) {
      res += conv_value[i] << (8 * i);
    }
    return true;
  }

  bool NSPanelHAUI::recv_int_value_(int &value, int timeout, bool check_first_byte) {
    while (this->recv_active_) {
      App.feed_wdt();
      continue;
    }
    this->recv_active_ = true;
    bool ret = false;
    std::string temp;
    while (this->recv_response_(temp, timeout)) {
      if (this->available() && check_first_byte && temp[0] != RES_INT_VALUE) {
        this->process_command_(temp);
      } else if (temp[0] == RES_INT_VALUE || !check_first_byte) {
        if (this->conv_int_value_(temp, value, check_first_byte)) {
          ret = true;
          break;
        }
      }
      temp.clear();
    }
    this->recv_active_ = false;
    return ret;
  }

  bool NSPanelHAUI::recv_txt_value_(std::string &value, int timeout, bool check_first_byte) {
    while (this->recv_active_) {
      App.feed_wdt();
      continue;
    }
    this->recv_active_ = true;
    bool ret = false;
    std::string temp;
    while (this->recv_response_(temp, timeout)) {
      if (this->available() && check_first_byte && temp[0] != RES_TXT_VALUE) {
        this->process_command_(temp);
      } else if (temp[0] == RES_TXT_VALUE || !check_first_byte) {
        if (this->conv_txt_value_(temp, value, check_first_byte)) {
          ret = true;
        }
      }
      temp.clear();
    }
    this->recv_active_ = false;
    return ret;
  }

  uint16_t NSPanelHAUI::recv_response_(std::string &response, int timeout, bool remove_ff, bool recv_flag) {
    uint16_t ret = 0;
    uint8_t c = 0;
    uint8_t nr_ff_bytes = 0;
    uint64_t start = millis();
    bool exit_flag = false;
    bool ff_flag = false;
    bool recv = false;
    while ((timeout == 0 && this->available()) || millis() - start <= timeout) {
      while (this->available()) {
        this->read_byte(&c);
        if (!recv) recv = true;
        ESP_LOGV(TAG, "recv_response_ %02X", c);
        response += (char)c;
        if (response.find(COMMAND_DELIMITER) != std::string::npos) {
          ff_flag = true;
        }
        if (recv_flag && c == 0x05) {
          exit_flag = true;
        }
        if (exit_flag || ff_flag) {
          break;
        }
      }
      App.feed_wdt();
      if (exit_flag || ff_flag || recv) {
        break;
      }
    }
    if (remove_ff && ff_flag) {
      response = response.substr(0, response.length() - 3);  // Remove last 3 0xFF
    }
    if (recv) {
      ret = response.length();
    }
    return ret;
  }

  // nextion.tech/instruction-set/
  void NSPanelHAUI::process_command_(std::string command_data) {
    char c = command_data[0];
    std::string command = command_data.substr(1, command_data.length());
    for(int i = 0; i < command_data.length(); i++) {
        ESP_LOGVV(TAG, "Received command_data %d: 0x%0X", i, command_data[i]);
    }
    switch (c) {
      case RES_CMD_INVALID:  // 0x00: instruction has failed
        // startup generates 0x00 0x00 0x00 0xFF 0xFF 0xFF
        // which can be skipped
        if (!command_data.length()) {
          ESP_LOGW(TAG, "Nextion reported invalid instruction!");
        }
        break;
      case RES_CMD_FINISHED:  // 0x01: instruction finished successful
        ESP_LOGV(TAG, "instruction finished successful");
        break;
      case RES_INVALID_COMPONENT_ID:  // 0x02: invalid Component ID or name was used
        ESP_LOGW(TAG, "Nextion reported component ID or name invalid!");
        break;
      case RES_INVALID_PAGE_ID:  // 0x03: invalid Page ID or name was used
        ESP_LOGW(TAG, "Nextion reported page ID invalid!");
        break;
      case RES_INVALID_PICTURE_ID:  // 0x04: invalid Picture ID was used
        ESP_LOGW(TAG, "Nextion reported picture ID invalid!");
        break;
      case RES_INVALID_FONT_ID:  // 0x05: invalid Font ID was used
        ESP_LOGW(TAG, "Nextion reported font ID invalid!");
        break;
      case RES_FILE_OPERATION_FAILED:  // 0x06: file operation fails
        ESP_LOGW(TAG, "Nextion File operation fail!");
        break;
      case RES_INVALID_INSTRUCTIONS_CRC:  // 0x09: instructions with CRC validation fails their CRC check
        ESP_LOGW(TAG, "Nextion Instructions with CRC validation fails their CRC check!");
        break;
      case RES_INVALID_BAUD_RATE:  // 0x11: invalid Baud rate was used
        ESP_LOGW(TAG, "Nextion reported baud rate invalid!");
        break;
      case RES_INVALID_WAVEFORM_ID:  // 0x12: invalid Waveform ID or Channel # was used
        ESP_LOGW(TAG, "Nextion reported invalid Waveform ID or Channel was used!");
        break;
      case RES_INVALID_VARIABLE:  // 0x1A: variable name invalid
        ESP_LOGW(TAG, "Nextion reported variable name invalid!");
        break;
      case RES_INVALID_OPERATION:  // 0x1B: variable operation invalid
        ESP_LOGW(TAG, "Nextion reported variable operation invalid!");
        break;
      case RES_ASSIGNMENT_FAILED:  // 0x1C: failed to assign
        ESP_LOGW(TAG, "Nextion reported failed to assign variable!");
        break;
      case RES_OPERATE_EEPROM_FAILED:  // 0x1D: operate EEPROM failed
        ESP_LOGW(TAG, "Nextion reported operating EEPROM failed!");
        break;
      case RES_INVALID_PARAMETER_QUANTITY:  // 0x1E: parameter quantity invalid
        ESP_LOGW(TAG, "Nextion reported parameter quantity invalid!");
        break;
      case RES_IO_OPERATION_FAILED:  // 0x1F: IO operation failed
        ESP_LOGW(TAG, "Nextion reported component I/O operation invalid!");
        break;
      case RES_UNDEFINED_ESC_CHARS:  // 0x20: undefined escape characters
        ESP_LOGW(TAG, "Nextion reported undefined escape characters!");
        break;
      case RES_VARIABLE_NAME_TOO_LONG: // 0x23: variable name too long
        ESP_LOGW(TAG, "Nextion reported too long variable name!");
        break;
      case RES_SERIAL_BUFFER_OVERFLOW:  // 0x24: serial buffer overflow occured
        ESP_LOGW(TAG, "Nextion reported Serial Buffer overflow!");
        break;
      case RES_TOUCH:  // 0x65: touch event
        {
          if (command.length() != 3) {
            ESP_LOGW(TAG, "Touch event data is expecting 3, received %zu", command.length());
            break;
          }
          uint8_t page_id = command[0];
          uint8_t component_id = command[1];
          uint8_t touch_event = command[2];  // 0 -> release, 1 -> press
          ESP_LOGD(TAG, "Got touch page: %u component: %u type: %s", page_id, component_id,
                  touch_event ? "PRESS" : "RELEASE");
          this->component_callback_.call(page_id, component_id, touch_event != 0);
        }
        break;
      case RES_CURRENT_PAGE_ID:  // 0x66: new page event generated by sendme
        {
          if (command.length() != 1) {
            ESP_LOGW(TAG, "New page event data is expecting 1, received %zu", command.length());
            break;
          }
          uint8_t page_id = command[0];
          ESP_LOGD(TAG, "Got new page=%u", page_id);
          this->page_callback_.call(page_id);
        }
        break;
      case RES_TOUCH_COORDINATES:  // 0x67: touch coordinates (awake)
      case RES_TOUCH_COORDINATES_SLEEP:  // 0x68: touch coordinates (sleep)
        {
          if (command.length() != 5) {
            ESP_LOGW(TAG, "Touch coordinate data is expecting 5, received %zu", command.length());
            ESP_LOGW(TAG, "%s", command.c_str());
            break;
          }
          uint16_t x = (uint16_t(command[0]) << 8) | command[1];
          uint16_t y = (uint16_t(command[2]) << 8) | command[3];
          uint8_t touch_event = command[4];  // 0 -> release, 1 -> press
          ESP_LOGD(TAG, "Got touch at x: %u y: %u type: %s", x, y, touch_event ? "PRESS" : "RELEASE");
          this->touch_callback_.call(x, y, touch_event != 0);
        }
        break;
      case RES_TXT_VALUE:  // 0x70: string variable data return
        {
          std::string res = "";
          this->conv_txt_value_(command_data, res, true);
          ESP_LOGW(TAG, "Received unprocessed txt value: \"%s\"", res.c_str());
        }
        break;
      case RES_INT_VALUE:  // 0x71: numeric variable data return
        {
          int res = 0;
          this->conv_int_value_(command_data, res, true);
          ESP_LOGW(TAG, "Received unprocessed int value: %d", int(res));
        }
        break;
      case RES_SLEEP:  // 0x86: device goes into sleep mode (not when using sleep=1)
        ESP_LOGV(TAG, "Received Nextion entering sleep automatically");
        this->is_sleeping_ = true;
        this->sleep_callback_.call();
        break;
      case RES_WAKEUP:  // 0x87: device wakes up (not when using sleep=0)
        ESP_LOGV(TAG, "Received Nextion leaves sleep automatically");
        this->is_sleeping_ = false;
        this->wakeup_callback_.call();
        break;
      case RES_SYSTEM_STARTUP:  // 0x88: nextion startup
        ESP_LOGV(TAG, "Nextion startup");
        this->reset_();
        break;
      case RES_SD_CARD_UPGRADE:  // 0x89: SD card upgrade
        break;
      default:
        ESP_LOGW(TAG, "Received unknown event from nextion: 0x%02X (%s)", c, command_data.c_str());
        break;
    }

  }

  void NSPanelHAUI::process_commands_() {
    if (this->is_updating_) return;
    std::string commands = "";
    std::string command;
    size_t command_length = 0;
    uint8_t d;
    while (this->available()) {
      this->read_byte(&d);
      commands += (char)d;
    }
    while ((command_length = commands.find(COMMAND_DELIMITER)) != std::string::npos) {
      command = commands.substr(0, command_length);
      this->process_command_(command);
      commands.erase(0, command_length + COMMAND_DELIMITER.length());
    }
  }

  void NSPanelHAUI::add_setup_callback(std::function<void()> &&callback) {
    this->setup_callback_.add(std::move(callback));
  }

  void NSPanelHAUI::add_page_callback(std::function<void(uint8_t)> &&callback) {
    this->page_callback_.add(std::move(callback));
  }

  void NSPanelHAUI::add_sleep_callback(std::function<void()> &&callback) {
    this->sleep_callback_.add(std::move(callback));
  }

  void NSPanelHAUI::add_wakeup_callback(std::function<void()> &&callback) {
    this->wakeup_callback_.add(std::move(callback));
  }

  void NSPanelHAUI::add_touch_callback(std::function<void(uint16_t, uint16_t, bool)> &&callback) {
    this->touch_callback_.add(std::move(callback));
    this->use_touch_callback_ = true;
  }

  void NSPanelHAUI::add_component_callback(std::function<void(uint8_t, uint8_t, bool)> &&callback) {
    this->component_callback_.add(std::move(callback));
  }


}  // namespace nspanel_haui
}  // namespace esphome
