import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from split_resources import SplitResources, rank_split_token, SPLIT_THRESHOLD


class FakeOrdbank:
    def repair_splits(self, word, **kwargs):
        return [
            {"form": "imorgen", "split": "i morgen", "distance": 3},
            {"form": "imorgen", "split": "imo rgen", "distance": 3},
        ] if word == "imårn" else []


class SplitResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.resource = root / "phrases.json"
        self.overrides = root / "overrides.json"
        self.resource.write_text(json.dumps({"phrases": [{
            "phrase": "i morgen", "joined": "imorgen",
            "development_count": 2, "evaluation_count": 0, "total_count": 2,
        }]}), encoding="utf-8")
        self.overrides.write_text(json.dumps({
            "idag": {"suggestion": "i dag", "authority": "test",
                     "source_url": "https://example.invalid/idag"}
        }), encoding="utf-8")
        self.resources = SplitResources(self.resource, self.overrides, FakeOrdbank())

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_and_override(self):
        self.assertEqual(SPLIT_THRESHOLD, 3.0)
        self.assertEqual(self.resources.exact("IMORGEN")[0]["phrase"], "i morgen")
        self.assertEqual(self.resources.override("IDAG")["suggestion"], "i dag")

    def test_repaired_candidate_requires_matching_ordbank_and_corpus_split(self):
        self.assertEqual(
            self.resources.repaired("imårn"),
            [{"phrase": "i morgen", "joined": "imorgen",
              "development_count": 2, "evaluation_count": 0,
              "total_count": 2, "distance": 3}],
        )

    def test_repaired_split_must_beat_best_single_word_correction(self):
        row = {"word": "imårn", "start": 0, "end": 5,
               "native_known": False, "candidates": ["imorgen", "jern"]}
        values = {"imårn": -5.0, "imorgen": 0.0, "jern": -2.0,
                  "i morgen": 3.5}
        with patch("experimental_inference.fast_whole", return_value=(values, None)):
            proposal = rank_split_token("imårn kommer", row, object(), self.resources)
        self.assertEqual(proposal["suggestion"], "i morgen")
        self.assertEqual(proposal["comparison"], "imorgen")

    def test_repaired_split_loses_when_an_ordinary_correction_is_better(self):
        row = {"word": "imårn", "start": 0, "end": 5,
               "native_known": False, "candidates": ["imorgen", "jern"]}
        values = {"imårn": -5.0, "imorgen": 0.0, "jern": 4.0,
                  "i morgen": 5.0}
        with patch("experimental_inference.fast_whole", return_value=(values, None)):
            self.assertIsNone(rank_split_token(
                "imårn kommer", row, object(), self.resources))

    def test_authority_override_does_not_depend_on_model_margin(self):
        row = {"word": "idag", "start": 0, "end": 4,
               "native_known": True, "candidates": []}
        values = {"idag": 2.0, "i dag": 1.0}
        with patch("experimental_inference.fast_whole", return_value=(values, None)):
            proposal = rank_split_token("idag", row, object(), self.resources)
        self.assertEqual(proposal["retrieval"], "authority_override")


if __name__ == "__main__":
    unittest.main()
