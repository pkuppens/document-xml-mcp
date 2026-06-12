"""DocumentProcessingService — orchestrates Source → security → Parser → Renderer → Sink."""

import logging

from xml_processing_mcp.config import Settings
from xml_processing_mcp.document_tree.nodes import DocumentNode
from xml_processing_mcp.models import ParseDocumentResponse, ParseStats
from xml_processing_mcp.parsers.base import DocumentParser
from xml_processing_mcp.parsers.docx_parser import DocxParser
from xml_processing_mcp.renderers.simple_xml_renderer import SimpleXmlRenderer
from xml_processing_mcp.security.file_limits import check_extension, check_file_size
from xml_processing_mcp.sinks.base import XmlSink
from xml_processing_mcp.sinks.return_sink import ReturnSink
from xml_processing_mcp.sources.base import DocumentSource

_log = logging.getLogger(__name__)


def _count_tag(node: DocumentNode, tag: str) -> int:
    count = 1 if node.tag == tag else 0
    for child in node.children:
        count += _count_tag(child, tag)
    return count


class DocumentProcessingService:
    def __init__(self, config: Settings) -> None:
        self._config = config

    def process(
        self,
        source: DocumentSource,
        filename: str,
        parser: DocumentParser | None = None,
        sink: XmlSink | None = None,
    ) -> ParseDocumentResponse:
        _log.info("process start filename=%r source=%s", filename, type(source).__name__)

        _log.debug("process reading bytes from source")
        data = source.get_document_bytes()
        _log.debug("process bytes read size=%d", len(data))

        _log.debug("process checking file size limit=%d MB", self._config.max_file_size_mb)
        check_file_size(data, self._config.max_file_size_mb)

        _log.debug("process checking extension filename=%r", filename)
        check_extension(filename)

        effective_parser: DocumentParser = parser or DocxParser()
        _log.debug("process parsing with %s", type(effective_parser).__name__)
        tree = effective_parser.parse(data)
        _log.debug("process parse complete root_tag=%r children=%d", tree.tag, len(tree.children))

        _log.debug("process rendering tree to XML")
        xml = SimpleXmlRenderer().render(tree)
        _log.debug("process render complete xml_len=%d", len(xml))

        para_count = _count_tag(tree, "paragraph")
        table_count = _count_tag(tree, "table")
        stats = ParseStats(
            source_type="docx",
            paragraph_count=para_count,
            table_count=table_count,
            character_count=len(xml),
        )
        _log.debug("process stats paragraphs=%d tables=%d chars=%d", para_count, table_count, len(xml))

        effective_sink: XmlSink = sink or ReturnSink()
        _log.debug("process writing to sink %s document_id=%r", type(effective_sink).__name__, filename)
        effective_sink.write_xml(filename, xml)

        _log.info("process done filename=%r paragraphs=%d tables=%d xml_chars=%d",
                  filename, para_count, table_count, len(xml))
        return ParseDocumentResponse(xml=xml, warnings=[], stats=stats)
