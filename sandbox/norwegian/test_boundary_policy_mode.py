import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from engine import Checker, OBT_JOIN_THRESHOLD, ORDBANK_JOIN_THRESHOLD


class FakeOrdbank:
    def decompositions(self, word):
        if word == "arbeidsgiver":
            return [{"first": "arbeid", "linking": "s", "second": "giver"}]
        return []

    def lookup(self, word):
        return None

    def repair_compounds(self, left, right, repair_side):
        return []


class FakeObt:
    def analyse(self, words):
        return {word: {"lexical_compound": False, "strict": []} for word in words}


class AcceptingObt:
    def analyse(self, words):
        return {word: {"lexical_compound": False,
                       "strict": [{"trusted": True, "suffix_pos": "subst"}]}
                for word in words}


class ComponentOrdbank(FakeOrdbank):
    def compounds(self, first_words, second_words):
        if "brett" in first_words and "spill" in second_words:
            return ["brettspill"]
        return []

    def decompositions(self, word):
        if word == "brettspill":
            return [{"first": "brett", "linking": "", "second": "spill"}]
        return super().decompositions(word)

    def repair_compounds(self, left, right, repair_side):
        if (left, right, repair_side) == ("bret", "spill", "left"):
            return [{"form": "brettspill", "left": "brett",
                     "right": "spill", "distance": 1}]
        return []


def base_result(text):
    return {
        "text": text,
        "words": [
            {"id": 0, "word": "arbeids", "start": 0, "end": 7,
             "start_utf16": 0, "end_utf16": 7, "status": "OK", "native_known": True},
            {"id": 1, "word": "giver", "start": 8, "end": 13,
             "start_utf16": 8, "end_utf16": 13, "status": "OK", "native_known": True},
            {"id": 2, "word": "kommer", "start": 14, "end": 20,
             "start_utf16": 14, "end_utf16": 20, "status": "OK", "native_known": True},
        ],
        "elapsed_seconds": 0, "load_seconds": 0,
    }


class BoundaryPolicyModeTests(unittest.TestCase):
    def checker(self, text):
        checker = Checker.__new__(Checker)
        checker.norbert = object()
        checker.ordbank_resources = FakeOrdbank()
        checker.obt_resources = FakeObt()
        checker.check = lambda supplied, mode: base_result(supplied)
        return checker

    def test_linking_letter_compound_uses_locked_ordbank_threshold(self):
        text = "arbeids giver kommer"
        checker = self.checker(text)
        with patch("experimental_inference.fast_whole",
                   return_value=({"arbeids giver": 0.0, "arbeidsgiver": -0.5}, None)):
            result = Checker.check_compound_policy(checker, text)
        self.assertEqual(result["words"][0]["suggestions"], ["arbeidsgiver"])
        self.assertEqual(result["words"][0]["boundary_source"], "ordbank")
        self.assertEqual(result["words"][0]["operation"], "join")

    def test_context_can_strongly_veto_stored_join(self):
        text = "arbeids giver kommer"
        checker = self.checker(text)
        with patch("experimental_inference.fast_whole",
                   return_value=({"arbeids giver": 0.0, "arbeidsgiver": -6.0}, None)):
            result = Checker.check_compound_policy(checker, text)
        self.assertEqual([row["word"] for row in result["words"]],
                         ["arbeids", "giver", "kommer"])

    def test_runtime_thresholds_match_locked_policy(self):
        self.assertEqual(ORDBANK_JOIN_THRESHOLD, -1.0)
        self.assertEqual(OBT_JOIN_THRESHOLD, 1.0)

    def test_stronger_overlapping_join_wins(self):
        text = "alle lever anser"
        checker = Checker.__new__(Checker)
        checker.norbert = object()
        checker.ordbank_resources = FakeOrdbank()
        checker.obt_resources = AcceptingObt()
        checker.nuspell_checker = SimpleNamespace(
            lexicon=SimpleNamespace(vocab={"allelever", "leveranser"})
        )
        checker.check = lambda supplied, mode: {
            "text": supplied, "elapsed_seconds": 0, "load_seconds": 0,
            "words": [
                {"id": 0, "word": "alle", "start": 0, "end": 4,
                 "start_utf16": 0, "end_utf16": 4, "status": "OK"},
                {"id": 1, "word": "lever", "start": 5, "end": 10,
                 "start_utf16": 5, "end_utf16": 10, "status": "OK"},
                {"id": 2, "word": "anser", "start": 11, "end": 16,
                 "start_utf16": 11, "end_utf16": 16, "status": "OK"},
            ],
        }

        def scores(model, supplied, token, choices):
            margin = 1.7 if choices[1] == "allelever" else 8.5
            return ({choices[0]: 0.0, choices[1]: margin}, None)

        with patch("experimental_inference.fast_whole", side_effect=scores):
            result = Checker.check_compound_policy(checker, text)
        self.assertEqual([row["word"] for row in result["words"]],
                         ["alle", "lever anser"])
        self.assertEqual(result["words"][1]["suggestions"], ["leveranser"])

    def component_checker(self):
        checker = Checker.__new__(Checker)
        checker.norbert = object()
        checker.ordbank_resources = ComponentOrdbank()
        checker.obt_resources = FakeObt()
        checker.nuspell_checker = None
        checker.check = lambda supplied, mode: {
            "text": supplied, "elapsed_seconds": 0, "load_seconds": 0,
            "words": [
                {"id": 0, "word": "bret", "start": 0, "end": 4,
                 "start_utf16": 0, "end_utf16": 4, "status": "UNCERTAIN",
                 "native_known": False, "native_suggestions": ["brett"]},
                {"id": 1, "word": "spill", "start": 5, "end": 10,
                 "start_utf16": 5, "end_utf16": 10, "status": "OK",
                 "native_known": True, "native_suggestions": []},
            ],
        }
        return checker

    def test_component_repair_compares_against_corrected_spaced_form(self):
        checker = self.component_checker()
        scores = {"bret spill": -4.0, "brett spill": 0.0, "brettspill": -0.75}
        with patch("experimental_inference.fast_whole", return_value=(scores, None)):
            result = Checker.check_compound_policy(checker, "bret spill")
        self.assertEqual(result["words"][0]["suggestions"], ["brettspill"])
        self.assertEqual(result["words"][0]["boundary_source"], "ordbank_component")
        self.assertEqual(result["words"][0]["boundary_comparison"], "brett spill")
        self.assertEqual(result["words"][0]["boundary_retrieval"],
                         "ordbank_component_distance")

    def test_component_repair_is_rejected_when_boundary_margin_is_too_low(self):
        checker = self.component_checker()
        scores = {"bret spill": -4.0, "brett spill": 0.0, "brettspill": -1.01}
        with patch("experimental_inference.fast_whole", return_value=(scores, None)):
            result = Checker.check_compound_policy(checker, "bret spill")
        self.assertEqual([row["word"] for row in result["words"]], ["bret", "spill"])


if __name__ == "__main__":
    unittest.main()
