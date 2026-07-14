import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path to import hepara
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from hepara.subagents.arxiv_agent.tools import search_papers

async def test():
    print("Testing search_papers...")
    query = "all:Higgs boson"
    try:
        results = await search_papers(query, max_results=3)
        print(f"Found {len(results)} papers for query: '{query}'")
        
        for i, paper in enumerate(results):
            print(f"\nPaper {i+1}:")
            print(f"  Title: {paper.get('Title')}")
            print(f"  Authors: {paper.get('Authors')}")
            print(f"  arXiv ID: {paper.get('arXiv ID')}")
            print(f"  Published: {paper.get('Published Date')}")
        
        if len(results) > 0:
            print("\nTest passed.")
        else:
            print("\nTest failed: No results found.")
            
    except Exception as e:
        print(f"\nAn exception occurred during testing: {e}")

if __name__ == "__main__":
    asyncio.run(test())
