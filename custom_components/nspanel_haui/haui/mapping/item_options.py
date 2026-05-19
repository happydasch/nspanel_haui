"""Standard per-item override options shared by HAUIItem and HAUIEntity."""

from __future__ import annotations

from .descriptor import PageOption


class ItemOptions:
    """Standard per-item override options available to all item-based panels.

    These define the common overrides (name, icon, color, value, state, etc.)
    that users can configure per item in any item_list.  Pages that need
    additional per-item options call ``ItemOptions.extend_with(extra)``.
    """

    STANDARD_OPTIONS: list[PageOption] = [
        PageOption(
            key="item",
            kind="item",
            label="Entity",
            description="Entity to display and control.",
        ),
        PageOption(
            key="popup_key",
            kind="generic",
            label="Popup override",
            description="Override the default popup panel type for this item.",
        ),
        PageOption(
            key="state",
            kind="generic",
            label="State override",
            description=(
                "Override the entity state. "
                "Use an attribute key to read state from an entity attribute."
            ),
        ),
        PageOption(
            key="value",
            kind="generic",
            label="Value override",
            description="Override the displayed value of this item.",
        ),
        PageOption(
            key="name",
            kind="generic",
            label="Name override",
            description="Override the displayed name of this item.",
        ),
        PageOption(
            key="icon",
            kind="icon",
            label="Icon override",
            description="Override the icon of this item.",
        ),
        PageOption(
            key="color",
            kind="color",
            label="Color override",
            description="Override the color of this item.",
        ),
    ]

    @classmethod
    def extend_with(cls, extra: list[PageOption]) -> list[PageOption]:
        """Return standard options + extra per-item options for a page type.

        Args:
            extra: Additional PageOption entries that a page type supports
                   as per-item overrides (e.g. grid's color_mode, text_color).

        Returns:
            Combined list of standard + extra options.
        """
        return list(cls.STANDARD_OPTIONS) + list(extra)
