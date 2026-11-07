"""Static checks for the ESPHome YAML (no ESPHome install needed)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "esphome" / "nspanel_haui"


def _read(name: str) -> str:
    return (ROOT / name).read_text()


def _load_tagged(path: Path) -> dict:
    """Parse ESPHome YAML, keeping custom tags (``!remove`` …) as ``"!<tag>"``."""
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    Loader.add_multi_constructor("!", lambda loader, suffix, node: f"!{suffix}")
    return yaml.load(path.read_text(), Loader=Loader)  # noqa: S506 - SafeLoader subclass


def test_hub_availability_reset_on_last_client_disconnect():
    api = _read("api.yaml")
    disconnected = api.split("on_client_disconnected:")[1].split("actions:")[0]
    assert "id(hub_availability) = global_api_server->is_connected();" in disconnected


def test_min_esphome_version_declared():
    assert "min_version: 2026.10.0" in _read("base.yaml")


def test_web_server_is_optional_and_off_by_default():
    """The web server costs flash/RAM; only the dev build enables it."""
    import re

    # base.yaml keeps only a commented example, so the shipped build omits it.
    assert not re.search(r"^web_server:", _read("base.yaml"), re.MULTILINE)
    # The local development build keeps the web UI for diagnostics.
    dev = (ROOT.parent / "nspanel_haui_dev.yaml").read_text()
    assert re.search(r"^web_server:", dev, re.MULTILINE)
    # The universal image bakes no web credentials because it has no web server.
    universal = (ROOT.parent / "nspanel_haui_universal.yaml").read_text()
    assert "web_username" not in universal


def test_firmware_reports_required_tft_version_separately():
    version = _read("version.yaml")
    state_script = _read("scripts_event.yaml")
    assert "tft_version:" in version
    assert 'auto tft_required_version = "$tft_version";' in state_script
    assert 'root["tft_required_version"] = tft_required_version;' in state_script


def test_unused_required_tft_version_removed():
    assert "required_tft_version" not in _read("version.yaml")


def test_http_request_buffers_fit_github_redirect_headers():
    """The firmware update entity needs room for GitHub's ~5.4 KB headers."""
    import re

    base = _read("base.yaml")
    assert re.search(r"^\s+buffer_size_rx:\s*8192\s*$", base, re.MULTILINE)
    assert re.search(r"^\s+buffer_size_tx:\s*2048\s*$", base, re.MULTILINE)


def test_command_spacing_is_enabled_to_prevent_nextion_rx_overflow():
    import re

    assert re.search(r"^\s+command_spacing:\s*2ms\s*$", _read("display.yaml"), re.MULTILINE)


def test_tft_upload_tx_buffer_fits_the_github_redirect():
    """GitHub redirects release TFTs to a ~870-character signed URL.

    The redirected request line overflows the 512-byte ESP-IDF default TX
    buffer, so every hub TFT install failed before the first byte.
    """
    import re

    match = re.search(
        r"^\s+tft_upload_http_buffer_size_tx:\s*(\d+)\s*$", _read("display.yaml"), re.MULTILINE
    )
    assert match and int(match.group(1)) >= 1024
    upload = (ROOT.parent / "nextion_patch" / "nextion" / "nextion_upload_esp32.cpp").read_text()
    assert ".buffer_size_tx = this->tft_upload_http_buffer_size_tx_" in upload


def test_every_tft_upload_starts_with_the_4k_first_chunk():
    """Only a failed upload leaves ``upload_first_chunk_sent_`` set; success reboots.

    A retry in the same boot then requested the whole file as its first range,
    jumped past the end on the display's 0x08 answer and stopped after 4 KB.
    """
    for name in ("nextion_upload_esp32.cpp", "nextion_upload_arduino.cpp"):
        source = (ROOT.parent / "nextion_patch" / "nextion" / name).read_text()
        upload_tft = source.split("bool Nextion::upload_tft(")[1]
        before_first_chunk = upload_tft[: upload_tft.index("upload_by_chunks_(")]
        assert "this->upload_first_chunk_sent_ = false;" in before_first_chunk, name


def test_tft_install_actions_live_in_the_integration():
    """Only the hub's transport action remains; installs go through nspanel_haui."""
    api = _read("api.yaml")
    assert "- action: upload_tft_url" in api
    assert "- action: upload_tft\n" not in api

    # The standalone Update Display button is gone, but the display component
    # keeps a configurable TFT URL: overridng the `tft_update_url` substitution
    # in a device YAML installs a local TFT build. HAUI itself always passes
    # the URL of the TFT it installs.
    for config in (
        "install.yaml",
        "nspanel_haui.yaml",
        "nspanel_haui_dev.yaml",
        "nspanel_haui_universal.yaml",
    ):
        assert "tft_update_url:" in (ROOT.parent / config).read_text(), config
    display = _read("display.yaml")
    assert "tft_url: $tft_update_url" in display


