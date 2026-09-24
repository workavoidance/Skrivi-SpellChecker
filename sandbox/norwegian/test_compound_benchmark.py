import json
from pathlib import Path
import unittest


HERE = Path(__file__).parent
ROOT = HERE / "compound-benchmark"
EXPECTED = {
    "established_boundary": 30,
    "obt_boundary_probe": 30,
    "clean_separate_phrase": 40,
    "compound_internal_typo": 25,
    "proper_name_control": 15,
}


class CompoundBenchmarkTests(unittest.TestCase):
    def test_frozen_splits_are_disjoint_reversible_and_complete(self):
        ids_by_split = {}
        for split in ("development", "evaluation"):
            rows = json.loads((ROOT / f"{split}.json").read_text(encoding="utf-8"))
            counts = {category: 0 for category in EXPECTED}
            sentence_ids = set()
            for row in rows:
                counts[row["category"]] += 1
                sentence_id = row["source"]["sent_id"]
                self.assertNotIn(sentence_id, sentence_ids)
                sentence_ids.add(sentence_id)
                target = row["target"]
                self.assertEqual(row["text"][target["start"]:target["end"]], target["typed"])
                if target["action"] == "replace":
                    restored = (row["text"][:target["start"]] + target["answer"]
                                + row["text"][target["end"]:])
                    self.assertEqual(restored, row["source"]["original_text"])
                else:
                    self.assertEqual(row["text"], row["source"]["original_text"])
                    self.assertEqual(target["typed"], target["answer"])
            self.assertEqual(counts, EXPECTED)
            ids_by_split[split] = sentence_ids
        self.assertFalse(ids_by_split["development"] & ids_by_split["evaluation"])

    def test_manifest_hashes_match_outputs(self):
        import hashlib
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        for split in ("development", "evaluation"):
            path = ROOT / f"{split}.json"
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             manifest["splits"][split]["output_sha256"])


if __name__ == "__main__":
    unittest.main()
