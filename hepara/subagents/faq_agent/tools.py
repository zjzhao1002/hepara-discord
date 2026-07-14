import os
import chromadb
from pathlib import Path
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional

PDF_PATH = os.getenv("PDF_PATH")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def _create_query_output(metadatas: List[Dict], docs: List[str]) -> str:
    context_chunks = []
    for doc, meta in zip(docs, metadatas):
        header_context = f"arXiv ID: {meta.get("arXiv ID")}, Authors: {meta.get("Authors")}, Title: {meta.get("Header_1")}"
        context_chunks.append(f"[{header_context}]\n{doc}\n")
    return "\n\n".join(context_chunks)

def query_chromadb(query: str, paper_path: Optional[str]=PDF_PATH):
    if paper_path:
        db_path = Path(paper_path)/"chroma_db"
    else:
        db_path = Path.cwd()/"chroma_db"

    if not db_path.exists():
        return "No local arXiv database found. Use google search instead."
    
    client = chromadb.PersistentClient(path=db_path)

    gemini_embedding = embedding_functions.GoogleGeminiEmbeddingFunction(
        model_name = "gemini-embedding-001", 
        api_key_env_var="GOOGLE_API_KEY",
        task_type="RETRIEVAL_QUERY"
    )

    try:
        collection = client.get_collection(
            name = "arxiv_papers",
            embedding_function=gemini_embedding # type: ignore
        )

        results = collection.query(
            query_texts=[query],
            n_results=3, 
            include=['documents', "metadatas"]
        )

        retrieve_docs = results.get("documents", [[]])[0] # type: ignore
        retrieve_metadatas = results.get("metadatas", [[]])[0] # type: ignore
        if not retrieve_docs:
            return "No relevant context found in the local arXiv database."
        
        return _create_query_output(retrieve_metadatas, retrieve_docs) # type: ignore

    except Exception as e:
        return f"Fail to query arXiv database: {e}"
