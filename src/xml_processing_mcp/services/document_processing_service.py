"""DocumentProcessingService — orchestrates Source → security → Parser → Renderer → Sink."""

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
        data = source.get_document_bytes()
        check_file_size(data, self._config.max_file_size_mb)
        check_extension(filename)

        effective_parser: DocumentParser = parser or DocxParser()
        tree = effective_parser.parse(data)

        xml = SimpleXmlRenderer().render(tree)

        para_count = _count_tag(tree, "paragraph")
        table_count = _count_tag(tree, "table")
        stats = ParseStats(
            source_type="docx",
            paragraph_count=para_count,
            table_count=table_count,
            character_count=len(xml),
        )

        effective_sink: XmlSink = sink or ReturnSink()
        effective_sink.write_xml(filename, xml)

        return ParseDocumentResponse(xml=xml, warnings=[], stats=stats)
