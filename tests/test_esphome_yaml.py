"""Static checks for the ESPHome YAML (no ESPHome install needed)."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent / "esphome" / "nspanel_haui"


def _read(name: str) -> str:
    return (ROOT / name).read_text()


def _ms(text: str, key: str) -> int | None:
    """An option whose value is written as ``<n>ms``, or None when it is not set."""
    match = re.search(rf"^\s+{key}:\s*'?(\d+)\s*ms'?\s*$", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def _count(text: str, key: str) -> int | None:
    """An option whose value is a plain integer, or None when it is not set."""
    match = re.search(rf"^\s+{key}:\s*(\d+)\s*$", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def _component_default_ms(key: str) -> int | None:
    """The default the vendored component declares for ``key`` (e.g. max_queue_age)."""
    source = (ROOT.parent / "nextion_patch" / "nextion" / "display.py").read_text()
    match = re.search(rf'{key.upper()},\s*default="(\d+)ms"', source)
    return int(match.group(1)) if match else None


def _load_tagged(path: Path) -> dict:
    """Parse ESPHome YAML, keeping custom tags (``!remove`` …) as ``"!<tag>"``."""

    class Loader(yaml.SafeLoader):
        pass

    Loader.add_multi_constructor("!", lambda loader, suffix, node: f"!{suffix}")
    return yaml.load(path.read_text(), Loader=Loader)  # noqa: S506 - SafeLoader subclass


def _substitution(text: str, key: str) -> str:
    """A "substitutions:" entry of a package file, as written."""
    match = re.search(rf"^\s+{key}:\s*'([^']*)'", text, re.MULTILINE)
    assert match is not None, f"{key} is not a substitution"
    return match.group(1)


def _script_parameters(steps: object) -> list[tuple[str, str, object]]:
    """Every ``script.execute`` parameter in ``steps``: (script id, name, value)."""

    found: list[tuple[str, str, object]] = []
    if isinstance(steps, list):
        for step in steps:
            found += _script_parameters(step)
    elif isinstance(steps, dict):
        for key, value in steps.items():
            if key == "script.execute" and isinstance(value, dict):
                found += [
                    (str(value.get("id")), str(name), parameter)
                    for name, parameter in value.items()
                    if name != "id"
                ]
            else:
                found += _script_parameters(value)
    return found


def test_hub_availability_reset_on_last_client_disconnect():
    api = _read("api.yaml")
    disconnected = api.split("on_client_disconnected:")[1].split("actions:")[0]
    assert "id(hub_availability) = global_api_server->is_connected();" in disconnected


def test_min_esphome_version_declared():
    """min_version and the firmware pin must move together."""
    pin = re.search(
        r"^esphome==(\S+)$",
        (ROOT.parent.parent / "requirements-esphome.txt").read_text(),
        re.MULTILINE,
    )
    assert pin is not None
    assert f"min_version: {pin.group(1)}" in _read("base.yaml")


def test_web_server_is_optional_and_off_by_default():
    """The web server costs flash/RAM; only the dev build enables it."""
    # base.yaml keeps only a commented example, so the shipped build omits it.
    assert not re.search(r"^web_server:", _read("base.yaml"), re.MULTILINE)
    # The local development build keeps the web UI for diagnostics.
    dev = (ROOT.parent / "nspanel_haui_dev.yaml").read_text()
    assert re.search(r"^web_server:", dev, re.MULTILINE)
    # The universal image bakes no web credentials because it has no web server.
    universal = (ROOT.parent / "nspanel_haui_universal.yaml").read_text()
    assert "web_username" not in universal


def test_the_uart_starts_at_the_tft_baud_and_scans_down():
    """The shipped TFT boots at 921600; older TFTs are found by the boot scan."""
    hardware = _read("hardware.yaml")
    assert re.search(r"^\s+baud_rate:\s*921600\s*$", hardware, re.MULTILINE)
    baud_script = _read("display_baud.yaml")
    assert "restore_value: true" in baud_script
    assert "921600" in baud_script
    assert "set_baud_rate(id(haui_display_baud))" in baud_script
    # A failed scan must not strand an older panel on the rate it did not answer
    # at: 115200 is what every TFT before 0.4.6 and the stock one use.
    assert "set_baud_rate(115200)" in baud_script
    # A power-cycled display is back on its power-on defaults and returns no
    # `get` reply, so the probe has to re-enable returns itself.
    assert "bkcmd=3" in baud_script
    assert "retry_display_baud" in baud_script
    assert "is_detected()" in baud_script
    assert "screen_power" in baud_script
    assert "display_baud: !include display_baud.yaml" in _read("packages.yaml")


def test_only_the_boot_applies_the_remembered_baud():
    """A retry must keep the rate the last scan settled on.

    The boot check applies the remembered rate, so a panel that already found
    its display's older rate starts there. A retry must not repeat that: it
    would overwrite the 115200 fallback of a failed scan before that rate got
    the retry's window, which is the one thing the fallback is for.
    """
    baud_script = _read("display_baud.yaml")
    boot, _, scripts = baud_script.partition("script:\n")
    assert "set_baud_rate(id(haui_display_baud))" in boot
    assert "set_baud_rate(id(haui_display_baud))" not in scripts


def test_firmware_reports_required_tft_version_separately():
    version = _read("version.yaml")
    state_script = _read("scripts_event.yaml")
    assert "tft_version:" in version
    assert 'auto tft_required_version = "$tft_version";' in state_script
    assert 'root["tft_required_version"] = tft_required_version;' in state_script


def test_firmware_reports_the_display_link_rate() -> None:
    """The editor shows the display link's speed, so the state has to carry it."""
    state_script = _read("scripts_event.yaml")
    # Only a display that answers has a link: reporting the rate the UART sits
    # at with nothing on the other end would look like a working slow panel.
    assert re.search(
        r"display_baud_val = id\(haui_disp\)\.is_detected\(\)\s*\?\s*"
        r"int\(id\(haui_uart\)\.get_baud_rate\(\)\) : 0;",
        state_script,
    )
    assert 'root["display_baud"] = display_baud_val;' in state_script
    baud_script = _read("display_baud.yaml")
    # Both detection paths report it: the boot check (usually before the hub
    # connected) and the scan, which may settle on a rate much later.
    assert baud_script.count("id(publish_device_state).execute();") == 2


