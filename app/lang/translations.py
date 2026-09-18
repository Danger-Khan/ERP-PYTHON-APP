from . import en, ur, ps, zh, ru

LANGUAGE_OPTIONS = [
    ("en", "English 🇬🇧"),
    ("ur", "Urdu 🇵🇰"),
    ("ps", "Pashto 🇦🇫"),
    ("zh", "中文 🇨🇳"),
    ("ru", "Русский 🇷🇺"),
]

ORDER_CARD_TRANSLATIONS = {
    "en": en.ORDER_CARD,
    "ur": ur.ORDER_CARD,
    "ps": ps.ORDER_CARD,
    "zh": zh.ORDER_CARD,
    "ru": ru.ORDER_CARD,
}

TRANSLATIONS = {
    "en": en.TRANSLATIONS,
    "ur": ur.TRANSLATIONS,
    "ps": ps.TRANSLATIONS,
    "zh": zh.TRANSLATIONS,
    "ru": ru.TRANSLATIONS,
}

__all__ = ["LANGUAGE_OPTIONS", "ORDER_CARD_TRANSLATIONS", "TRANSLATIONS"]