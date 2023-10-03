#pragma once

#include "nspanel_haui_types.h"

#include "esphome/core/defines.h"
#include "esphome/core/component.h"
#include "esphome/components/uart/uart.h"
#include "esphome/components/display/display_color_utils.h"

#include <WiFiClientSecure.h>
#include <HTTPClient.h>

namespace esphome {
namespace nspanel_haui {

  class NSPanelHAUI;

  using haui_writer_t = std::function<void(NSPanelHAUI &)>;

  static const std::string COMMAND_DELIMITER{static_cast<char>(255), static_cast<char>(255), static_cast<char>(255)};
  static const uint32_t RECV_TIMEOUT_MS = 500;


class NSPanelHAUI : public PollingComponent, public uart::UARTDevice {


  // main functionality
  public:

    void setup() override;
    void update() override;
    void loop() override;
    void dump_config() override;
    float get_setup_priority() const override;
    void set_writer(const haui_writer_t &writer);
    void soft_reset();
    void hard_reset();
    bool sleep();
    bool wakeup();
    bool is_sleeping() { return this->is_sleeping_; }
    bool is_connected() { return this->is_connected_; }
    bool is_ready() { return this->is_ready_; }
    bool goto_page(std::string page);
    void set_brightness(float brightness) { this->brightness_ = brightness; }
    bool set_backlight_brightness(float brightness);
    std::string get_command(const char *format, ...);
    void process_commands() { this->process_commands_(); }
    bool send_command(const std::string &command, bool check_response);
    bool send_command(const std::string &command) { return send_command(command, false); };
    bool set_component_int(const std::string &component, int value);
    bool set_component_txt(const std::string &component, const std::string &value);
    int get_int_value(const std::string &variable_name, const int default_value);
    int get_int_value(const std::string &variable_name) { return get_int_value(variable_name, -1); }
    std::string get_txt_value(const std::string &variable_name, const std::string default_value);
    std::string get_txt_value(const std::string &variable_name) { return get_txt_value(variable_name, ""); }
    std::string get_component_txt(const std::string &component, const std::string default_value);
    std::string get_component_txt(const std::string &component) { return get_component_txt(component, ""); }
    int get_component_int(const std::string &component, const int default_value);
    int get_component_int(const std::string &component) { return get_component_int(component, -1); }

    /**
     * Add a callback to be notified when the display completes its initialize setup.
     *
     * This will be initialized when receiving the 0x88 command from display. In newer nextion editor
     * versions it is needed to call `printh 00 00 00 ff ff ff 88 ff ff ff` in program.s
     *
     * @param callback The void() callback.
     */
    void add_setup_callback(std::function<void()> &&callback);

    /**
     * Add a callback to be notified when the display changes pages.
     *
     * This requires to use `sendme` command in page initialize.
     *
     * @param callback The void(std::string) callback.
     */
    void add_page_callback(std::function<void(uint8_t)> &&callback);

    /**
     * Add a callback to be notified when display has a sleep event.
     *
     * This callback is called when automatical sleep event happens.
     *
     * @param callback The void() callback.
     */
    void add_sleep_callback(std::function<void()> &&callback);

    /**
     * Add a callback to be notified when display has a wakeup event.
     *
     * This callback is called when automatical wake up event happens.
     *
     * @param callback The void() callback.
     */
    void add_wakeup_callback(std::function<void()> &&callback);

    /**
     * Add a callback to be notified when a display touch happened.
     *
     * This callback is using `sendxy=1` which gives a limited access to
     * x,y coordinates. To get the current coordinates get the value
     * from `tch0` and `tch1` while touch is active.
     *
     * @param callback The void(std::string) callback.
     */
    void add_touch_callback(std::function<void(uint16_t, uint16_t, bool)> &&callback);

    /**
     * Add a callback to be notified when a display component was pressed.
     *
     * To use this callback, it is neccessary to enable `send component id` in the
     * components event.
     *
     * @param callback The void(std::string) callback.
     */
    void add_component_callback(std::function<void(uint8_t, uint8_t, bool)> &&callback);

  protected:

    /**
     * Connects to the display.
     *
     */
    void connect_();

    /**
     * Sets up display after connect.
     *
     * This method sets up the display after connect.
     */
    void setup_();

    /**
     * Resets the display.
     *
     * @param restart should the display be restarted
     */
    void reset_();

    /**
     * Converts a txt result command to a string
     *
     * starts with 0x70
     *
     * @param value the value from command
     * @param res the result
     * @param check_first_byte should the first byte be checked
     * @return bool
     */
    bool conv_txt_value_(const std::string value, std::string &res, bool check_first_byte);

