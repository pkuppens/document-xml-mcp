"""DOCX → DocumentNode tree parser."""

from lxml import etree

from xml_processing_mcp.document_tree.nodes import DocumentNode
from xml_processing_mcp.security.zip_safety import safe_open_docx

# WordprocessingML namespace
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _w(local: str) -> str:
    return f"{{{_W}}}{local}"


def _collect_text(elem: etree._Element) -> str:
    """Join all w:t text runs inside an element."""
    parts = []
    for t in elem.iter(_w("t")):
        parts.append(t.text or "")
    return "".join(parts)


def _style_name(para: etree._Element) -> str:
    """Return the paragraph style name, or empty string."""
    ppr = para.find(_w("pPr"))
    if ppr is None:
        return ""
    ps = ppr.find(_w("pStyle"))
    if ps is None:
        return ""
    return ps.get(_w("val"), "")


def _is_list_item(para: etree._Element) -> bool:
    ppr = para.find(_w("pPr"))
    if ppr is None:
        return False
    return ppr.find(_w("numPr")) is not None


def _parse_table(tbl: etree._Element) -> DocumentNode:
    table_node = DocumentNode(tag="table")
    for tr in tbl.findall(_w("tr")):
        row_node = DocumentNode(tag="row")
        for tc in tr.findall(_w("tc")):
            cell_text = _collect_text(tc)
            row_node.children.append(DocumentNode(tag="cell", text=cell_text or None))
        table_node.children.append(row_node)
    return table_node


def _parse_body(body: etree._Element) -> DocumentNode:
    body_node = DocumentNode(tag="body")
    pending_list: DocumentNode | None = None

    for child in body:
        tag = etree.QName(child).localname

        if tag == "p":
            style = _style_name(child)
            text = _collect_text(child)

            # Detect hyperlink — look for w:hyperlink inside the paragraph
            hyperlink = child.find(_w("hyperlink"))
            if hyperlink is not None:
                href = hyperlink.get(_w("id"), hyperlink.get(f"{{{_R}}}id", ""))
                link_text = _collect_text(hyperlink) or text
                node = DocumentNode(tag="link", text=link_text or None, attributes={"href": href} if href else {})
                pending_list = None
                body_node.children.append(node)
                continue

            if style.startswith("Heading") or style.startswith("heading"):
                level = "".join(c for c in style if c.isdigit()) or "1"
                node = DocumentNode(tag="heading", text=text or None, attributes={"level": level, "class": style})
                pending_list = None
                body_node.children.append(node)
            elif _is_list_item(child):
                if pending_list is None:
                    pending_list = DocumentNode(tag="list")
                    body_node.children.append(pending_list)
                pending_list.children.append(DocumentNode(tag="item", text=text or None))
            else:
                pending_list = None
                if text:
                    body_node.children.append(DocumentNode(tag="paragraph", text=text))

        elif tag == "tbl":
            pending_list = None
            body_node.children.append(_parse_table(child))

        else:
            pending_list = None

    return body_node


class DocxParser:
    """Parse DOCX bytes into a normalised DocumentNode tree."""

    def parse(self, document_bytes: bytes) -> DocumentNode:
        zf = safe_open_docx(document_bytes)
        try:
            xml_bytes = zf.read("word/document.xml")
        finally:
            zf.close()

        root = etree.fromstring(xml_bytes)  # noqa: S320 — defusedxml not needed; lxml is safe by default
        body = root.find(_w("body"))
        if body is None:
            return DocumentNode(tag="document", children=[DocumentNode(tag="body")])

        doc_node = DocumentNode(tag="document")
        doc_node.children.append(_parse_body(body))
        return doc_node
