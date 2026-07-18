import os
import unittest
from unittest.mock import patch

from hepara.bot_tasks import (
    _deduplicate_articles_by_arxiv_id,
    _filter_articles_by_keywords,
    _get_categories,
    _merge_relevant_articles,
    _semantic_matches_from_query_results,
)


class DailyKeywordFilterTest(unittest.TestCase):
    def setUp(self):
        self.articles = [
            {
                "title": "Vector-like leptons at the LHC",
                "abstract": "We study collider signatures.",
            },
            {
                "title": "A precision QCD calculation",
                "abstract": "Dark matter appears only in the abstract.",
            },
            {
                "title": "Lattice gauge theory update",
                "abstract": "No selected topic appears here.",
            },
        ]

    def test_empty_keywords_keeps_all_articles(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_filter_articles_by_keywords(self.articles), self.articles)

    def test_matches_keyword_phrase_in_title_case_insensitively(self):
        with patch.dict(os.environ, {"KEYWORDS": "vector-like lepton"}, clear=True):
            result = _filter_articles_by_keywords(self.articles)

        self.assertEqual([article["title"] for article in result], ["Vector-like leptons at the LHC"])

    def test_matches_keyword_phrase_in_abstract(self):
        with patch.dict(os.environ, {"KEYWORDS": "dark matter"}, clear=True):
            result = _filter_articles_by_keywords(self.articles)

        self.assertEqual([article["title"] for article in result], ["A precision QCD calculation"])

    def test_drops_articles_without_keyword_matches(self):
        with patch.dict(os.environ, {"KEYWORDS": "neutrino"}, clear=True):
            self.assertEqual(_filter_articles_by_keywords(self.articles), [])

    def test_semantic_matches_convert_cosine_distance_to_similarity(self):
        articles = [
            {
                "arxiv_id": "2607.00001",
                "category": "hep-ph",
                "title": "Heavy lepton partners",
                "abstract": "A collider study.",
            },
            {
                "arxiv_id": "2607.00002",
                "category": "hep-ph",
                "title": "Unrelated lattice result",
                "abstract": "A different topic.",
            },
        ]
        query_results = {
            "ids": [["2607.00001", "2607.00002"]],
            "distances": [[0.2, 0.8]],
        }

        result = _semantic_matches_from_query_results(articles, query_results, threshold=0.5)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["arxiv_id"], "2607.00001")
        self.assertAlmostEqual(result[0]["relevance_score"], 0.8)
        self.assertEqual(result[0]["relevance_reasons"], ["semantic match 0.80"])

    def test_merge_relevant_articles_keeps_keyword_and_semantic_matches(self):
        keyword_match = {
            "arxiv_id": "2607.00001",
            "title": "Exact keyword match",
            "relevance_score": 1.0,
            "relevance_reasons": ["keyword match"],
        }
        semantic_match = {
            "arxiv_id": "2607.00002",
            "title": "Semantic match",
            "relevance_score": 0.72,
            "relevance_reasons": ["semantic match 0.72"],
        }

        result = _merge_relevant_articles([keyword_match], [semantic_match])

        self.assertEqual([article["arxiv_id"] for article in result], ["2607.00001", "2607.00002"])

    def test_get_categories_deduplicates_configured_categories(self):
        with patch.dict(os.environ, {"CATEGORIES": "hep-ph, hep-th, hep-ph, ,hep-ex"}, clear=True):
            self.assertEqual(_get_categories(), ["hep-ph", "hep-th", "hep-ex"])

    def test_deduplicates_articles_by_arxiv_id_and_preserves_categories(self):
        articles = [
            {
                "arxiv_id": "2607.00001",
                "category": "hep-ph",
                "title": "Shared paper",
                "link": "https://arxiv.org/abs/2607.00001",
            },
            {
                "arxiv_id": "2607.00001",
                "category": "hep-th",
                "title": "Shared paper",
                "link": "https://arxiv.org/abs/2607.00001",
            },
            {
                "arxiv_id": "2607.00002",
                "category": "hep-ph",
                "title": "Unique paper",
                "link": "https://arxiv.org/abs/2607.00002",
            },
        ]

        result = _deduplicate_articles_by_arxiv_id(articles)

        self.assertEqual([article["arxiv_id"] for article in result], ["2607.00001", "2607.00002"])
        self.assertEqual(result[0]["category"], "hep-ph, hep-th")
        self.assertEqual(result[0]["categories"], ["hep-ph", "hep-th"])

    def test_deduplicates_unknown_ids_by_link_not_unknown_id_label(self):
        articles = [
            {
                "arxiv_id": "Unknown ID",
                "category": "hep-ph",
                "title": "First unknown",
                "link": "https://arxiv.org/abs/unknown-one",
            },
            {
                "arxiv_id": "Unknown ID",
                "category": "hep-th",
                "title": "Second unknown",
                "link": "https://arxiv.org/abs/unknown-two",
            },
        ]

        result = _deduplicate_articles_by_arxiv_id(articles)

        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
