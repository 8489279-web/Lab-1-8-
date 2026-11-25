import re
from pathlib import Path

from findex.index import Index
from findex.query import parse
from findex.ranking import positive_terms


def make_snippet(index: Index, doc_id: int, query: str, radius: int = 80) -> str:
    path = Path(index.doc_meta[doc_id].path)
    text = path.read_text(encoding="utf-8-sig")

    terms = positive_terms(parse(query))

    if not terms:
        return text[: radius * 2]

    pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(term) for term in terms) + r")\b", re.IGNORECASE
    )

    matches = list(pattern.finditer(text))

    if not matches:
        return text[: radius * 2]

    best = max(
        matches,
        key=lambda m: sum(
            abs(other.start() - m.start()) <= radius for other in matches
        ),
    )

    start = max(0, best.start() - radius)
    end = min(len(text), best.end() + radius)

    snippet = text[start:end]

    snippet = pattern.sub(lambda m: "[" + m.group() + "]", snippet)

    if start > 0:
        snippet = "..." + snippet

    if end < len(text):
        snippet += "..."

    return snippet
