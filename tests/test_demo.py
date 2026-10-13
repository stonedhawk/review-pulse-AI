"""Runs the no-key demo pipeline end to end on a throwaway database.

    python -m unittest
"""
import os
import tempfile
import unittest

# Settings are read on first import of core.config, so point at a temp database first.
_tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp.name, 'test.db')}"
for key in ("PLAY_STORE_PACKAGE_NAME", "GOOGLE_APPLICATION_CREDENTIALS_JSON", "GEMINI_API_KEY"):
    os.environ.pop(key, None)

from core.analyzer import ReviewAnalyzer  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import Base, SessionLocal, engine  # noqa: E402
from core.demo import MOCK_REVIEWS, KeywordClusterer, seed_mock_reviews  # noqa: E402
from core.llm_client import GeminiClient  # noqa: E402


class DemoPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_mock_reviews(db)
        finally:
            db.close()
        cls.stats = ReviewAnalyzer(clusterer=KeywordClusterer()).run_analysis()

    def test_every_review_is_clustered(self):
        self.assertEqual(sum(s["count"] for s in self.stats.values()), len(MOCK_REVIEWS))

    def test_priority_score_is_rating_drag(self):
        # 6 crash reviews averaging 7/6 stars against a 4.5 target: 6 * (4.5 - 7/6) = 20.0
        crash = self.stats["STARTUP_CRASH"]
        self.assertEqual(crash["count"], 6)
        self.assertEqual(crash["priority_score"], 20.0)

    def test_praise_scores_zero(self):
        self.assertEqual(self.stats["GENERIC_PRAISE"]["priority_score"], 0.0)

    @unittest.skipIf(settings.GEMINI_API_KEY, "a local .env sets GEMINI_API_KEY")
    def test_gemini_without_key_explains_the_demo(self):
        with self.assertRaisesRegex(ValueError, "pulse.py demo"):
            GeminiClient()


if __name__ == "__main__":
    unittest.main()
