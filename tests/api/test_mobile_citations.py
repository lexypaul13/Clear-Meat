"""Unit tests for mobile optimizer citation handling.

These tests verify that:
- Citations without URLs are still included in the mobile response
- Grounding citations are merged into the mobile response and assigned IDs
"""

import unittest

from app.api.v1.endpoints.products import _optimize_for_mobile


class TestMobileCitations(unittest.TestCase):
    def test_includes_citations_without_urls(self):
        """Citations lacking URLs should still appear in the mobile response."""
        assessment = {
            "summary": "This product contains preservatives requiring moderation.",
            "risk_summary": {"grade": "C", "color": "Yellow"},
            "ingredients_assessment": {
                "high_risk": [],
                "moderate_risk": [],
                "low_risk": [],
            },
            # Citation with no URL should remain visible
            "citations": [
                {"id": 1, "title": "Health effects of ingredient X", "year": 2023}
            ],
            "metadata": {"product_name": "Test Product"},
        }

        mobile = _optimize_for_mobile(assessment)

        self.assertIn("citations", mobile)
        self.assertEqual(len(mobile["citations"]), 1)
        self.assertEqual(mobile["citations"][0]["id"], 1)
        self.assertEqual(mobile["citations"][0]["title"], "Health effects of ingredient X")
        # URL may be missing; ensure key exists and is a string
        self.assertIn("url", mobile["citations"][0])
        self.assertIsInstance(mobile["citations"][0]["url"], str)

    def test_merges_grounding_citations_with_ids(self):
        """Grounding citations should be merged and assigned IDs in mobile response."""
        assessment = {
            "summary": "This product contains preservatives requiring moderation.",
            "risk_summary": {"grade": "C", "color": "Yellow"},
            "ingredients_assessment": {
                "high_risk": [],
                "moderate_risk": [],
                "low_risk": [],
            },
            # No explicit citations from the main assessment
            "citations": [],
            # Grounding citations discovered via search
            "grounding_citations": [
                {"title": "FDA Guidance on Ingredient X", "url": "https://www.fda.gov/example"},
                {"title": "WHO Safety Assessment on Ingredient X", "url": "https://www.who.int/example"},
            ],
            "metadata": {"product_name": "Test Product"},
        }

        mobile = _optimize_for_mobile(assessment)

        self.assertIn("citations", mobile)
        # Expect two citations merged from grounding
        self.assertEqual(len(mobile["citations"]), 2)

        # Check IDs are assigned sequentially and URLs present
        self.assertEqual(mobile["citations"][0]["id"], 1)
        self.assertEqual(mobile["citations"][1]["id"], 2)
        self.assertTrue(mobile["citations"][0]["url"].startswith("http"))
        self.assertTrue(mobile["citations"][1]["url"].startswith("http"))


if __name__ == "__main__":
    unittest.main()