def test_http_request_buffers_fit_github_redirect_headers():
    """The firmware update entity needs room for GitHub's ~5.4 KB headers."""
    base = _read("base.yaml")
    assert re.search(r"^\s+buffer_size_rx:\s*8192\s*$", base, re.MULTILINE)
    assert re.search(r"^\s+buffer_size_tx:\s*2048\s*$", base, re.MULTILINE)


def _pace_ms() -> int:
    """The pacer's spacing, in ms, from the one substitution that holds it.

    ``display.yaml`` names ``${command_spacing_ms}`` (base.yaml) rather than
    repeating the number, because the draw path restores the same value when a
    program ends (``image.yaml``) - a second literal would be free to drift.
    """
    display = _read("display.yaml")
    assert re.search(
        r"^\s+command_spacing:\s*\$\{command_spacing_ms\}ms\s*$", display, re.MULTILINE
    )
    return int(_substitution(_read("base.yaml"), "command_spacing_ms"))


def test_command_spacing_is_enabled_to_prevent_nextion_rx_overflow():
    assert _pace_ms() > 0


def test_loop_interval_does_not_outrun_the_command_spacing():
    """The pacer sends one command per component phase, so the phase is the pace.

    ``command_spacing`` is compared against a timestamp that is constant inside
    a component phase, and ESPHome gates the phase on ``loop_interval`` (16 ms
    by default). A loop interval above the spacing therefore makes every render
    slower than configured — 16 ms per command is a panel page taking seconds.
    """
    loop = _ms(_read("base.yaml"), "loop_interval")
    spacing = _pace_ms()
    assert loop is not None
    assert loop <= spacing


def test_a_full_command_queue_drains_before_its_entries_expire():
    """``max_queue_age`` must not purge a command the pacer never sent.

    A full queue drains at one command per component phase, so the age limit has
    to cover ``max_queue_size × command_spacing``. At 16 ms per command a full
    queue needed 12.8 s against the component's 8 s default, and the tail of a
    heavy render was dropped unsent instead of merely arriving late.
    """
    size = _count(_read("display.yaml"), "max_queue_size")
    spacing = _pace_ms()
    age = _ms(_read("display.yaml"), "max_queue_age")
    if age is None:
        age = _component_default_ms("max_queue_age")
    assert size is not None and age is not None
    assert size * spacing <= age, (
        f"a full queue needs {size * spacing} ms to drain but entries expire after {age} ms"
    )


