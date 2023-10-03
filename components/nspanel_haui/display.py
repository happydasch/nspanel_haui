import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.components import display, uart
from esphome.const import (
    CONF_ID,
    CONF_LAMBDA,
    CONF_BRIGHTNESS,
    CONF_TRIGGER_ID,
)
from esphome.core import CORE
from . import NSPanelHAUI, haui_ns, haui_ref

CONF_TFT_URL = "tft_url"
CONF_ON_SLEEP = "on_sleep"
CONF_ON_WAKEUP = "on_wakeup"
CONF_ON_PAGE = "on_page"
CONF_ON_SETUP = "on_setup"
CONF_ON_TOUCH = "on_touch"
CONF_ON_COMPONENT = "on_component"
CONF_TFT_URL = "tft_url"

CODEOWNERS = ["@happydasch"]

DEPENDENCIES = ["uart"]
AUTO_LOAD = ["binary_sensor", "switch", "sensor", "text_sensor"]

SetupTrigger = haui_ns.class_("SetupTrigger", automation.Trigger.template())
PageTrigger = haui_ns.class_("PageTrigger", automation.Trigger.template())
SleepTrigger = haui_ns.class_("SleepTrigger", automation.Trigger.template())
WakeupTrigger = haui_ns.class_("WakeupTrigger", automation.Trigger.template())
TouchTrigger = haui_ns.class_("TouchTrigger", automation.Trigger.template())
ComponentTrigger = haui_ns.class_("ComponentTrigger", automation.Trigger.template())

CONFIG_SCHEMA = (
    display.BASIC_DISPLAY_SCHEMA.extend(
        {
            cv.GenerateID(): cv.declare_id(NSPanelHAUI),
            cv.Optional(CONF_TFT_URL): cv.All(cv.string, cv.only_with_arduino),
            cv.Optional(CONF_BRIGHTNESS, default=1.0): cv.percentage,
            cv.Optional(CONF_ON_SETUP): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(SetupTrigger),
                }
            ),
            cv.Optional(CONF_ON_PAGE): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(PageTrigger),
                }
            ),
            cv.Optional(CONF_ON_SLEEP): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(SleepTrigger),
                }
            ),
            cv.Optional(CONF_ON_WAKEUP): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(WakeupTrigger),
                }
            ),
            cv.Optional(CONF_ON_TOUCH): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(TouchTrigger),
                }
            ),
            cv.Optional(CONF_ON_COMPONENT): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(ComponentTrigger),
                }
            ),
        }
    )
    .extend(cv.polling_component_schema("5s"))
    .extend(uart.UART_DEVICE_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)

    if CONF_BRIGHTNESS in config:
        cg.add(var.set_brightness(config[CONF_BRIGHTNESS]))

    if CONF_LAMBDA in config:
        lambda_ = await cg.process_lambda(
            config[CONF_LAMBDA], [(haui_ref, "it")], return_type=cg.void
        )
        cg.add(var.set_writer(lambda_))

    if CONF_TFT_URL in config:
        cg.add_define("USE_NSPANEL_HAUI_TFT_UPLOAD")
        cg.add(var.set_tft_url(config[CONF_TFT_URL]))
        cg.add_library("WiFiClientSecure", None)
        cg.add_library("HTTPClient", None)

    await display.register_display(var, config)

    for conf in config.get(CONF_ON_SETUP, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    for conf in config.get(CONF_ON_PAGE, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.uint8, "x")], conf)

    for conf in config.get(CONF_ON_SLEEP, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    for conf in config.get(CONF_ON_WAKEUP, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    for conf in config.get(CONF_ON_TOUCH, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.uint16, "x"), (cg.uint16, "y"), (cg.bool_, "state")], conf)

    for conf in config.get(CONF_ON_COMPONENT, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.uint8, "p_id"), (cg.uint8, "c_id"), (cg.bool_, "state")], conf)
