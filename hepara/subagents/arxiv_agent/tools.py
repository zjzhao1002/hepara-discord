import os
import httpx
import time
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from arxivflow import arXivFlow
from collections import Counter
from pathlib import Path
from utils.paper_helpers import add_to_chromadb, extract_markdown, get_md_raw_text, get_pdf_path

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ARXIVFLOW_KEYWORD_BACKEND = os.getenv("ARXIVFLOW_KEYWORD_BACKEND", "ollama").lower()

BASE_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom"
}

ARXIV_HEADERS = {
    "User-Agent": "HEPARA/0.1.0 (https://github.com/zjzhao1002/hepara; research tool)"
}

_last_request_time = 0.0
_arxiv_semaphore = asyncio.Semaphore(1)
MIN_REQUEST_INTERVAL = 3.0
_arxiv_client: Optional[httpx.AsyncClient] = None

def _get_arxiv_client() -> httpx.AsyncClient:
    """
    Returns a shared httpx.AsyncClient instance.
    """
    global _arxiv_client
    if _arxiv_client is None:
        _arxiv_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    return _arxiv_client

async def search_papers(query: str, 
                        max_results: Optional[int] = None, 
                        sort_by: str = 'submittedDate', 
                        order_by: str = 'descending'
                        ) -> List[Dict[str, Any]]:
    """
    Searches for papers on arXiv using the Atom API.
    """
    params = {
        "search_query": query,
        "sortBy": sort_by,
        "sortOrder": order_by
    }
    if max_results:
        params["max_results"] = max_results # type: ignore

    client = _get_arxiv_client()

    response = await _rate_limit_request(client=client, url=BASE_URL, params=params)
    return _parse_arxiv_atom_response(response.text)

async def _rate_limit_request(client: httpx.AsyncClient, url: str, params: Optional[Dict] = None) -> httpx.Response:
    global _last_request_time

    async with _arxiv_semaphore: # Strict: Only one connection at a time.
        for attempt in range(3): # Retry on timeout or 503
            # Enforce minimum interval before EVERY attempt (including retries)
            elapsed = time.monotonic() - _last_request_time
            if elapsed < MIN_REQUEST_INTERVAL:
                await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
            
            _last_request_time = time.monotonic()

            try:
                response = await client.get(url, params=params, headers=ARXIV_HEADERS)
                if response.status_code == 429:
                    print(f"arXiv is rate limiting (429). Waiting 60 seconds...")
                    await asyncio.sleep(60.0)
                    _last_request_time = time.monotonic() # Reset timer after long wait
                    continue
                if response.status_code == 503:
                    print("arXiv service unavailable (503). Waiting 5 seconds...")
                    await asyncio.sleep(5.0)
                    _last_request_time = time.monotonic()
                    continue
                
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt < 2:
                    print(f"arXiv request failed: {type(e).__name__}: {e}. Retrying in 5s...")
                    await asyncio.sleep(5.0)
                    _last_request_time = time.monotonic()
                else:
                    raise

    raise RuntimeError("arXiv request failed after retries.")

def _parse_arxiv_atom_response(text: str) -> List[Dict[str, Any]]:
    results = []

    try: 
        root = ET.fromstring(text)
        for entry in root.findall('atom:entry', ARXIV_NS):
            id_elem = entry.find('atom:id', ARXIV_NS)
            if id_elem is None or id_elem.text is None:
                continue
            
            arxiv_url = id_elem.text
            paper_id = arxiv_url.split('/abs/')[-1]
            short_id = paper_id.split('v')[0]

            title_elem = entry.find('atom:title', ARXIV_NS)
            title = (
                title_elem.text.strip().replace('\n', ' ') 
                if title_elem is not None and title_elem.text 
                else ""
                )
            
            authors = []
            for author in entry.findall('atom:author', ARXIV_NS):
                name_elem = author.find('atom:name', ARXIV_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text)

            summary_elem = entry.find('atom:summary', ARXIV_NS)
            abstract = (
                summary_elem.text.strip().replace('\n', ' ')
                if summary_elem is not None and summary_elem.text
                else ""
            )

            categories = []
            for cat in entry.findall('arxiv:primary_category', ARXIV_NS):
                term = cat.get('term')
                if term:
                    categories.append(term)
            for cat in entry.findall('atom:category', ARXIV_NS):
                term = cat.get('term')
                if term and term not in categories:
                    categories.append(term)

            published = entry.findtext('atom:published', default="", namespaces=ARXIV_NS)[:10]
            updated = entry.findtext('atom:updated', default="", namespaces=ARXIV_NS)[:10]

            pdf_url = None
            for link in entry.findall('atom:link', ARXIV_NS):
                if link.get('title') == 'pdf':
                    pdf_url = link.get('href')
                    break
            if not pdf_url:
                pdf_url = f"https://arxiv.org/pdf/{paper_id}"

            results.append(
                {
                    "arXiv ID": short_id,
                    "Title": title,
                    "Authors": ", ".join(authors),
                    "Abstract": abstract,
                    "Categories": ", ".join(categories),
                    "Published Date": published,
                    "Updated Date": updated,
                    "arXiv URL": arxiv_url,
                    "PDF URL": pdf_url
                }
            )
    except ET.ParseError as e:
        raise ValueError(f"Failed parsing arXiv API response: {e}")
    
    return results