def test_tft_upload_tx_buffer_fits_the_github_redirect():
    """GitHub redirects release TFTs to a ~870-character signed URL.

    The redirected request line overflows the 512-byte ESP-IDF default TX
    buffer, so every hub TFT install failed before the first byte.
    """
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


def test_maintenance_entities_are_disabled_by_default():
    """Restart Display and Screen Power are rarely needed."""
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
    base = yaml.safe_load(_read("base.yaml"))
    platforms = {ota["platform"]: ota for ota in base["ota"]}
    assert set(platforms) == {"esphome", "http_request"}
    for ota in platforms.values():
        assert {"script.execute": "suspend_activities"} in ota["on_begin"]
    assert {"script.execute": "suspend_activities"} in base["esphome"]["on_shutdown"]

    upload = _read("scripts_common.yaml").split("- id: prepare_tft_upload")[1]
    assert upload.index("script.execute: suspend_activities") < upload.index("upload_tft()")


def test_the_panel_reports_a_tft_upload_it_could_not_start():
    """A failed upload names its cause; a successful one reboots instead.

    Without the failure event the hub could only guess from its install
    timeout, twenty minutes later.
    """
    upload = _read("scripts_common.yaml").split("- id: prepare_tft_upload")[1]
    assert upload.index('"esphome.tft_upload_started"') < upload.index("upload_tft()")
    assert upload.index("upload_tft()") < upload.index('"esphome.tft_upload_failed"')
    # The reason the uploader recorded travels with the event.
    assert "tft_upload_error()" in upload


def test_a_transfer_the_display_cannot_hold_falls_back_to_the_safe_baud():
    """The 921600 link is fast; a display that cannot transfer at it is not lost.

    A failed transfer leaves the Nextion waiting for data, so the retry has to
    power-cycle it; a successful one reboots, which is why the fallback only
    ever runs after a failure.
    """
    upload = _read("scripts_common.yaml").split("- id: prepare_tft_upload")[1]
    assert upload.index("upload_tft()") < upload.index("upload_tft(115200)")
    assert "switch.turn_off: screen_power" in upload
    assert "switch.turn_on: screen_power" in upload
    # The retry re-runs the transfer the hub is waiting on, so the install
    # timeout is re-armed the same way the first attempt armed it.
    assert upload.count('"esphome.tft_upload_started"') == 2
    assert '"esphome.tft_upload_failed"' in upload


def test_only_a_failure_the_display_caused_is_retried():
    """A download or heap error repeats at any rate, and a retry costs a transfer."""
    upload = _read("scripts_common.yaml").split("- id: prepare_tft_upload")[1]
    guard = upload.split("- if:")[1].split("then:")[0]
    assert "tft_upload_display_fault()" in guard
    # Nothing to fall back to when the link already runs at the safe rate.
    assert "get_baud_rate() > 115200" in guard

    patch = ROOT.parent / "nextion_patch" / "nextion"
    # The display's own failures are the ones a lower rate can fix; the vendor's
    # other paths (a `404`, an exhausted heap) stay unmarked.
    assert (
        'return fail_display("the display refused the upload (power-cycle it to recover)");'
        in (patch / "nextion_upload_esp32.cpp").read_text()
    )
    source = (patch / "nextion_upload_esp32.cpp").read_text()
    assert "tft_upload_display_fault_ = true;" in source
    # Cleared per attempt, so a stale mark cannot make a download error look
    # like a rate the display cannot hold.
    assert "tft_upload_display_fault_ = false;" in source
    assert "bool tft_upload_display_fault() const" in (patch / "nextion.h").read_text()


def test_a_tft_upload_asks_a_power_cycled_display_for_returns():
    """The retry power-cycles the display, which resets it to no command results.

    Same lesson as the boot scan's probe: a display that was just power-cycled
    answers nothing without `bkcmd=3`, so the upload re-enables returns with its
    other wake-up commands.
    """
    source = (ROOT.parent / "nextion_patch" / "nextion" / "nextion_upload_esp32.cpp").read_text()
    upload = source.split("bool Nextion::upload_tft(")[1]
    wake_up = upload[: upload.index("whmi-wris")]
    assert 'this->send_command_("bkcmd=3");' in wake_up


