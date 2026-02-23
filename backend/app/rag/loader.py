from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader, Docx2txtLoader


def load_documents(docs_dir: Path):
    documents = []

    if not docs_dir.exists():
        return documents

    for pattern, loader in (
        ("**/*.pdf", PyPDFLoader),
        ("**/*.txt", TextLoader),
        ("**/*.docx", Docx2txtLoader),
    ):
        loaded = DirectoryLoader(str(docs_dir), glob=pattern, loader_cls=loader).load()
        documents.extend(loaded)

    return documents
