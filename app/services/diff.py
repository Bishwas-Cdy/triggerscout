from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class ChangeCandidate:
    before_excerpt: str
    after_excerpt: str


def compact_diff(before: str, after: str, *, excerpt_limit: int = 1_500) -> ChangeCandidate | None:
    if before == after:
        return None
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    matcher = SequenceMatcher(a=before_lines, b=after_lines, autojunk=False)
    removed: list[str] = []
    added: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"delete", "replace"}:
            removed.extend(before_lines[i1:i2])
        if tag in {"insert", "replace"}:
            added.extend(after_lines[j1:j2])
    before_excerpt = " ".join(removed)[:excerpt_limit].strip()
    after_excerpt = " ".join(added)[:excerpt_limit].strip()
    if not before_excerpt and not after_excerpt:
        return None
    return ChangeCandidate(before_excerpt=before_excerpt, after_excerpt=after_excerpt)
