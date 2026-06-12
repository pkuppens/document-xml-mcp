"""SimpleXmlRenderer — tree processor + XML serialiser.

Processing rules applied in a single recursive pass before serialisation:
1. Remove empty nodes — drop nodes with no text (or whitespace-only) and no children.
2. Strip useless attributes — remove attrs whose value is empty, "none", "false", or "0"
   (case-insensitive), EXCEPT the "level" attribute on heading nodes.
3. Promote single-child nodes — if a node has exactly one child, no text, and no
   remaining attributes after stripping, replace it with its child in the parent list.
"""

from lxml import etree

from xml_processing_mcp.document_tree.nodes import DocumentNode

_USELESS_VALUES = frozenset(("", "none", "false", "0"))

# Tags that carry semantic meaning and must never be unwrapped by Rule 3
_NON_PROMOTABLE = frozenset(("document", "body", "table", "list", "row", "cell", "heading", "paragraph", "item", "link"))


def _strip_attrs(node: DocumentNode) -> dict[str, str]:
    result = {}
    for k, v in node.attributes.items():
        if node.tag == "heading" and k == "level":
            result[k] = v
            continue
        if v.lower() not in _USELESS_VALUES:
            result[k] = v
    return result


def _process(node: DocumentNode) -> DocumentNode | None:
    """Recursively clean node; return None to signal removal."""
    # Process children first
    cleaned_children: list[DocumentNode] = []
    for child in node.children:
        result = _process(child)
        if result is not None:
            cleaned_children.append(result)

    stripped_attrs = _strip_attrs(node)
    has_text = bool(node.text and node.text.strip())

    # Rule 1: drop empty leaf nodes
    if not has_text and not cleaned_children:
        return None

    # Rule 3: promote single-child wrapper (no text, no attrs after strip)
    # Only applies to non-semantic wrapper nodes (e.g. section, unknown)
    if node.tag not in _NON_PROMOTABLE and not has_text and not stripped_attrs and len(cleaned_children) == 1:
        return cleaned_children[0]

    return DocumentNode(tag=node.tag, text=node.text if has_text else None, attributes=stripped_attrs, children=cleaned_children)


def _to_element(node: DocumentNode) -> etree._Element:
    elem = etree.Element(node.tag, attrib=node.attributes)
    if node.text:
        elem.text = node.text
    for child in node.children:
        elem.append(_to_element(child))
    return elem


class SimpleXmlRenderer:
    """Process and serialise a DocumentNode tree to clean XML."""

    def render(self, document: DocumentNode) -> str:
        processed = _process(document)
        if processed is None:
            return "<document/>"
        root = _to_element(processed)
        return etree.tostring(root, pretty_print=True, encoding="unicode")
