"""The committed HMIs match their layout specs (``scripts/hmi_layout/gen_layout.py``).

``--check`` reports widgets missing on either side and every attribute value
that differs from the spec. For the portrait HMI it also requires the same
widgets as the landscape project, with the same touch settings (Send Component
ID), so a widget or touch that exists in only one TFT fails here.
"""

from __future__ import annotations

import pytest

from scripts.hmi_layout import gen_layout


@pytest.mark.parametrize(
    ("args", "spec"),
    [
        (["--check"], "landscape_layout"),
        (["--spec", "portrait", "--check"], "portrait_layout"),
    ],
    ids=["landscape", "portrait"],
)
def test_committed_hmi_matches_its_spec(args, spec, capsys):
    result = gen_layout.main(args)

    out = capsys.readouterr().out
    assert result == 0, out
    assert f"spec {spec} consistent" in out
