import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path to import hepara
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from hepara.subagents.arxiv_agent.tools import download_pdf

async def test():
    print("Testing download_pdf by arXiv ID...")
    arxiv_id = "2605.15023"
    try:
        test_dir = "tests/tmp_downloads"
        os.makedirs(test_dir, exist_ok=True)
        os.environ["PDF_PATH"] = test_dir
        
        print(f"Downloading PDF for ID {arxiv_id}...")
        downloaded_path = await download_pdf(arxiv_id)
        
        # Verify the download
        if os.path.exists(downloaded_path):
            size = os.path.getsize(downloaded_path)
            print(f"File downloaded successfully: {downloaded_path} ({size} bytes)")
            if size > 0:
                print("Test passed.")
            else:
                print("Test failed: Downloaded file is empty.")
        else:
            print("Test failed: File does not exist.")

        # Cleanup
        if os.path.exists(downloaded_path):
            os.remove(downloaded_path)
            print(f"Cleaned up {downloaded_path}")
        if os.path.exists(test_dir) and not os.listdir(test_dir):
            os.rmdir(test_dir)
            print(f"Removed empty directory {test_dir}")

    except Exception as e:
        print(f"\nAn exception occurred during testing: {e}")

if __name__ == "__main__":
    asyncio.run(test())