async def download_pdf(
        arxiv_id: str,
        filename: str = ""
    ) -> str:
    """
    Downloads the PDF for a given arXiv ID asynchronously, respecting arXiv's rate limits.
    """
    if not arxiv_id:
        raise ValueError("No arXiv ID provided")

    # Search for the paper to get the PDF URL
    results = await search_papers(query=f"id:{arxiv_id}", max_results=1)
    if not results:
        raise ValueError(f"Could not find paper with arXiv ID: {arxiv_id}")

    pdf_url = results[0].get("PDF URL")
    if not pdf_url:
        raise ValueError(f"No PDF URL found for arXiv ID: {arxiv_id}")
    
    metadata = {
        "arXiv ID": arxiv_id
    }

    authors = results[0].get("Authors")
    if authors:
        metadata["Authors"] = authors
    
    dirpath = get_pdf_path()

    dirpath.mkdir(parents=True, exist_ok=True)

    if not filename:
        filename = f"{arxiv_id}.pdf"
        if not filename.endswith(".pdf"):
            filename += ".pdf"

    path = dirpath / filename

    client = _get_arxiv_client()

    response = await _rate_limit_request(client=client, url=pdf_url)
    with open(path, 'wb') as f:
        f.write(response.content)

    try:
        markdown_path = extract_markdown(Path(path))
    except Exception as e:
        print(f"Downloaded PDF to {path}, but failed to convert it to Markdown: {e}")
    else:
        raw_text = get_md_raw_text(markdown_path)
        try:
            add_to_chromadb(raw_text, metadata, str(dirpath))
        except Exception as e:
            print(f"Downloaded PDF to {path} and converted it to Markdown at {markdown_path}, but failed to add it to Chroma DB: {e}")

    return str(path)

def _calculate_relevance(row_keywords: str | list[str], search_keywords: list[str]) -> int:
    """
    Calculates the relevance score for a paper based on its keywords and the search keywords.
    Match papers (up to 5) based on keywords.
    """
    if not row_keywords:
        return 0
    if isinstance(row_keywords, str):
        row_k_list = [k.strip().lower() for k in row_keywords.split(',') if k.strip()]
    elif isinstance(row_keywords, list):
        row_k_list = [str(k).strip().lower() for k in row_keywords if str(k).strip()]
    else:
        return 0
        
    search_k_lower = [k.lower() for k in search_keywords]
    matches = set(search_k_lower) & set(row_k_list)
    return len(matches)

