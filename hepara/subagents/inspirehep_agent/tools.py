import os
import httpx
import json
from typing import Literal

DEFAULT_PAGE_SIZE = 150
MAX_INSPIRE_PAGE_SIZE = 250
AUTHOR = os.getenv("AUTHOR")
RECORD_FILE = os.path.join(os.path.dirname(__file__), "citations_record.json")
LITERATURE_API_URL = "https://inspirehep.net/api/literature"
CITATION_DIRECTIONS = {
    "citing": {
        "query_prefix": "citedby",
        "relationship": "references",
        "description": "papers this paper cites",
    },
    "cited_by": {
        "query_prefix": "refersto",
        "relationship": "citations",
        "description": "papers that cite this paper",
    },
}

async def _fetch_literature(params: dict) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Using the base URL directly as the tool sometimes has issues with nested URLs
        response = await client.get(LITERATURE_API_URL, params=params)
        response.raise_for_status()
        return response.json()

def _paper_summary(hit: dict) -> dict:
    metadata = hit.get('metadata', {})
    return {
        'Inspire ID': hit.get('id'),
        'Title': metadata.get('titles', [{}])[0].get('title', 'N/A'),
        'arXiv ID': metadata.get('arxiv_eprints', [{}])[0].get('value', 'N/A'),
    }

def _paper_summary_with_citations(hit: dict) -> dict:
    summary = _paper_summary(hit)
    summary['Citations'] = hit.get('metadata', {}).get('citation_count', 0)
    return summary

def _hits(data: dict) -> list[dict]:
    return data.get('hits', {}).get('hits', [])

def _total_matches(data: dict) -> int:
    total = data.get('hits', {}).get('total', 0)
    if isinstance(total, dict):
        return int(total.get('value', 0))
    return int(total or 0)

async def _fetch_all_author_citation_hits(query: str, sort: str) -> tuple[list[dict], int]:
    fields = "titles,arxiv_eprints,citation_count"
    page_size = MAX_INSPIRE_PAGE_SIZE
    page = 1
    all_hits = []
    total_matches = 0

    while True:
        params = {'q': query, 'sort': sort, 'size': page_size, 'page': page, 'fields': fields}
        data = await _fetch_literature(params=params)
        page_hits = _hits(data)
        if page == 1:
            total_matches = _total_matches(data)

        all_hits.extend(page_hits)
        found_all_known_matches = total_matches > 0 and len(all_hits) >= total_matches
        if not page_hits or found_all_known_matches or len(page_hits) < page_size:
            break
        page += 1

    return all_hits, total_matches or len(all_hits)
    
async def search_papers(query: str, sort: str="mostrecent", page_size: int=DEFAULT_PAGE_SIZE, page: int=1) -> dict:
    """
    Searches for papers on INSPIRE-HEP.

    Args:
        query (str): The search query.
        sort (str): Sort order, either 'mostrecent' or 'mostcited'. Defaults to 'mostrecent'.
        page_size (int): Number of results per page. Defaults to DEFAULT_PAGE_SIZE.
        page (int): Page number. Defaults to 1.

    Returns:
        dict: A dictionary containing the list of papers found.
    """
    if sort not in {"mostrecent", "mostcited"}:
        sort = "mostrecent"
    size = max(1, page_size)
    
    params = {'q': query, 'sort': sort, 'size': size, 'page': page}
    try:
        data = await _fetch_literature(params=params)
    except Exception as e:
        return {'Error': f"Error in fetching data from INSPIRE-HEP: {e}"}
    
    results = {'Papers': [_paper_summary(hit) for hit in _hits(data)]}
    
    return results