def test_native_ota_is_encrypted_with_the_api_key():
    """ESPHome warns that an OTA password next to an api key wastes flash and
    RAM (#81).  A bare ``encryption:`` inherits ``api_encryption_key``.
    """
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


def test_the_nextion_patch_travels_with_the_package_that_uses_it():
    """The patch and the YAML that calls it are always one tree.

    A git source let a build pair a fresh ``display.yaml`` with an older patch
    ("[tft_upload_http_buffer_size_tx] is an invalid option"), and once the patch
    grew C++ the YAML calls, a panel installed from ``dev`` failed to compile
    against the patch of ``master``: "no member named
    'tft_upload_display_fault'". A local path resolves against the config's own
    directory, so a remote package compiles the patch fetched beside it.
    """
    for config in ("nspanel_haui.yaml", "nspanel_haui_dev.yaml", "nspanel_haui_universal.yaml"):
        text = (ROOT.parent / config).read_text()
        block = text.split("external_components:")[1].split("packages:")[0]
        assert "type: local" in block, config
        assert "path: nextion_patch" in block, config
        # The path is relative to the config, so it must exist next to it.
        assert (ROOT.parent / "nextion_patch" / "nextion" / "__init__.py").is_file(), config
    # No config may fetch the patch by branch again.
    for config in ("nspanel_haui.yaml", "nspanel_haui_dev.yaml", "nspanel_haui_universal.yaml"):
        block = (
            (ROOT.parent / config)
            .read_text()
            .split("external_components:")[1]
            .split("packages:")[0]
        )
        assert "ref:" not in block, config


def test_the_installed_package_fetches_the_stable_branch():
    """A ref naming a branch that is not in the repository fails every build.

    ``install.yaml``'s remote package is the one remaining git source, so it must
    name `master`, the stable one: an installed panel builds the released
    firmware, while `dev` carries unreleased code for the development channel.
    """
    install = (ROOT.parent / "install.yaml").read_text()
    assert "ref: master" in install.split("packages:")[1]


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


def test_hub_connection_closed_is_forced_but_last_client_disconnect_is_not():
    api = _read("api.yaml")
    hub_close = api.split("- action: hub_connection_closed", 1)[1].split(
        "# HA requests device state", 1
    )[0]
    assert "force: 1" in hub_close
    client_disconnect = api.split("on_client_disconnected:", 1)[1].split("actions:", 1)[0]
    assert "force: 0" in client_disconnect


def test_connection_grace_reuses_the_dimming_timeout():
    display = _script_lambda("scripts_display.yaml", "update_display")
    connection = _read("scripts_connection.yaml")
    assert "hub_state_change_ms" in display
    assert "since_connection_change" in display
    assert "timeout_dim_val" in display
    assert "connection_grace" in display
    assert "bool connection_grace = timeout_dim_val > 0" in display
    assert "id(hub_state_change_ms) = millis();" in connection
    assert "new_state = 1;" in display
    assert "target_brightness = min(target_brightness, int(id(brightness_dim).state));" in display


def test_disconnected_display_never_turns_off_or_hardware_sleeps():
    display = _script_lambda("scripts_display.yaml", "update_display")
    assert "id(display_off).execute()" not in display
    assert "id(haui_disp).sleep(true)" not in display
    assert "wakeup_page" not in display
    assert "brightness_dim" in display
    disconnected = display.split("if (!id(hub_connection))", 1)[1].split(
        "} else if (connection_grace)", 1
    )[0]
    assert "target_brightness = 0" not in disconnected


def test_auto_display_off_switch_is_the_live_gate_for_connected_off():
    display = _script_lambda("scripts_display.yaml", "update_display")
    connected = display.split("} else if (connection_grace)", 1)[1].split("// Hardware sleep", 1)[0]
    assert "id(use_auto_display_off).state" in connected
    assert "else if (!id(use_auto_display_off).state && current_state == 0)" in connected
    brightness = display.split("// Desired brightness", 1)[1]
    assert "id(use_auto_display_off).state" in brightness
    assert (
        "else if (id(use_auto_display_off).state && timeout_off_val > 0 && age > timeout_off_val)"
        in brightness
    )


