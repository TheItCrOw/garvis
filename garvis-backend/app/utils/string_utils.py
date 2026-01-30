import re

# Matches: jarvis / jar vis / jar-vis / javis / ja vis / ja-vis
GARVIS_MISHEAR_REGEX = re.compile(
    r"""
    \b
    ja              # ja...
    r?              # optional 'r' => jarvis OR javis
    [\s\-]*         # optional space/hyphen => "jar vis", "ja-vis"
    v
    i
    s
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _capitalize_first(text: str) -> str:
    text = text.lstrip()
    return (text[:1].upper() + text[1:]) if text else text


def normalize_text(text: str) -> str:
    if not text:
        return text

    text = GARVIS_MISHEAR_REGEX.sub("Garvis", text)
    text = _capitalize_first(text)
    return text
