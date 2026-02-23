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
        self.collection_name = collection_name
        self.collection: Collection = self.client.get_or_create_collection(collection_name)
        self._selected_docs: set[str] = set()

    def list_available_docs(self) -> list[str]:
        if not settings.docs_dir.exists():
            return []

        files = []
        for pattern in ("*.pdf", "*.docx", "*.txt"):
            files.extend(settings.docs_dir.glob(pattern))
        return sorted({path.name for path in files})

    def get_selected_docs(self) -> list[str]:
        if self._selected_docs:
            return sorted(self._selected_docs)

        return self.list_available_docs()

    def set_selected_docs(self, docs: list[str]) -> list[str]:
        available = set(self.list_available_docs())
        chosen = {doc for doc in docs if doc in available}
        self._selected_docs = chosen
        return self.get_selected_docs()

    def build_index(self) -> int:
        documents = load_documents(settings.docs_dir)
        if not documents:
            return 0

        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(self.collection_name)

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
            source = str(chunk.metadata.get("source", ""))
            doc_name = Path(source).name if source else "unknown"
            metadata = dict(chunk.metadata)
            metadata["doc_name"] = doc_name
            metadatas.append(metadata)

        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        return len(chunks)

    def retrieve(self, query: str, top_k: int | None = None) -> List[str]:
        if self.collection.count() == 0:
            return []

        limit = top_k or settings.top_k
        selected_docs = set(self.get_selected_docs())
        result = self.collection.query(
            query_texts=[query],
            n_results=max(limit * 5, limit),
            include=["documents", "metadatas"],
        )

        doc_rows = result.get("documents", [])
        meta_rows = result.get("metadatas", [])
        if not doc_rows:
            return []

        docs = doc_rows[0] if doc_rows else []
        metas = meta_rows[0] if meta_rows else []
        filtered: list[str] = []

        for idx, doc_text in enumerate(docs):
            metadata = metas[idx] if idx < len(metas) else {}
            doc_name = str((metadata or {}).get("doc_name", ""))
            if selected_docs and doc_name not in selected_docs:
                continue
            filtered.append(doc_text)
            if len(filtered) >= limit:
                break

        return filtered


rag_service = RAGService(settings.chroma_path, settings.collection_name)