async def recommend_by_trends(max_results: int=100) -> dict:
    """
    Recommends latest papers based on trending topics in the last week.
    It finds the most frequent keywords in the latest papers and recommends papers matching those keywords.
    """
    CATEGORIES = os.getenv("CATEGORIES")
    if not CATEGORIES:
        return {"error": "Error: Required environment variable CATEGORIES is not set."}

    backend = ARXIVFLOW_KEYWORD_BACKEND or "ollama"
    if backend not in {"ollama", "gemini"}:
        return {"error": "Error: ARXIVFLOW_KEYWORD_BACKEND must be either 'ollama' or 'gemini'."}

    categories = [cat.strip() for cat in CATEGORIES.split(',') if cat.strip()]
    if not categories:
        return {"error": "Error: Required environment variable CATEGORIES does not contain any valid arXiv categories."}

    flow_kwargs: dict[str, Any] = {
        "categories": categories,
        "max_results": max_results,
    }

    if backend == "ollama":
        if not OLLAMA_MODEL:
            return {"error": "Error: Required environment variable OLLAMA_MODEL is not set for Ollama keyword extraction."}
        flow_kwargs["ollama_model"] = OLLAMA_MODEL
    else:
        if not GOOGLE_MODEL or not GOOGLE_API_KEY:
            return {"error": "Error: Required environment variables GOOGLE_MODEL and GOOGLE_API_KEY are not set for Gemini keyword extraction."}
        flow_kwargs["gemini_model"] = GOOGLE_MODEL
        flow_kwargs["gemini_api_key"] = GOOGLE_API_KEY

    # Initialize arXivFlow and fetch data
    flow = arXivFlow(**flow_kwargs)
    # flow.set_client_parameters(delay_seconds=3.0, num_retries=3)
    try:
        df = await flow.get_arxiv_data(download_pdfs=False)
    finally:
        close = getattr(flow, "close", None)
        if close is not None:
            await close()

    if df is None or df.empty:
        return {"error": "Error:No papers found for the specified categories."}
    
    # Drop duplicates based on arXiv ID to ensure unique recommendations
    id_col = "arXiv ID"  # Default column name for arXiv ID
    if id_col:
        df = df.drop_duplicates(subset=[id_col])

    if 'Keywords' not in df.columns:
        return {"error": "Error: The papers database does not contain a 'Keywords' column."}
    
    all_keywords = []
    for k_val in df['Keywords'].dropna():
        if isinstance(k_val, str):
            all_keywords.extend([k.strip() for k in k_val.split(',') if k.strip()])
        elif isinstance(k_val, list):
            all_keywords.extend([str(k).strip() for k in k_val if str(k).strip()])  

    if all_keywords:
        counts = Counter(all_keywords)
        top_trending = counts.most_common(3)
        search_keywords = [k for k, _ in top_trending] # Get top 3 trending keywords
        keyword_counts = {k: c for k, c in top_trending}
    else:
        return {"error": "Error: No keywords found in the database to determine trends."}
    
    df['relevance_score'] = df['Keywords'].apply(lambda x: _calculate_relevance(x, search_keywords))
    
    # Filter for relevant papers and then pick top 5
    relevant_df = df[df['relevance_score'] > 0]
    
    if relevant_df.empty:
        return {"error": f"Error: No papers matched the keywords: {', '.join(search_keywords)}"}
    
    top_papers = relevant_df.sort_values(by='relevance_score', ascending=False).head(5)

    report = {"keywords": keyword_counts, "papers": []}

    for _, row in top_papers.iterrows():
        title = row.get('Title', row.get('title', 'No Title'))
        arxiv_id = row.get('arXiv ID', row.get('arxiv_id', row.get('id', 'N/A')))
        
        report['papers'].append({
            "title": title,
            "arxiv_id": arxiv_id,
        })
    return report

def list_papers()->dict:
    """
    List all stored papers IDs
    """
    paper_path = get_pdf_path()
    
    if not paper_path.exists():
        papers = []
    else:
        papers = sorted([
            p.stem 
            for p in paper_path.iterdir()
            if p.is_file() and p.suffix == ".pdf"
        ])
    return {
        "paper_path": str(paper_path),
        "total_papers": len(papers),
        "papers": papers
    }

async def read_paper(arxiv_id: str)->str:
    paper_dict = list_papers()
    papers_path = get_pdf_path()
    if not papers_path.exists():
        papers_path = Path(paper_dict['paper_path'])

    if not papers_path:
        return "Error: Cannot find the path to store papers."

    paper_ids = paper_dict['papers']

    if arxiv_id not in paper_ids:
        # If paper does not exist, try to download it.
        pdf_path = await download_pdf(arxiv_id=arxiv_id, filename=f"{arxiv_id}.pdf")
        markdown_path = Path(pdf_path).with_suffix(".md")
        if not markdown_path.exists():
            try:
                markdown_path = extract_markdown(Path(pdf_path))
            except Exception as e:
                return f"Error: Downloaded PDF to {pdf_path}, but failed to convert it to Markdown: {e}"
    else:
        pdf_path = papers_path/f"{arxiv_id}.pdf"
        markdown_path = papers_path/f"{arxiv_id}.md"
        if not markdown_path.exists():
            try:
                markdown_path = extract_markdown(pdf_path)
            except Exception as e:
                return f"Error: Found stored PDF at {pdf_path}, but failed to convert it to Markdown: {e}"

    if not markdown_path.exists():
        return f"Error: Markdown content was not generated for arXiv ID {arxiv_id}."

    content = markdown_path.read_text(
        encoding="utf-8"
    )
    return content
