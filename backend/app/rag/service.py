from pathlib import Path
from typing import List

import chromadb
from chromadb.api.models.Collection import Collection
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.rag.loader import load_documents


class RAGService:
    def __init__(self, chroma_path: Path, collection_name: str) -> None:
        self.client = chromadb.PersistentClient(path=str(chroma_path))
        self.collection: Collection = self.client.get_or_create_collection(collection_name)

    def build_index(self) -> int:
        documents = load_documents(settings.docs_dir)
        if not documents:
            return 0

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunks = splitter.split_documents(documents)

        ids = []
        texts = []
        metadatas = []

        for idx, chunk in enumerate(chunks):
            ids.append(f"chunk_{idx}")
            texts.append(chunk.page_content)
            metadatas.append(chunk.metadata)

        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        return len(chunks)

    def retrieve(self, query: str, top_k: int | None = None) -> List[str]:
        if self.collection.count() == 0:
            return []

        limit = top_k or settings.top_k
        result = self.collection.query(query_texts=[query], n_results=limit)
        docs = result.get("documents", [])
        if not docs:
            return []
        return docs[0]


rag_service = RAGService(settings.chroma_path, settings.collection_name)
