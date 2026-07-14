import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path to import hepara
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from hepara.subagents.arxiv_agent.tools import recommend_by_trends

async def test():
    print("Testing recommend_by_trends...")
    try:
        # We can limit max_results to speed up the test
        result = await recommend_by_trends(max_results=10)
        print("Result:")
        import json
        print(json.dumps(result, indent=2))
        
        if "error" in result:
            print("\nTest failed with error.")
        else:
            print("\nTest passed.")
    except Exception as e:
        print(f"\nAn exception occurred during testing: {e}")

if __name__ == "__main__":
    asyncio.run(test())
