import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from wordnet_help import build_index, WordnetHelp


class WordnetHelpTests(unittest.TestCase):
    def test_build_lookup_and_inflection_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            archive = folder / 'source.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('dat/words.tab', '1\tlekse\tNoun\n2\tskolearbeid\tNoun\n3\thjerne\tNoun\n4\torgan\tNoun\n5\tBrain\tNoun\n')
                bundle.writestr('dat/wordsenses.tab', '1\t1\t10\t\n2\t2\t11\t\n3\t3\t20\t\n4\t4\t21\t\n5\t5\t20\t\n')
                bundle.writestr('dat/relations.tab', '10\thyponymOf\thas_hyperonym\t11\ttaxonomic\n20\thyponymOf\thas_hyperonym\t21\ttaxonomic\n')
            database = folder / 'index.sqlite3'
            stats = build_index(archive, database)
            self.assertGreater(stats['senses'], 0)
            help_index = WordnetHelp(database)
            self.assertEqual(help_index.lookup('lekser')['lemma'], 'lekse')
            self.assertEqual(help_index.lookup('lekser')['senses'][0]['broader'], ['skolearbeid'])
            self.assertEqual(help_index.lookup('hjerne')['senses'][0]['broader'], ['organ'])
            self.assertNotIn('Brain', json.dumps(help_index.lookup('hjerne')))
            self.assertIsNone(help_index.lookup('gjerne'))

    def test_missing_database_is_an_offline_safe_fallback(self):
        self.assertFalse(WordnetHelp(None).available)
        self.assertEqual(WordnetHelp(None).lookup_many(['hjerne']), {})


if __name__ == '__main__':
    unittest.main()
