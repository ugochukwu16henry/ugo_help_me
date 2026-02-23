from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class TranscriptSegmentRequest(BaseModel):
    text: str


class BuildIndexResponse(BaseModel):
    indexed_chunks: int
