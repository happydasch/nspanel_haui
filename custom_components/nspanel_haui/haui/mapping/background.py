# backgrounds: name -> picture_id. Picture 0 is the layout grid, not a background.
BACKGROUNDS = {
    "dark": 1,
    "light": 2,
    "modern": 3,
    "spring": 4,
    "summer": 5,
    "autumn": 6,
    "winter": 7,
    "dog_1": 8,
    "dog_2": 9,
    "cat": 10,
}


BACKGROUND_VARIANTS = {
    "dark": "dark",
    "light": "light",
    "modern": "dark",
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
