import sqlite3
import tempfile
import unittest
from pathlib import Path

from traditional_resources import TraditionalResources


class TraditionalResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "test.sqlite3"
        connection = sqlite3.connect(self.database)
        connection.executescript(
            """
            CREATE TABLE scarrie_correction (typed TEXT, replacement TEXT, style TEXT);
            CREATE TABLE unigram (word TEXT PRIMARY KEY, count INTEGER);
            INSERT INTO scarrie_correction VALUES ('feil', 'riktig', 'MN');
            INSERT INTO unigram VALUES ('riktig', 999), ('feil', 2);
            """
        )
        connection.close()
        self.resources = TraditionalResources(self.database)

    def tearDown(self):
        self.resources.close()
        self.temp.cleanup()

    def test_correction_lookup_is_casefolded(self):
        self.assertEqual(self.resources.corrections("FEIL"), ["riktig"])

    def test_frequency_adjustment_preserves_context_when_weight_zero(self):
        original = {"feil": -1.0, "riktig": -2.0}
        self.assertEqual(self.resources.adjusted_scores(original, 0), original)
        adjusted = self.resources.adjusted_scores(original, 1)
        self.assertGreater(adjusted["riktig"], adjusted["feil"])


if __name__ == "__main__":
    unittest.main()
