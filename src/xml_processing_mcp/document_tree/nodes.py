"""DocumentNode dataclass — the normalised internal document representation."""

from dataclasses import dataclass, field
from typing import Literal

TAG_NAMES = Literal[
    "document",
    "body",
    "section",
    "heading",
    "paragraph",
    "list",
    "item",
    "table",
    "row",
    "cell",
    "link",
    "break",
    "unknown",
]

VALID_TAGS: frozenset[str] = frozenset(TAG_NAMES.__args__)  # type: ignore[attr-defined]


@dataclass
class DocumentNode:
    tag: str
    text: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    children: list["DocumentNode"] = field(default_factory=list)
