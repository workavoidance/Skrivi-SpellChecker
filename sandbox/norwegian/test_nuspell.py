import unittest
from nuspell_backend import parse_output
from engine import replace_word, words

class NativeProtocol(unittest.TestCase):
    def test_output_alignment_and_whitespace_rejection(self):
        parsed=parse_output('Enter some text: * OK\n\n& Wrong: budsjettx. How about: budsjett, to ord, blåbær\n\n# Wrong: zzxx. No suggestions.\n\n', ['hei','budsjettx','zzxx'])
        self.assertTrue(parsed['hei']['known'])
        self.assertEqual(parsed['budsjettx']['suggestions'], ['budsjett','blåbær'])
        self.assertEqual(parsed['zzxx']['suggestions'], [])
        self.assertIn('to ord',parsed['budsjettx']['raw_suggestions'])

    def test_misaligned_or_unrecognised_output_fails_closed(self):
        with self.assertRaises(RuntimeError): parse_output('* OK\n\n',['hei','du'])
        with self.assertRaises(RuntimeError): parse_output('unexpected\n\n',['hei'])
        with self.assertRaises(RuntimeError): parse_output('& Wrong: other. How about: hei\n\n',['hei'])

    def test_fragment_suggestions_do_not_replace_whole_token(self):
        row=parse_output('* OK\n& Wrong: postx. How about: post\n\n',['e-postx'])['e-postx']
        self.assertTrue(row['segmented'])
        self.assertFalse(row['known'])
        self.assertEqual(row['suggestions'],[])

    def test_only_selected_occurrence_changes(self):
        text='😀 budsjet  og budsjet.'
        token=words(text)[2]
        self.assertEqual(replace_word(text,token,'budsjett'),'😀 budsjet  og budsjett.')
        with self.assertRaises(ValueError): replace_word(text,token,'to ord')

if __name__ == '__main__': unittest.main()
