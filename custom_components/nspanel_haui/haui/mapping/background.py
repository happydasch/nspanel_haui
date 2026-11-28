# backgrounds: name -> picture_id. Picture 0 is the layout grid, not a background.
BACKGROUNDS = {
    "dark": 1,
    "light": 2,
    "modern": 3,
    "cool_glow": 4,
    "warm_glow": 5,
    "dusk": 6,
    "spring": 7,
    "summer": 8,
    "autumn": 9,
    "winter": 10,
    "dog_1": 11,
    "dog_2": 12,
    "cat": 13,
}


BACKGROUND_VARIANTS = {
    "dark": "dark",
    "light": "light",
    "modern": "dark",
    "cool_glow": "dark",
    "warm_glow": "dark",
    "dusk": "dark",
    "spring": "dark",
    "summer": "dark",
    "autumn": "dark",
    "winter": "dark",
    "dog_1": "dark",
    "dog_2": "dark",
    "cat": "dark",
}


def background_variant(background: str) -> str:
    """Return the contrast palette paired with a static page background."""
    return BACKGROUND_VARIANTS[background]