def test_firmware_drops_protocol_the_hub_never_uses():
    """Discovery uses the device registry and the device state carries the versions."""
    api = _read("api.yaml")
    for action in ("haui_discover", "req_device_info", "req_reconnect"):
        assert f"- action: {action}\n" not in api
    events = _read("scripts_event.yaml") + _read("switch.yaml")
    for event in ("esphome.haui_discover", "esphome.res_device_info", "esphome.use_relay_"):
        assert event not in events


def test_maintenance_entities_are_disabled_by_default():
    """Restart Display and Screen Power are rarely needed."""
    import yaml

    entities = {
        e["id"]: e
        for name in ("button.yaml", "switch.yaml")
        for e in next(iter(yaml.safe_load(_read(name)).values()))
    }
    for entity_id in ("restart_display", "screen_power"):
        assert entity_id in entities, f"button '{entity_id}' missing"
        assert entities[entity_id]["disabled_by_default"] is True, entity_id

    # The standalone Update Display button was removed: TFT management belongs
    # to the hub (the HAUI Display update entity and Device Manager flow).
    assert "update_display" not in entities


def test_buzzer_is_silenced_before_every_main_loop_stall():
    """rtttl turns a note off only from its loop(); the LEDC keeps sounding it.

    A blocked main loop (TFT upload, firmware OTA) or a reboot (a CPU-only
    reset leaves the LEDC running until the next boot's setup) left the note
    playing at that moment sounding continuously (#62).
    """
    import yaml

    base = yaml.safe_load(_read("base.yaml"))
    platforms = {ota["platform"]: ota for ota in base["ota"]}
    assert set(platforms) == {"esphome", "http_request"}
    for ota in platforms.values():
        assert {"script.execute": "suspend_activities"} in ota["on_begin"]
    assert {"script.execute": "suspend_activities"} in base["esphome"]["on_shutdown"]

    upload = _read("scripts_common.yaml").split("- id: prepare_tft_upload")[1]
    assert upload.index("script.execute: suspend_activities") < upload.index("upload_tft()")


def test_native_ota_is_encrypted_with_the_api_key():
    """ESPHome warns that an OTA password next to an api key wastes flash and
    RAM (#81).  A bare ``encryption:`` inherits ``api_encryption_key``.
    """
    import yaml

    base = yaml.safe_load(_read("base.yaml"))
    native = next(ota for ota in base["ota"] if ota["platform"] == "esphome")
    assert "encryption" in native and native["encryption"] is None
    assert "password" not in native

    configs = (
        "install.yaml",
        "nspanel_haui.yaml",
        "nspanel_haui_dev.yaml",
        "nspanel_haui_universal.yaml",
        "secrets.yaml.example",
    )
    for config in configs:
        assert "ota_password" not in (ROOT.parent / config).read_text(), config


def test_optional_debug_diagnostics_are_dev_only():
    """Production packages avoid exposing troubleshooting sensors by default."""
    import yaml

    debug = yaml.safe_load(_read("debug.yaml"))
    assert any(sensor["platform"] == "uptime" for sensor in debug["sensor"])
    assert any(sensor["platform"] == "debug" for sensor in debug["sensor"])
    assert any(sensor["platform"] == "debug" for sensor in debug["text_sensor"])

    sensors = yaml.safe_load(_read("sensor.yaml"))["sensor"]
    assert not any(sensor["platform"] == "uptime" for sensor in sensors)

    for config in ("nspanel_haui.yaml", "nspanel_haui_universal.yaml"):
        packages = _load_tagged(ROOT.parent / config)["packages"]
        assert "debug" not in packages

    dev_packages = _load_tagged(ROOT.parent / "nspanel_haui_dev.yaml")["packages"]
    assert dev_packages["debug"] == "!include"


def test_universal_image_keeps_its_wifi_across_firmware_updates():
    """ESPHome keys the captive-portal Wi-Fi to the config hash when the YAML
    defines a station network, so every firmware update forgot it and the panel
    fell back to its setup access point.  Without one it uses a fixed key; a
    boot migration (before WiFi's setup at priority 250) moves Wi-Fi saved by
    older builds there.
    """
    universal = _load_tagged(ROOT.parent / "nspanel_haui_universal.yaml")
    assert universal["wifi"]["ssid"] == "!remove"
    assert universal["wifi"]["password"] == "!remove"

    boot = universal["esphome"]["on_boot"]
    assert boot["priority"] > 250
    migrate = boot["then"][0]["lambda"]
    assert "88491487UL" in migrate
    assert "sizeof(saved)" in migrate
    assert "<nvs.h>" in universal["esphome"]["includes"]


