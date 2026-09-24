import sqlite3
import tempfile
import unittest
from pathlib import Path

from ordbank_resources import OrdbankResources


class OrdbankResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name) / "test.sqlite3"
        db = sqlite3.connect(path)
        db.executescript(
            """
            CREATE TABLE form (word TEXT PRIMARY KEY, display TEXT, proper INTEGER, tag TEXT);
            CREATE TABLE compound (form TEXT, first TEXT, fugue TEXT, second TEXT);
            INSERT INTO form VALUES ('nordstrand', 'Nordstrand', 1, 'subst prop normert');
            INSERT INTO compound VALUES ('brettspill', 'brett', '', 'spill');
            INSERT INTO compound VALUES ('arbeidsgiver', 'arbeid', 's', 'giver');
            INSERT INTO compound VALUES ('imorgen', 'i', '', 'morgen');
            """
        )
        db.close()
        self.resources = OrdbankResources(path)

    def tearDown(self):
        self.resources.close(); self.temp.cleanup()

    def test_lookup_and_casefold(self):
        self.assertTrue(self.resources.lookup("Nordstrand")["proper"])
        self.assertEqual(self.resources.display("nordstrand"), "Nordstrand")
        self.assertIsNone(self.resources.lookup("mangler"))

    def test_compound_join_and_split(self):
        self.assertEqual(self.resources.compounds(["brett"], ["spill"]), ["brettspill"])
        self.assertEqual(self.resources.splits("BRETTSPILL"), ["brett spill"])
        self.assertEqual(
            self.resources.decompositions("BRETTSPILL"),
            [{"first": "brett", "linking": "", "second": "spill"}],
        )

    def test_component_repair_is_conditioned_on_the_other_side(self):
        self.assertEqual(
            self.resources.repair_compounds("bret", "spill", "left"),
            [{"form": "brettspill", "left": "brett", "right": "spill", "distance": 1}],
        )
        self.assertEqual(
            self.resources.repair_compounds("arbeids", "givr", "right"),
            [{"form": "arbeidsgiver", "left": "arbeids", "right": "giver", "distance": 1}],
        )
        self.assertEqual(self.resources.repair_compounds("bret", "giver", "left"), [])

    def test_repaired_whole_form_can_expose_a_recorded_split(self):
        self.assertEqual(
            self.resources.repair_splits("imårn"),
            [{"form": "imorgen", "split": "i morgen", "distance": 3}],
        )


if __name__ == "__main__":
    unittest.main()
