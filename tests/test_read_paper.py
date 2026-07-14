import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hepara.subagents.arxiv_agent import tools
from utils import paper_helpers


class ReadPaperTest(unittest.IsolatedAsyncioTestCase):
    async def test_read_paper_generates_missing_markdown_for_stored_pdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "1234.5678.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")

            with (
                patch.dict("os.environ", {"PDF_PATH": tmpdir}),
                patch.object(paper_helpers.pymupdf4llm, "to_markdown", return_value="paper markdown") as to_markdown,
            ):
                content = await tools.read_paper("1234.5678")

            self.assertEqual(content, "paper markdown")
            self.assertEqual((Path(tmpdir) / "1234.5678.md").read_text(encoding="utf-8"), "paper markdown")
            to_markdown.assert_called_once_with(str(pdf_path), show_progress=False)

    async def test_read_paper_returns_error_when_stored_pdf_conversion_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "1234.5678.pdf").write_bytes(b"%PDF-1.4")

            with (
                patch.dict("os.environ", {"PDF_PATH": tmpdir}),
                patch.object(paper_helpers.pymupdf4llm, "to_markdown", side_effect=RuntimeError("boom")),
            ):
                content = await tools.read_paper("1234.5678")

            self.assertIn("Error: Found stored PDF", content)
            self.assertIn("boom", content)

    async def test_download_pdf_creates_destination_directory(self):
        class FakeResponse:
            content = b"%PDF-1.4"

        async def fake_search_papers(*args, **kwargs):
            return [{"PDF URL": "https://example.test/paper.pdf"}]

        async def fake_rate_limit_request(*args, **kwargs):
            return FakeResponse()

        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "nested" / "pdfs"

            with (
                patch.object(tools, "search_papers", side_effect=fake_search_papers),
                patch.object(tools, "_rate_limit_request", side_effect=fake_rate_limit_request),
                patch.dict("os.environ", {"PDF_PATH": str(target_dir)}),
                patch.object(paper_helpers.pymupdf4llm, "to_markdown", return_value="paper markdown"),
                patch.object(tools, "add_to_chromadb"),
            ):
                downloaded_path = await tools.download_pdf("1234.5678")

            self.assertTrue(Path(downloaded_path).exists())
            self.assertEqual(Path(downloaded_path).parent, target_dir)
            self.assertEqual(Path(downloaded_path).with_suffix(".md").read_text(encoding="utf-8"), "paper markdown")


if __name__ == "__main__":
    unittest.main()
