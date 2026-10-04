import hashlib
import re

from bs4 import BeautifulSoup

_NOISE_LINE_PATTERNS = (
    re.compile(r"(?:©|copyright)\s*\d{4}", re.IGNORECASE),
    re.compile(r"all rights reserved", re.IGNORECASE),
    re.compile(r"(?:accept|manage|reject) (?:all )?cookies?", re.IGNORECASE),
    re.compile(r"cookie (?:policy|preferences|settings)", re.IGNORECASE),
)
_NAV_WORDS = {
    "home",
    "about",
    "contact",
    "login",
    "log in",
    "sign up",
    "blog",
    "careers",
    "pricing",
    "products",
    "solutions",
    "resources",
    "menu",
}


def normalize_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
        tag.decompose()
    for element in soup.select(
        "[class*='cookie'], [id*='cookie'], [class*='consent'], [id*='consent'], "
        "[aria-label*='cookie' i]"
    ):
        element.decompose()
    return normalize_text(soup.get_text("\n"))


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\r", "\n")
    raw_lines = re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z0-9])", text)
    lines: list[str] = []
    for raw_line in raw_lines:
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or _is_noise_line(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _is_noise_line(line: str) -> bool:
    if any(pattern.search(line) for pattern in _NOISE_LINE_PATTERNS):
        return True
    words = [word.strip(" /|·•,-").lower() for word in re.split(r"\s*[|·•]\s*|\s{2,}", line)]
    return len(words) <= 8 and bool(words) and all(word in _NAV_WORDS for word in words)


def content_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