async def get_paper_citations(query: str, direction: Literal["citing", "cited_by"] = "citing", page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """
    Retrieves the citation graph (references or citations) for a specific paper.

    Args:
        query (str): The search query to find the paper (e.g., arXiv ID or INSPIREHEP ID).
        direction (str): The direction of the citation graph. 
                         'citing' returns papers this paper cites (its references).
                         'cited_by' returns papers that cite this paper (citations).
                         Defaults to 'citing'.
        page_size (int): The number of results to return. Defaults to DEFAULT_PAGE_SIZE.

    Returns:
        dict: A dictionary containing the paper details and the citation graph.
    """
    direction_info = CITATION_DIRECTIONS.get(direction)
    if not direction_info:
        valid_directions = ", ".join(CITATION_DIRECTIONS)
        return {'Error': f"Invalid direction {direction}. The direction must be one of: {valid_directions}"}
    
    data = await search_papers(query=query)

    if 'Papers' not in data or not isinstance(data['Papers'], list) or not data['Papers']:
        return {'Error': f"Could not find any paper by query: {query}"}
        
    papers = data['Papers']
    if len(papers) > 1:
        results = {
            'Warning': f"{len(papers)} papers are found. Please specify the INSPIREHEP ID or arXiv ID of the paper you are looking for.",
            'Papers': papers
        }
        return results
    
    inspire_id = papers[0]['Inspire ID']
    fields = "titles,arxiv_eprints"
    params = {
        'q': f"{direction_info['query_prefix']}:recid:{inspire_id}",
        'sort': 'mostrecent',
        'size': max(1, page_size),
        'fields': fields,
    }
    try:
        response_json = await _fetch_literature(params=params)
    except Exception as e:
        return  {'Error': f"Error in tracking citations: {e}"}
    
    entries = [_paper_summary(hit) for hit in _hits(response_json)]

    results = {
        'Inspire ID': inspire_id,
        'Direction': direction,
        'Relationship': direction_info['relationship'],
        'Description': direction_info['description'],
        'Total Papers': len(entries),
        'Papers': entries,
    }
    
    return results

async def get_author_citations(
    author: str,
    sort: str = "mostrecent",
    page_size: int = DEFAULT_PAGE_SIZE,
    include_all_papers: bool = False,
) -> dict:
    """
    Retrieves the papers and citation counts for a specific author.

    Args:
        author (str): The author name (e.g., 'John Doe').
        sort (str): Sort order, either 'mostrecent' or 'mostcited'. Defaults to 'mostrecent'.
        page_size (int): Number of papers to include in the returned Papers list.
        include_all_papers (bool): Include every matched paper in 'All Papers'. Defaults to False.

    Returns:
        dict: A dictionary containing the author's displayed papers and citation total over all matched papers.
    """
    if not author:
        return {'Error': "Error: author parameter is required."}
    
    if sort not in {"mostrecent", "mostcited"}:
        sort = "mostrecent"

    query = f"a {author}"

    try:
        all_hits, total_matches = await _fetch_all_author_citation_hits(query=query, sort=sort)
    except Exception as e:
        return {'Error': f"Error in fetching data from INSPIRE-HEP: {e}"}

    all_entries = [_paper_summary_with_citations(hit) for hit in all_hits]
    displayed_entries = all_entries[:max(1, page_size)]
    total_citations = sum(paper['Citations'] for paper in all_entries)

    results = {
        'Total Citations': total_citations,
        'Total Papers': total_matches,
        'Returned Papers': len(displayed_entries),
        'Citation Scope': 'all matched papers',
        'Papers': displayed_entries,
    }
    if include_all_papers:
        results['All Papers'] = all_entries

    return results

async def track_citations_updates() -> dict:
    """
    Tracks updates to the user's citations since the last check.

    Returns:
        dict: A dictionary containing new publications and citation increases.
    """

    if not AUTHOR:
        return {'Error': "Error: AUTHOR environment variable is not set."}
    
    current_citations = await get_author_citations(AUTHOR, include_all_papers=True)
    if not current_citations or 'Error' in current_citations:
        return {'Error': f"Could not find any papers or citations for author: {AUTHOR}"}
    
    papers = current_citations.get('All Papers', current_citations['Papers'])
    current_map = {p['Inspire ID']: p['Citations'] for p in papers}

    if not os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, 'w') as f:
            json.dump(current_map, f)

        return {'Result': f"First run: Successfully recorded citations for author {AUTHOR}"}
    
    with open(RECORD_FILE, 'r') as f:
        previous_map = json.load(f)

    new_citations = []
    new_publications = []
    for paper in papers:
        pid = paper['Inspire ID']
        if pid not in previous_map:
            new_publications.append({
                'Title': paper['Title'],
                'arXiv ID': paper.get('arXiv ID', 'N/A'),
                'Citations': paper['Citations']
            })
        else:
            prev_count = previous_map[pid]
            if paper['Citations'] > prev_count:
                update = {
                    'Title': paper['Title'],
                    'Previous': prev_count,
                    'Current': paper['Citations'],
                    'Increase': paper['Citations'] - prev_count
                }
                new_citations.append(update)

    with open(RECORD_FILE, 'w') as f:
        json.dump(current_map, f)

    result_output = {}
    if new_publications:
        result_output['New Publications'] = new_publications
    if new_citations:
        result_output['Citation Updates'] = new_citations

    if result_output:
        return {'Result': result_output}
    else:
        return {'Result': f"No new publications or citations found for author '{AUTHOR}' since the last check."}
