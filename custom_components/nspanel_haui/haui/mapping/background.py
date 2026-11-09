# backgrounds
# name -> picture_id
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


BACKGROUND_COLOR_SCHEMES = {
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

# Solid picture fills already embedded in the HMI (1=dark, 2=light).
BACKGROUND_COLOR_PICTURES = {"dark": BACKGROUNDS["dark"], "light": BACKGROUNDS["light"]}


def scheme_background_picture_id(variant: str) -> int:
    """Return the HMI's solid-fill picture for a dark/light scheme background."""
    return BACKGROUND_COLOR_PICTURES[variant]


def background_color_scheme(background: str) -> str:
    """Return the contrast palette paired with a static page background."""
    return BACKGROUND_COLOR_SCHEMES[background]