def test_nextion_patch_is_never_older_than_the_package():
    """The package and the patch change together on dev.

    With the default 1-day cache a build combined a fresh display.yaml with an
    older patch: "[tft_upload_http_buffer_size_tx] is an invalid option".
    """
    package = (ROOT.parent / "nspanel_haui.yaml").read_text()
    block = package.split("external_components:")[1].split("packages:")[0]
    assert "path: esphome/nextion_patch" in block
    assert "refresh: 0s" in block


def test_firmware_can_be_flashed_from_a_url():
    """The hub installs other releases and custom builds through this action."""
    api = _read("api.yaml")
    block = api.split("- action: install_firmware_url")[1].split("- action:")[0]
    assert "md5sum: string" in block
    assert "ota.http_request.flash:" in block
    assert "md5: !lambda return md5sum;" in block
    assert "platform: http_request" in _read("base.yaml")


def test_firmware_declares_no_update_entity_of_its_own():
    """The hub's HAUI Firmware entity owns firmware updates; ESPHome keeps only its stock one."""
    base = _read("base.yaml")
    assert "\nupdate:" not in base
    assert "firmware_manifest_url" not in base


def test_firmware_build_variant_is_reported_and_never_universal_for_custom_builds():
    """The device state names its build variant; a custom build never claims universal.

    The hub refuses to offer or install a firmware manifest whose ``variant``
    does not match the reported one, so the universal release image must only
    ever be published by the universal config.
    """
    for script in ("publish_connection_request", "publish_device_state"):
        block = _read("scripts_event.yaml").split(f"- id: {script}")[1].split("- id:")[0]
        assert 'root["firmware_variant"]' in block

    package = (ROOT.parent / "nspanel_haui.yaml").read_text()
    assert "firmware_variant: 'custom'" in package

    dev = (ROOT.parent / "nspanel_haui_dev.yaml").read_text()
    assert "firmware_variant: 'custom'" in dev

    universal = (ROOT.parent / "nspanel_haui_universal.yaml").read_text()
    assert "firmware_variant: 'universal'" in universal


def test_display_setting_changes_do_not_reset_last_interaction():
    import yaml

    numbers = yaml.safe_load(_read("number.yaml"))["number"]
    for timeout_id in (
        "brightness_full",
        "brightness_dim",
        "duration_dim",
        "timeout_dim",
        "timeout_display_off",
    ):
        number = next(number for number in numbers if number["id"] == timeout_id)
        assert "on_value" not in number

    interval = _read("interval.yaml")
    assert interval.count("id(update_display).execute();") == 1
    assert "id(check_display" not in interval


def test_last_interaction_uses_one_rollover_safe_clock():
    import yaml

    globals_config = yaml.safe_load(_read("globals.yaml"))["globals"]
    clock = next(value for value in globals_config if value["id"] == "last_interaction_ms")
    assert clock["type"] == "uint32_t"
    assert clock["restore_value"] is False
    initialized = next(
        value for value in globals_config if value["id"] == "interaction_timer_initialized"
    )
    assert initialized["type"] == "bool"
    assert initialized["initial_value"] == "false"

    interval = _read("interval.yaml")
    assert "id(interaction_age_ms) = millis() - id(last_interaction_ms);" in interval
    assert "if (!id(interaction_timer_initialized))" in interval
    assert "id(last_interaction_ms) = millis();" in interval
    assert interval.index("interaction_age_ms") < interval.index("update_display")

    display = _read("scripts_display.yaml")
    interaction = _read("scripts_interaction.yaml")
    assert display.count("id(interaction_age_ms) / 1000.0f") == 1
    assert "millis() / 100" not in display + interaction
    assert "update_last_interaction" not in display + interaction
    assert (
        "id(last_interaction_ms) = millis() - static_cast<uint32_t>(offset) * 1000U;" in interaction
    )
    assert "id: reset_interaction_timer" in interaction
    interaction_state = _read("scripts_interaction.yaml")
    assert "id(reset_interaction_timer).execute(0);" in interaction_state
    assert "if (is_touch)" in interaction_state
    touch_sensors = (
        _read("sensor.yaml").split("# Touch X coordinates")[1].split("# Brightness of display")[0]
    )
    assert "reset_interaction_timer" not in touch_sensors

    # Connection changes, config changes, and serial recovery are not activity.
    assert "reset_last_interaction" not in _read("scripts_connection.yaml")
    assert "reset_last_interaction" not in display
    assert "reset_last_interaction" not in _read("display.yaml").split("on_buffer_overflow:")[1]


def _script_lambda(file_name: str, script_id: str) -> str:
    scripts = _load_tagged(ROOT / file_name)["script"]
    script = next(script for script in scripts if script["id"] == script_id)
    return script["then"][0]["lambda"]


