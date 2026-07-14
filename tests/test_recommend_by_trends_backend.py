import importlib
import os
import unittest
from unittest.mock import patch

import pandas as pd


class FakeArxivFlow:
    calls = []
    closed = False

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        FakeArxivFlow.calls.append(kwargs)

    async def get_arxiv_data(self, download_pdfs=False):
        return pd.DataFrame(
            [
                {
                    "arXiv ID": "2605.00001",
                    "Title": "Paper A",
                    "Keywords": "dark matter, higgs, collider",
                },
                {
                    "arXiv ID": "2605.00002",
                    "Title": "Paper B",
                    "Keywords": "dark matter, neutrino",
                },
            ]
        )

    async def close(self):
        FakeArxivFlow.closed = True


class RecommendByTrendsBackendTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeArxivFlow.calls = []
        FakeArxivFlow.closed = False

    async def _run_with_env(self, env):
        with patch.dict(os.environ, env, clear=True):
            import hepara.subagents.arxiv_agent.tools as tools

            tools = importlib.reload(tools)
            with patch.object(tools, "arXivFlow", FakeArxivFlow):
                return await tools.recommend_by_trends(max_results=7)

    async def test_ollama_backend_passes_only_ollama_model(self):
        result = await self._run_with_env(
            {
                "ARXIVFLOW_KEYWORD_BACKEND": "ollama",
                "CATEGORIES": "hep-ph, hep-th",
                "OLLAMA_MODEL": "llama3.2",
            }
        )

        self.assertNotIn("error", result)
        self.assertEqual(
            FakeArxivFlow.calls[0],
            {
                "categories": ["hep-ph", "hep-th"],
                "max_results": 7,
                "ollama_model": "llama3.2",
            },
        )
        self.assertTrue(FakeArxivFlow.closed)

    async def test_gemini_backend_passes_only_gemini_settings(self):
        result = await self._run_with_env(
            {
                "ARXIVFLOW_KEYWORD_BACKEND": "gemini",
                "CATEGORIES": "hep-ph",
                "GOOGLE_MODEL": "gemini-2.5-flash",
                "GOOGLE_API_KEY": "test-key",
                "OLLAMA_MODEL": "llama3.2",
            }
        )

        self.assertNotIn("error", result)
        self.assertEqual(
            FakeArxivFlow.calls[0],
            {
                "categories": ["hep-ph"],
                "max_results": 7,
                "gemini_model": "gemini-2.5-flash",
                "gemini_api_key": "test-key",
            },
        )
        self.assertTrue(FakeArxivFlow.closed)

    async def test_ollama_backend_requires_ollama_model(self):
        result = await self._run_with_env(
            {
                "ARXIVFLOW_KEYWORD_BACKEND": "ollama",
                "CATEGORIES": "hep-ph",
            }
        )

        self.assertIn("OLLAMA_MODEL", result["error"])
        self.assertEqual(FakeArxivFlow.calls, [])

    async def test_gemini_backend_requires_model_and_key(self):
        result = await self._run_with_env(
            {
                "ARXIVFLOW_KEYWORD_BACKEND": "gemini",
                "CATEGORIES": "hep-ph",
                "GOOGLE_MODEL": "gemini-2.5-flash",
            }
        )

        self.assertIn("GOOGLE_MODEL and GOOGLE_API_KEY", result["error"])
        self.assertEqual(FakeArxivFlow.calls, [])


if __name__ == "__main__":
    unittest.main()