def test_disconnected_dim_uses_the_dim_timeout_not_the_ramp_or_auto_switch():
    display = _script_lambda("scripts_display.yaml", "update_display")
    grace = display.split("bool connection_grace", 1)[1].split(";", 1)[0]
    assert "since_connection_change <= timeout_dim_val" in grace
    assert "duration_dim_val" not in grace
    disconnected_state = display.split("if (!id(hub_connection))", 1)[1].split(
        "} else if (connection_grace)", 1
    )[0]
    assert "timeout_dim_val > 0 && !connection_grace" in disconnected_state
    assert "use_auto_dimming" not in disconnected_state
    assert "use_auto_display_off" not in disconnected_state


def test_a_live_switch_change_is_read_on_each_timeout_check():
    display = _script_lambda("scripts_display.yaml", "update_display")
    assert display.count("id(use_auto_display_off).state") >= 3
    assert "static bool" not in display
    assert "bool use_auto_display_off" not in display


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
    assert "target_brightness = min(target_brightness, int(id(brightness_dim).state));" in dim[1]

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


def test_current_page_sensor_names_match_the_hub_page_mapping():
    """The firmware names the shown page itself; its table must follow the HMI."""
    from custom_components.nspanel_haui.haui.mapping.panel import PAGE_MAPPING

    sensors = _read("sensor.yaml")
    table = re.search(r"PAGE_NAMES\[\] = \{(.*?)\};", sensors, re.DOTALL)
    assert table is not None
    names = re.findall(r'"([^"]+)"', table.group(1))
    # By id, not by position: the table is the display's page list, so it also
    # names a page no panel type renders yet (an HMI page can land before its
    # page class does), and such an id is simply absent from PAGE_MAPPING.
    for page_id, page_name in PAGE_MAPPING.items():
        assert page_id < len(names), f"the table is too short for page id {page_id}"
        assert names[page_id] == page_name
    assert "id(current_page).publish_state(" in sensors


def test_current_page_sensors_are_exposed_but_disabled_by_default():
    config = yaml.safe_load(_read("sensor.yaml"))
    current_page = next(s for s in config["text_sensor"] if s.get("id") == "current_page")
    page_number = next(s for s in config["sensor"] if s.get("id") == "page")
    for sensor in (current_page, page_number):
        assert sensor["disabled_by_default"] is True
        assert not sensor.get("internal", False)
    assert page_number["name"] == "Current Page Number"


def test_touch_and_brightness_sensors_are_disabled_by_default():
    """The firmware uses both values itself; the entities are diagnostics only."""
    config = yaml.safe_load(_read("sensor.yaml"))
    touch = next(s for s in config["binary_sensor"] if s.get("id") == "touch")
    brightness = next(s for s in config["sensor"] if s.get("id") == "brightness")
    for sensor in (touch, brightness):
        assert sensor["disabled_by_default"] is True
        assert not sensor.get("internal", False)


def test_relays_restore_their_state_after_a_firmware_update():
    """ALWAYS_OFF switched every connected load off on each OTA reboot."""
    switches = {switch["id"]: switch for switch in yaml.safe_load(_read("switch.yaml"))["switch"]}
    for relay in ("relay_left", "relay_right"):
        assert switches[relay]["restore_mode"] == "RESTORE_DEFAULT_OFF"


def test_packages_include_the_image_drawing_config():
    assert "image: !include image.yaml" in _read("packages.yaml")


def test_the_firmware_declares_the_draw_runs_action():
    """The hub can only paint an image through this action's program variable."""
    api = _load_tagged(ROOT / "api.yaml")
    actions = {action["action"]: action for action in api["api"]["actions"]}
    assert "draw_runs" in actions
    assert actions["draw_runs"]["variables"] == {"program": "string"}
    assert "id: haui_draw_runs" in _read("api.yaml")
    # A bare ``program: program`` is compiled as the literal word "program".
    executed = actions["draw_runs"]["then"][0]["script.execute"]
    assert executed["program"] == "!lambda"


