"""Pydantic request and response models."""

from pydantic import BaseModel


class ParseDocumentRequest(BaseModel):
    filename: str
    content_base64: str
    document_type: str = "docx"
    profile: str = "generic"


class ParseFileRequest(BaseModel):
    path: str
    document_type: str = "docx"
    profile: str = "generic"


class ParseBatchRequest(BaseModel):
    input_dir: str
    output_dir: str
    document_type: str = "docx"
    continue_on_error: bool = True


class ParseStats(BaseModel):
    source_type: str
    paragraph_count: int
    table_count: int
    character_count: int


class ParseDocumentResponse(BaseModel):
    xml: str
    warnings: list[str]
    stats: ParseStats


class ParseBatchResult(BaseModel):
    filename: str
    output_path: str | None
    warnings: list[str]
    error: str | None = None


class ParseBatchResponse(BaseModel):
    processed: int
    failed: int
    results: list[ParseBatchResult]


class SupportedTypesResponse(BaseModel):
    supported: list[str]
    planned: list[str]
