import os
import re
import pymupdf4llm 
from typing import List, Dict, Optional
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import MarkdownHeaderTextSplitter
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

PDF_PATH = os.getenv("PDF_PATH")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ARXIV_ID_PATTERN = re.compile(
    r"(?i)(?:arxiv\s*:\s*|arxiv\.org/(?:abs|pdf)/)?"
    r"([a-z-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?"
)

def get_pdf_path():
    configured_path = os.getenv("PDF_PATH")
    if configured_path:
        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path
    return PROJECT_ROOT / "pdf"

def _get_pdf_names() -> List[str]:
    pdf_path = get_pdf_path()
    if not pdf_path.exists():
        return []
    else:
        pdfs = sorted([
            p.stem 
            for p in pdf_path.iterdir()
            if p.is_file() and p.suffix == ".pdf"
        ])
        return pdfs

def _get_pdf_files() -> List[Path]:
    pdf_path = get_pdf_path()
    if not pdf_path.exists():
        return []
    return sorted(
        [
            p
            for p in pdf_path.iterdir()
            if p.is_file() and p.suffix == ".pdf"
        ],
        key=lambda p: p.name,
    )

def extract_markdown(pdf_path: Path) -> Path:
    markdown = pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)
    markdown_path = pdf_path.with_suffix(".md")
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown) # type: ignore
    return markdown_path

def get_md_raw_text(markdown_path: Path) -> str:
    if markdown_path.suffix != ".md":
        return ""
    else:
        content = markdown_path.read_text(encoding="utf-8")
        return content

def _extract_arxiv_id(text: str) -> Optional[str]:
    match = ARXIV_ID_PATTERN.search(text)
    if not match:
        return None
    return match.group(1)

def _build_paper_metadata(pdf_path: Path, markdown: str) -> Dict[str, str]:
    arxiv_id = _extract_arxiv_id(pdf_path.stem) or _extract_arxiv_id(markdown)
    document_id = arxiv_id or pdf_path.stem
    metadata = {
        "Document ID": document_id,
        "Source File": pdf_path.name,
    }
    if arxiv_id:
        metadata["arXiv ID"] = arxiv_id
    return metadata
    
def _markdown_text_splitter(raw_text: str) -> List:
    headers_to_split_on = [
        ("#", "Header_1"),
        ("##", "Header_2"),
        ("###", "Header_3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )

    chunks = markdown_splitter.split_text(raw_text)
    return chunks

def _get_chroma_db_path(path: Optional[str]) -> str:
    if path:
        return str(Path(path) / "chroma_db")
    return str(PROJECT_ROOT / "chroma_db")

def _get_chroma_collection(path: Optional[str]):
    client = chromadb.PersistentClient(path=_get_chroma_db_path(path))
    gemini_embedding = embedding_functions.GoogleGeminiEmbeddingFunction(
        model_name = "gemini-embedding-001",
        api_key_env_var="GOOGLE_API_KEY"
    )

    return client.get_or_create_collection(
        name = "arxiv_papers",
        embedding_function=gemini_embedding # type: ignore
    )


def _get_indexed_document_ids(path: Optional[str]) -> set[str]:
    collection = _get_chroma_collection(path)
    if collection.count() == 0:
        return set()

    records = collection.get(include=["metadatas"])
    indexed_ids = set()
    for metadata in records.get("metadatas", []): # type: ignore
        if not metadata:
            continue
        document_id = metadata.get("Document ID") or metadata.get("arXiv ID")
        if document_id:
            indexed_ids.add(document_id)
    return indexed_ids


def add_to_chromadb(markdown: str, metadata: Dict, path: Optional[str]) -> str:
    collection = _get_chroma_collection(path)

    documents = []
    metadatas = []
    ids = []

    if not markdown:
        return "Error: No markdown or markdown content is empty."
    
    chunks = _markdown_text_splitter(markdown)
    for idx, chunk in enumerate(chunks):
        documents.append(chunk.page_content)

        chunk_metadata = metadata | (chunk.metadata or {})
        metadatas.append(chunk_metadata)

        document_id = chunk_metadata.get("Document ID") or chunk_metadata.get("arXiv ID")
        if document_id:
            ids.append(f"{document_id}_chunk_{idx}")
        else:
            raise ValueError("No valid document ID")
        
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    document_id = metadata.get("Document ID") or metadata.get("arXiv ID")
    return f"Success: Write data of {document_id} to chroma database."

def create_new_markdown(pdf: str | Path) -> Path:
    pdf_path = Path(pdf)
    if not pdf_path.is_absolute():
        pdf_path = get_pdf_path() / f"{pdf_path.stem}.pdf"
    md_path = extract_markdown(pdf_path)
    return md_path

def update_database():
    pdf_path = get_pdf_path()
    if not pdf_path.exists():
        print("No valid PDF path.")
        return
    pdf_files = _get_pdf_files()
    for pdf_file in pdf_files:
        if not pdf_file.with_suffix(".md").exists():
            create_new_markdown(pdf_file)

    indexed_document_ids = _get_indexed_document_ids(str(pdf_path))
    for pdf_file in pdf_files:
        md = pdf_file.with_suffix(".md")
        if not md.exists():
            continue

        content = get_md_raw_text(md)
        metadata = _build_paper_metadata(pdf_file, content)
        if metadata["Document ID"] in indexed_document_ids:
            continue

        add_to_chromadb(content, metadata, str(pdf_path))
        indexed_document_ids.add(metadata["Document ID"])
        print(f"Paper {metadata['Document ID']} is added to database.")
    print("No more papers to be added.")
    
def print_papers():
    pdf_path = get_pdf_path()
    pdfs = _get_pdf_names()
    if not pdfs:
        print(f"No available papers in this directory: {str(pdf_path)}")
        return
    
    print("Available papers: ")
    print("\n".join(pdfs))