def test_no_api_action_passes_one_of_its_variables_as_a_bare_word():
    """ESPHome compiles a script parameter outside a lambda as a literal string.

    ``program: program`` therefore handed the display the seven characters
    "program": it was queued as one bogus command and reported as a drawn image,
    so every variable goes through ``!lambda`` (as ``goto_page``, ``req_val`` and
    ``req_txt`` always have).
    """
    offenders = []
    for action in _load_tagged(ROOT / "api.yaml")["api"]["actions"]:
        variables = set(action.get("variables") or {})
        offenders += [
            f"{action['action']}: {script}({name}={value})"
            for script, name, value in _script_parameters(action.get("then"))
            if isinstance(value, str) and value in variables
        ]
    assert not offenders, f"wrap the value in !lambda 'return x;': {offenders}"


def test_the_hub_and_firmware_agree_on_the_command_spacing():
    """The draw path plans at the pacer's pace, so the two numbers are one.

    ``draw_wire.COMMAND_SPACING_MS`` is what the hub multiplies a run budget by;
    ``base.yaml``'s ``command_spacing_ms`` is what the panel actually paces at.
    A drift between them makes every ``quality`` time estimate wrong.
    """
    from custom_components.nspanel_haui.haui.utils.draw_wire import COMMAND_SPACING_MS

    assert COMMAND_SPACING_MS == _pace_ms()


def test_a_draw_slice_the_hub_builds_is_never_over_the_firmware_limit():
    """The hub slices a pass; the device's own backstop must be above one slice."""
    from custom_components.nspanel_haui.haui.utils.draw_wire import DRAW_SLICE_CHARS

    firmware_max = int(_substitution(_read("image.yaml"), "draw_program_max"))
    assert firmware_max >= DRAW_SLICE_CHARS


def test_the_firmware_decodes_a_packed_run_back_into_a_fill():
    """The wire format carries five base-36 numbers, not the display command."""
    image = _read("image.yaml")

    # The enqueue lambda rebuilds "fill x,y,w,h,colour" from five numbers, and a
    # run it cannot decode is counted instead of sent. Verified against the hub's
    # packer by compiling the lambda on the host (haui/utils/draw_wire.pack_run).
    assert '"fill %ld,%ld,%ld,%ld,%ld"' in image
    assert "base 36" in image
    assert "id(haui_draw_rejected)++" in image


def test_the_firmware_reports_the_draw_format_it_decodes():
    """The hub packs for the format the panel reports, so both payloads carry it.

    A panel that says nothing is sent the display instructions themselves, which
    an older firmware streams as they are - the alternative, packing for a
    firmware without the decoder, painted nothing at all.
    """
    from custom_components.nspanel_haui.haui.utils.draw_wire import DRAW_FORMAT_PACKED

    version = _read("version.yaml")
    assert int(_substitution(version, "draw_format")) == DRAW_FORMAT_PACKED
    events = _read("scripts_event.yaml")
    assert events.count('root["draw_format"]') == 2
    assert events.count("int draw_format_val = ${draw_format};") == 2


def test_a_draw_window_fits_the_display_receive_buffer():
    """A draw runs unpaced, so its window is what the display's buffer holds.

    The window is the fills in flight - unsent or unacknowledged - and the pacer
    no longer slows their arrival: a run is at most the firmware's 40-byte fill
    buffer, so a window of N is at most N × 40 bytes of the Nextion's 1 KB
    receive buffer, leaving room for page commands interleaved with the stream.
    """
    window = int(_substitution(_read("image.yaml"), "draw_window"))
    assert window * 40 <= 1024 / 2
    size = _count(_read("display.yaml"), "max_queue_size")
    assert size is not None and window <= size


def test_one_unpaced_phase_sends_no_more_than_the_draw_window():
    """The window is what one phase writes, and the component's own cap allows it.

    ``max_commands_per_loop`` bounds a phase in which the pacer is off (it never
    binds while the pacer is in force), so it has to be at least the window - and
    a smaller cap would leave the stream idling between phases.
    """
    window = int(_substitution(_read("image.yaml"), "draw_window"))
    per_phase = _count(_read("display.yaml"), "max_commands_per_loop")
    assert per_phase is not None
    assert window <= per_phase


