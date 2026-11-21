"""Tests for the firmware size guard (scripts/verify_firmware/check_size.py)."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_firmware.check_size import (
    check,
    find_partitions_csv,
    newest_image,
    parse_app_partitions,
    smallest_app_partition,
)

PARTITION_CSV = """\
# Name, Type, SubType, Offset, Size, Flags
otadata, data, ota, , 0x2000,
phy_init, data, phy, , 0x1000,
app0, app, ota_0, , 0x1C0000,
app1, app, ota_1, , 0x1C0000,
nvs, data, nvs, , 0x70000,
"""


def test_parse_app_partitions_ignores_other_types_and_comments():
    assert parse_app_partitions(PARTITION_CSV) == [("app0", 0x1C0000), ("app1", 0x1C0000)]


def test_parse_app_partitions_accepts_decimal_and_suffixes():
    text = "app0, app, ota_0, , 1835008,\napp1, app, ota_1, , 1792K,\n"
    assert parse_app_partitions(text) == [("app0", 1835008), ("app1", 1792 * 1024)]


def test_smallest_app_partition(tmp_path: Path):
    path = tmp_path / "partitions.csv"
    path.write_text(
        "app0, app, ota_0, , 0x200000,\napp1, app, ota_1, , 0x1C0000,\n", encoding="utf-8"
    )
    assert smallest_app_partition(path) == 0x1C0000


def test_smallest_app_partition_returns_none_without_apps(tmp_path: Path):
    path = tmp_path / "partitions.csv"
    path.write_text("nvs, data, nvs, , 0x70000,\n", encoding="utf-8")
    assert smallest_app_partition(path) is None


def test_check_fails_at_the_limit(tmp_path: Path):
    image = tmp_path / "firmware.ota.bin"
    image.write_bytes(b"x" * 920)
    code, message = check(image, 1000)
    assert code == 1
    assert "92%" in message


def test_check_warns_between_the_thresholds(tmp_path: Path):
    image = tmp_path / "firmware.ota.bin"
    image.write_bytes(b"x" * 850)
    code, message = check(image, 1000)
    assert code == 0
    assert "warning" in message


def test_check_passes_below_the_warning(tmp_path: Path):
    image = tmp_path / "firmware.ota.bin"
    image.write_bytes(b"x" * 500)
    code, message = check(image, 1000)
    assert code == 0
    assert "flash 50.0%" in message


def test_newest_image_prefers_the_ota_image(tmp_path: Path):
    build = tmp_path / "build"
    build.mkdir()
    ota = build / "firmware.ota.bin"
    ota.write_bytes(b"ota")
    (build / "firmware.bin").write_bytes(b"factory")
    assert newest_image(tmp_path) == ota


def test_find_partitions_csv_walks_up_from_the_image(tmp_path: Path):
    build = tmp_path / "build"
    build.mkdir()
    image = build / "firmware.ota.bin"
    image.write_bytes(b"x")
    partitions = tmp_path / "partitions.csv"
    partitions.write_text(PARTITION_CSV, encoding="utf-8")
    assert find_partitions_csv(image, tmp_path) == partitions