    /**
     * Converts a int result command to a int
     *
     * starts with 0x71
     *
     * @param value the value from command
     * @param res the result
     * @param check_first_byte should the first byte be checked
     * @return bool
     */
    bool conv_int_value_(const std::string value, int &res, bool check_first_byte);

    /**
     * Receives a txt value from display.
     *
     * @param value
     * @param timeout
     * @param check_first_byte
     * @return bool
     */
    bool recv_txt_value_(std::string &value, int timeout, bool check_first_byte);

    /**
     * Receives a int value from display.
     *
     * @param value
     * @param timeout
     * @param check_first_byte
     * @return true
     * @return false
     */
    bool recv_int_value_(int &value, int timeout, bool check_first_byte);

    /**
     * Receives a response from display.
     *
     * This is the main communication method.
     *
     * @param response Response string.
     * @param timeout Timeout in ms.
     * @param remove_ff This flag defines if the last ff should be removed
     * @param recv_flag This flag is used by the upload process to indicate if the chunk is finished.
     * @return uint16_t
     */
    uint16_t recv_response_(std::string &response, int timeout, bool remove_ff, bool recv_flag);
    uint16_t recv_response_(std::string &response, int timeout, bool remove_ff) { return recv_response_(response, timeout, remove_ff, false); }
    uint16_t recv_response_(std::string &response, int timeout) { return recv_response_(response, timeout, true, false); }

    /**
     * Sends a command to display.
     *
     * This method should only be used internally.
     * If display is sleeping, this method can wake it up.
     *
     * @param command
     * @param check_response
     * @return true
     * @return false
     */
    bool send_command_(const std::string &command, bool check_response);
    bool send_command_(const std::string &command) { return send_command_(command, false); }

    /**
     * Processes a single command from serial.
     *
     * This method takes a complete command and parses it.
     * To process the whole buffer, this method needs to be called
     * multiple times.
     *
     * @param command_data The command data.
     */
    void process_command_(std::string command_data);

    /**
     * Process all pending commands.
     */
    void process_commands_();

    // callback handlers
    CallbackManager<void()> setup_callback_{};
    CallbackManager<void(uint8_t)> page_callback_{};
    CallbackManager<void()> sleep_callback_{};
    CallbackManager<void()> wakeup_callback_{};
    CallbackManager<void(uint16_t, uint16_t, bool)> touch_callback_{};
    CallbackManager<void(uint8_t, uint8_t, bool)> component_callback_{};

    // startup and communication related variables
    uint32_t startup_override_ms_ = 5000;
    uint32_t started_ms_ = 0;
    bool recv_active_ = false;

    // device info variables
    std::string device_model_;
    std::string firmware_version_;
    std::string serial_number_;
    std::string flash_size_;

    float brightness_{1.0};
    optional<haui_writer_t> writer_;

    /**
     * Should touch callback be used
     *
     * If a touch callback was setup, this will become true. In the connection
     * process, this will be used to get touch infos using sendxy=1
     *
     */
    bool use_touch_callback_ = false;

    /**
     * Is updating state
     *
     * This will be set to true after the display has started the
     * update process.
     */
    bool is_updating_ = false;

    /**
     * Is sleeping state
     *
     * This will be set to true after the display has been
     * sent autoamtically to sleep state or it has been woken up.
     */
    bool is_sleeping_ = false;

    /**
     * Is connected state
     *
     * This will be set to true after the display has been started and a connect
     * command was successfully sent.
     */
    bool is_connected_ = false;
    /**
     * Is setup state
     *
     * This will be set to true after the display has been set up
     */
    bool is_setup_ = false;
    /**
     * Is ready state
     *
     * This will be set to true after the display has been connected and it was set up.
     *
     * Only when is_ready_ is true it is possible to use the display. This will
     * be set to true after the display has been connected.
     *
     * NOTE: If not is_ready_ then only send_command and process_command is
     * available.
     */
    bool is_ready_ = false;


  // upload
  public:

    /**
     * Set the tft file URL.
     */
    void set_tft_url(const std::string &tft_url) { this->tft_url_ = tft_url; }

    /**
     * Upload the tft file
     */
    void upload_tft();

  protected:

    /**
     * will request chunk_size chunks from the web server
     * and send each to the display
     *
     * @param int content_length Total size of the file
     * @param uint32_t chunk_size
     * @return true if success, false for failure.
     */
    int upload_by_chunks_(String location, int range_start);

    void upload_end_();

    std::string tft_url_;
    uint8_t *transfer_buffer_{nullptr};
    size_t transfer_buffer_size_;
    bool upload_first_chunk_sent_ = false;

    int content_length_ = 0;
    int tft_size_ = 0;

};


}  // namespace nspanel_haui
}  // namespace esphome