def test_a_draw_streams_unpaced_and_every_way_it_ends_restores_the_pacer():
    """Only a draw leaves the pacer, and its report is the only way back.

    A refusal, a stalled display, a finished program and a page change all end
    in a restored spacing: a pacer left at zero would send page renders as fast
    as the UART takes them.
    """
    image = _read("image.yaml")
    assert int(_substitution(image, "draw_spacing")) < _pace_ms()
    assert "id(haui_disp).set_command_spacing(${draw_spacing})" in image
    report = image.split("id: haui_draw_report", 1)[1]
    assert "set_command_spacing(${command_spacing_ms})" in report
    goto = _read("scripts_display.yaml").split("id: goto_page", 1)[1].split("- id:", 1)[0]
    assert "id(haui_draw_runs).stop();" in goto
    assert "id(haui_draw_enqueue_batch).stop();" in goto
    assert "set_command_spacing(${command_spacing_ms})" in goto


def test_a_run_is_counted_sent_only_when_the_queue_grew():
    """``send_command()`` reports the display's state, not the queued entry.

    A full queue or a failed allocation drops the run without an error; counting
    it would report a gap in the picture as a finished slice.
    """
    image = _read("image.yaml")
    assert "const size_t queued = id(haui_disp).queue_size();" in image
    assert "id(haui_disp).queue_size() <= queued" in image
    assert "the queue dropped a run" in image


def test_a_finished_draw_is_forgotten_so_a_late_overflow_cannot_retry():
    """The report clears the program after building the payload, before publishing."""
    report = _read("image.yaml").split("id: haui_draw_report", 1)[1].split("- id:", 1)[0]
    built = report.index("std::string body")
    cleared = report.index('id(haui_draw_program) = ""')
    published = report.index("publish_event_native")
    assert built < cleared < published
    assert "id(haui_draw_ok) = false;" in report
    assert "id(haui_draw_awaiting) = false;" in report


def test_a_draw_retry_stays_one_shot():
    """The retry's guard must survive ``haui_draw_runs`` resetting its state."""
    scripts = _load_tagged(ROOT / "image.yaml")["script"]
    runs = next(script for script in scripts if script["id"] == "haui_draw_runs")
    assert runs["parameters"] == {"program": "std::string", "retry": "bool"}
    image = _read("image.yaml")
    assert "id(haui_draw_resent) = retry;" in image
    assert "id(haui_draw_runs).execute(id(haui_draw_program), true);" in image
    actions = _load_tagged(ROOT / "api.yaml")["api"]["actions"]
    draw = next(action for action in actions if action["action"] == "draw_runs")
    parameters = [
        (name, value)
        for script, name, value in _script_parameters(draw["then"])
        if script == "haui_draw_runs"
    ]
    # A hub slice is not a retry; only haui_draw_retry passes true.
    assert ("retry", "!lambda") in parameters


def test_the_hub_packs_only_numbers_the_firmware_decoder_accepts():
    """The base-36 decoder is bounded at 65535 per field; the packer must agree."""
    from custom_components.nspanel_haui.haui.utils.draw_wire import pack_run, unpack_run

    for run in (
        "fill 0,0,1,1,0",
        "fill 479,319,1,1,65535",
        "fill 65535,65535,65535,65535,65535",
    ):
        packed = pack_run(run)
        assert all(0 <= int(part, 36) <= 65535 for part in packed.split(","))
        assert unpack_run(packed) == run
    # The decoder rejects a field before it can overflow the packed number.
    assert "field[index] > 65535 / 36" in _read("image.yaml")


def test_a_draw_that_stalls_is_reported_instead_of_polling_forever():
    """A display that stops acknowledging must not hold the pacer off.

    The queue's own ``max_queue_age`` would clear a stuck window after eight
    seconds; the draw fails itself after ``draw_stall_polls`` passes instead, a
    second at one pass per component phase.
    """
    image = _read("image.yaml")
    polls = int(_substitution(image, "draw_stall_polls"))
    poll = _ms(image, "draw_queue_poll")
    assert poll is not None
    assert polls * poll <= 2000
    assert "id(haui_draw_stall_polls) >= ${draw_stall_polls}" in image


def test_a_buffer_overflow_re_sends_the_draw_program():
    """A 0x24 loses the runs in flight; the image must not vanish mid-burst."""
    assert "script.execute: haui_draw_retry" in _read("display.yaml")
    assert "id: haui_draw_retry" in _read("image.yaml")


def test_the_draw_fence_reads_the_same_variable_as_the_res_val_sensor():
    """The fence reply can only arrive after the program's last run was sent."""
    assert "component_name: system.resVal" in _read("image.yaml")
    assert "component_name: system.resVal" in _read("sensor.yaml")
