"""QR code page."""

from types import SimpleNamespace

from nspanel_haui.haui.page.qr import QRPage


class _Panel:
    def __init__(self, config):
        self.config = config

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_title(self):
        return "Wifi"


def _render(config, items):
    page = QRPage.__new__(QRPage)
    rendered = []
    page.app = SimpleNamespace(device=SimpleNamespace(is_portrait=False))
    page.texts = {}
    page.set_component_text = lambda component, text: page.texts.__setitem__(component.name, text)
    page._build_items_from_panel = lambda panel, key: items
    page._render_items = lambda items: rendered.append("items")
    page._render_text = lambda panel: rendered.append("text")
    page._apply_zoom_state = lambda: None
    page.render_panel(_Panel(config))
    page.rendered = rendered
    return page


def test_qr_info_text_uses_device_palette_for_light_theme():
    page = QRPage.__new__(QRPage)
    colors = {"text": 1234, "text_inactive": 5678}
    page.get_color = lambda key: colors[key]
    updated = []
    page.set_component_text_color = lambda component, color: updated.append((component, color))

    page._set_info_text_colors()

    assert updated == [
        (page.COMPONENTS.q1_title, 1234),
        (page.COMPONENTS.q1_text, 5678),
        (page.COMPONENTS.q1_text_add, 5678),
        (page.COMPONENTS.q2_title, 1234),
        (page.COMPONENTS.q2_text, 5678),
        (page.COMPONENTS.q2_text_add, 5678),
    ]


def test_big_qr_zoom_button_uses_header_accent_color() -> None:
    page = QRPage.__new__(QRPage)
    colors = {"component_text": 123, "header_accent": 456}
    updates = []
    page._is_big = True
    page._has_text = False
    page.hide_component = lambda component: None
    page.show_component = lambda component: None
    page.get_color = lambda key: colors[key]
    page.update_function_component = lambda fnc_id, **kwargs: updates.append((fnc_id, kwargs))

    page._apply_zoom_state()

    assert updates == [(page.FNC_BTN_R_SEC, {"visible": True, "color": colors["header_accent"]})]


def test_configured_items_replace_network_text():
    """Show network info applies only when no custom items are configured."""
    assert _render({"show_info": True}, ["item"]).rendered == ["items"]


def test_network_text_without_items():
    assert _render({}, []).rendered == ["text"]


def test_title_is_shown_with_text_items_too():
    page = _render({}, ["item"])

    assert page.texts["tTitle"] == "Wifi"
