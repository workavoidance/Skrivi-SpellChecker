import unittest
from rapidfuzz import process
from rapidfuzz.distance import OSA
from engine import Lexicon

class CandidateRepairs(unittest.TestCase):
    def lexicon(self):
        lex=Lexicon.__new__(Lexicon)
        lex.revised=True;lex.process=process;lex.distance=OSA.distance
        lex.vocab={'bruke','buker','burke','a-bruke','brødre','brøde'}
        lex.choices=sorted(lex.vocab);lex.cache={}
        return lex

    def test_swap_has_single_edit_cost(self):
        lex=self.lexicon()
        self.assertEqual(lex.distance('brørde','brødre'),1)
        known,candidates=lex.candidates('brørde')
        self.assertFalse(known)
        self.assertIn('brødre',candidates)

    def test_preserve_known_word_and_case(self):
        lex=self.lexicon()
        self.assertEqual(lex.candidates('bruke'),(True,[]))
        _,candidates=lex.candidates('Brørde')
        self.assertIn('Brødre',candidates)
        self.assertFalse(any('-' in w for w in candidates))

if __name__=='__main__':unittest.main()