def test_display_scripts_are_one_state_machine():
    """Display-off, dimming and the state label come from one 100 ms script."""
    scripts = _load_tagged(ROOT / "scripts_display.yaml")["script"]
    ids = [script["id"] for script in scripts]
    assert "update_display" in ids
    assert "check_display" not in ids
    assert "check_display_state" not in ids
    for name in ("scripts_display.yaml", "scripts_interaction.yaml"):
        assert "check_page" not in _read(name)

    interval = _read("interval.yaml")
    assert interval.count("id(update_display).execute();") == 1
    assert "id(check_display).execute();" not in interval
    assert "id(check_display_state).execute();" not in interval
    assert "id(check_page).execute();" not in interval


def test_legacy_timeout_event_is_removed_from_firmware_yaml():
    for path in ROOT.parent.rglob("*.yaml"):
        if any(part.startswith(".") for part in path.relative_to(ROOT.parent).parts):
            continue
        assert "esphome.timeout" not in path.read_text(), path


def test_update_display_turns_the_display_off_without_auto_dimming():
    """Display-off is independent of dimming: it may not sit behind its switch."""
    display = _script_lambda("scripts_display.yaml", "update_display")
    assert "if (!id(hub_connection) || !id(use_auto_dimming).state)" not in display
    assert "if (!id(hub_connection)) {" in display

    off = display.split(
        "id(use_auto_display_off).state && timeout_off_val > 0 && age > timeout_off_val", 1
    )
    assert len(off) == 2
    assert "target_brightness = 0;" in off[1]

    dim = display.split(
        "id(use_auto_dimming).state && timeout_dim_val > 0 && age > timeout_dim_val", 1
    )
    assert len(dim) == 2
    assert "target_brightness = int(id(brightness_dim).state);" in dim[1]

    # The state label follows the ramp end, as it did in check_display_state.
    assert "age > (timeout_off_val + duration_dim_val)" in display
    assert "age > (timeout_dim_val + duration_dim_val)" in display


def test_the_firmware_no_longer_knows_about_pages():
    switches = _load_tagged(ROOT / "switch.yaml")["switch"]
    assert not any(switch.get("name") == "Use Auto-Page" for switch in switches)
    assert "use_auto_page" not in _read("switch.yaml")

    numbers = _load_tagged(ROOT / "number.yaml")["number"]
    assert not any(number.get("name") == "Timeout Page" for number in numbers)
    assert "timeout_page" not in _read("number.yaml")


def test_a_touched_widget_counts_as_interaction():
    """The coordinate poll runs every 200 ms and can miss a short tap."""
    display = _load_tagged(ROOT / "display.yaml")["display"]
    on_touch = display[0]["on_touch"]["then"][0]["lambda"]
    reset = on_touch.index("id(reset_interaction_timer).execute(0);")
    assert reset < on_touch.index('execute("esphome.component", event);')
    assert reset < on_touch.index("if (touch_event == 1)")


def test_display_model_uses_numeric_input_instead_of_slider():
    import yaml

    numbers = yaml.safe_load(_read("number.yaml"))["number"]
    display_model = next(number for number in numbers if number["id"] == "display_model")
    assert display_model["mode"] == "box"


def test_current_page_sensor_names_match_the_hub_page_mapping():
    """The firmware names the shown page itself; its table must follow the HMI."""
    import re

    from nspanel_haui.haui.mapping.panel import PAGE_MAPPING

    sensors = _read("sensor.yaml")
    table = re.search(r"PAGE_NAMES\[\] = \{(.*?)\};", sensors, re.DOTALL)
    assert table is not None
    names = re.findall(r'"([^"]+)"', table.group(1))
    assert names == [PAGE_MAPPING[page_id] for page_id in range(len(PAGE_MAPPING))]
    assert "id(current_page).publish_state(" in sensors


def test_current_page_sensors_are_exposed_but_disabled_by_default():
    import yaml

    config = yaml.safe_load(_read("sensor.yaml"))
    current_page = next(s for s in config["text_sensor"] if s.get("id") == "current_page")
    page_number = next(s for s in config["sensor"] if s.get("id") == "page")
    for sensor in (current_page, page_number):
        assert sensor["disabled_by_default"] is True
        assert not sensor.get("internal", False)
    assert page_number["name"] == "Current Page Number"


def test_touch_and_brightness_sensors_are_disabled_by_default():
    """The firmware uses both values itself; the entities are diagnostics only."""
    import yaml

    config = yaml.safe_load(_read("sensor.yaml"))
    touch = next(s for s in config["binary_sensor"] if s.get("id") == "touch")
    brightness = next(s for s in config["sensor"] if s.get("id") == "brightness")
    for sensor in (touch, brightness):
        assert sensor["disabled_by_default"] is True
        assert not sensor.get("internal", False)
