#pragma once
#include "esphome/core/automation.h"
#include "nspanel_haui.h"

namespace esphome {
namespace nspanel_haui {

class SetupTrigger : public Trigger<> {
 public:
  explicit SetupTrigger(NSPanelHAUI *haui) {
    haui->add_setup_callback([this]() { this->trigger(); });
  }
};

class PageTrigger : public Trigger<uint8_t> {
 public:
  explicit PageTrigger(NSPanelHAUI *haui) {
    haui->add_page_callback([this](const uint8_t x) { this->trigger(x); });
  }
};

class SleepTrigger : public Trigger<> {
 public:
  explicit SleepTrigger(NSPanelHAUI *haui) {
    haui->add_sleep_callback([this]() { this->trigger(); });
  }
};

class WakeupTrigger : public Trigger<> {
 public:
  explicit WakeupTrigger(NSPanelHAUI *haui) {
    haui->add_wakeup_callback([this]() { this->trigger(); });
  }
};

class TouchTrigger : public Trigger<uint16_t, uint16_t, bool> {
 public:
  explicit TouchTrigger(NSPanelHAUI *haui) {
    haui->add_touch_callback([this](const uint16_t x, const uint16_t y, bool state) { this->trigger(x, y, state); });
  }
};

class ComponentTrigger : public Trigger<uint8_t, uint8_t, bool> {
 public:
  explicit ComponentTrigger(NSPanelHAUI *haui) {
    haui->add_component_callback([this](const uint8_t p_id, const uint8_t c_id, bool state) { this->trigger(p_id, c_id, state); });
  }
};

}  // namespace nspanel_haui
}  // namespace esphome
