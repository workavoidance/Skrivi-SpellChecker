import json
from pathlib import Path
import tempfile
import unittest

from personal_dictionary import PersonalDictionary


class PersonalDictionaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "personal.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_remembered_words_survive_restart_and_match_case(self):
        first = PersonalDictionary(self.path)
        first.add("Nordstrand")
        second = PersonalDictionary(self.path)
        result = {"words": [{"word": "NORDSTRAND", "status": "UNCERTAIN", "suggestions": ["nordstrand"]}]}
        second.apply(result)
        self.assertEqual(result["words"][0]["status"], "OK")
        self.assertEqual(result["words"][0]["suggestions"], [])
        self.assertTrue(result["words"][0]["remembered"])

    def test_rejects_phrases_and_can_clear(self):
        dictionary = PersonalDictionary(self.path)
        with self.assertRaises(ValueError):
            dictionary.add("two words")
        dictionary.add("Skrivi")
        self.assertEqual(dictionary.clear(), 1)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["words"], [])

