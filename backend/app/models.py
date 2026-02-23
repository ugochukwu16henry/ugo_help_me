from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class TranscriptSegmentRequest(BaseModel):
    text: str


class BuildIndexResponse(BaseModel):
    indexed_chunks: int


class ScreenFocusRequest(BaseModel):
    mode: str
    monitor_index: int = 1
    ratio: float | None = None
    left: int | None = None
    top: int | None = None
    width: int | None = None
    height: int | None = None


class DocumentSelectionRequest(BaseModel):
    selected_docs: list[str]
