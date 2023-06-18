import esphome.codegen as cg
from esphome.components import uart

haui_ns = cg.esphome_ns.namespace("nspanel_haui")
NSPanelHAUI = haui_ns.class_("NSPanelHAUI", cg.PollingComponent, uart.UARTDevice)
haui_ref = NSPanelHAUI.operator("ref")
