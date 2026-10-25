"""QR code page."""

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
    page.texts = {}
    page.set_component_text = lambda component, text: page.texts.__setitem__(component.name, text)
    page._build_items_from_panel = lambda panel, key: items
    page._render_items = lambda items: rendered.append("items")
    page._render_text = lambda panel: rendered.append("text")
    page._apply_zoom_state = lambda: None
    page.render_panel(_Panel(config))
    page.rendered = rendered
    return page


def test_configured_items_replace_network_text():
    """Show network info applies only when no custom items are configured."""
    assert _render({"show_info": True}, ["item"]).rendered == ["items"]


def test_network_text_without_items():
    assert _render({}, []).rendered == ["text"]


def test_title_is_shown_with_text_items_too():
    page = _render({}, ["item"])

    assert page.texts["tTitle"] == "Wifi"
