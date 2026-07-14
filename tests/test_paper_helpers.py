import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils import paper_helpers


class PaperHelpersTest(unittest.TestCase):
    def test_update_database_generates_missing_sidecars_and_indexes_all_markdowns_when_db_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "1234.5678.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")
            existing_pdf_path = Path(tmpdir) / "2301.00001.pdf"
            existing_pdf_path.write_bytes(b"%PDF-1.4")
            existing_md_path = Path(tmpdir) / "2301.00001.md"
            existing_md_path.write_text("existing markdown", encoding="utf-8")
            orphan_md_path = Path(tmpdir) / "orphan.md"
            orphan_md_path.write_text("orphan markdown", encoding="utf-8")

            with (
                patch.dict("os.environ", {"PDF_PATH": tmpdir}),
                patch.object(paper_helpers.pymupdf4llm, "to_markdown", return_value="paper markdown") as to_markdown,
                patch.object(paper_helpers, "_get_indexed_document_ids", return_value=set()),
                patch.object(paper_helpers, "add_to_chromadb") as add_to_chromadb,
            ):
                paper_helpers.update_database()

            expected_md_path = pdf_path.with_suffix(".md")
            self.assertEqual(expected_md_path.read_text(encoding="utf-8"), "paper markdown")
            self.assertEqual(existing_md_path.read_text(encoding="utf-8"), "existing markdown")
            to_markdown.assert_called_once_with(str(pdf_path), show_progress=False)
            indexed_arxiv_ids = {
                call.args[1]["arXiv ID"]
                for call in add_to_chromadb.call_args_list
            }
            self.assertEqual(indexed_arxiv_ids, {"1234.5678", "2301.00001"})

    def test_update_database_indexes_only_markdowns_missing_from_existing_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexed_pdf_path = Path(tmpdir) / "1234.5678.pdf"
            indexed_pdf_path.write_bytes(b"%PDF-1.4")
            indexed_md_path = indexed_pdf_path.with_suffix(".md")
            indexed_md_path.write_text("already indexed", encoding="utf-8")
            missing_pdf_path = Path(tmpdir) / "2301.00001.pdf"
            missing_pdf_path.write_bytes(b"%PDF-1.4")
            missing_md_path = missing_pdf_path.with_suffix(".md")
            missing_md_path.write_text("needs indexing", encoding="utf-8")

            with (
                patch.dict("os.environ", {"PDF_PATH": tmpdir}),
                patch.object(paper_helpers, "_get_indexed_document_ids", return_value={"1234.5678"}),
                patch.object(paper_helpers, "add_to_chromadb") as add_to_chromadb,
            ):
                paper_helpers.update_database()

            add_to_chromadb.assert_called_once()
            self.assertEqual(add_to_chromadb.call_args.args[0], "needs indexing")
            self.assertEqual(
                add_to_chromadb.call_args.args[1],
                {
                    "Document ID": "2301.00001",
                    "Source File": "2301.00001.pdf",
                    "arXiv ID": "2301.00001",
                },
            )
            self.assertEqual(add_to_chromadb.call_args.args[2], tmpdir)

    def test_update_database_indexes_manual_pdf_by_arxiv_id_from_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "manual paper name.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")
            md_path = pdf_path.with_suffix(".md")
            md_path.write_text("This is arXiv:2401.00001v2 content.", encoding="utf-8")

            with (
                patch.dict("os.environ", {"PDF_PATH": tmpdir}),
                patch.object(paper_helpers, "_get_indexed_document_ids", return_value=set()),
                patch.object(paper_helpers, "add_to_chromadb") as add_to_chromadb,
            ):
                paper_helpers.update_database()

            add_to_chromadb.assert_called_once()
            self.assertEqual(
                add_to_chromadb.call_args.args[1],
                {
                    "Document ID": "2401.00001",
                    "Source File": "manual paper name.pdf",
                    "arXiv ID": "2401.00001",
                },
            )

    def test_update_database_indexes_manual_pdf_without_arxiv_id_by_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "local notes.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")
            md_path = pdf_path.with_suffix(".md")
            md_path.write_text("No arXiv identifier in this file.", encoding="utf-8")

            with (
                patch.dict("os.environ", {"PDF_PATH": tmpdir}),
                patch.object(paper_helpers, "_get_indexed_document_ids", return_value=set()),
                patch.object(paper_helpers, "add_to_chromadb") as add_to_chromadb,
            ):
                paper_helpers.update_database()

            add_to_chromadb.assert_called_once()
            self.assertEqual(
                add_to_chromadb.call_args.args[1],
                {
                    "Document ID": "local notes",
                    "Source File": "local notes.pdf",
                },
            )


if __name__ == "__main__":
    unittest.main()
