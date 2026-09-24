import unittest
from types import SimpleNamespace
from engine import words, Norbert
from iteration_session import short_context, cleaner_context, fast_whole, fast_rank, ORIGINAL_WHOLE
from test_context_scoring import Tokenizer
import torch

class IterationChecks(unittest.TestCase):
    def test_internal_copy_keeps_target_and_source_unchanged(self):
        text='aa xx bb xx cc';tokens=words(text)
        for t in tokens:
            t.update(status='LIKELY_ERROR',suggestions=['longer'],scores=[('longer',-1),(t['word'],-10)])
        fn,repairs=cleaner_context({'words':tokens},SimpleNamespace(vocab={'aa','bb','cc'}))
        sentence,a,b=fn(text,tokens[3])
        self.assertEqual(sentence,'aa longer bb xx cc')
        self.assertEqual(sentence[a:b],'xx')
        self.assertEqual(text,'aa xx bb xx cc')
        sentence,a,b=fn(text,tokens[1])
        self.assertEqual(sentence,'aa xx bb longer cc')
        self.assertEqual(sentence[a:b],'xx')

    def test_short_context_preserves_target_and_sentence_boundary(self):
        text='Before. '+' '.join('word'+str(i) for i in range(20))+'. After.'
        token=words(text)[11]
        s,a,b=short_context(text,token)
        self.assertEqual(s[a:b],token['word'])
        self.assertEqual(len(words(s)),13)
        self.assertNotIn('Before',s);self.assertNotIn('After',s)

    def test_dedup_matches_reference_with_fewer_rows(self):
        seen=[]
        def forward(input_ids,attention_mask):
            seen.extend(input_ids.tolist())
            return SimpleNamespace(logits=torch.arange(128,dtype=torch.float32).expand(*input_ids.shape,128))
        model=SimpleNamespace(torch=torch,tokenizer=Tokenizer(),model=forward)
        token={'word':'ab','start':2,'end':4};candidates=['ab','ac','abc']
        original=ORIGINAL_WHOLE(model,'x ab y',token,candidates);count=len(seen);seen.clear()
        optimized=fast_whole(model,'x ab y',token,candidates)
        self.assertEqual(original,optimized)
        self.assertEqual(count,3);self.assertEqual(len(seen),2)

    def test_partial_dedup_preserves_scores(self):
        seen=[]
        def forward(input_ids,attention_mask):
            seen.extend(input_ids.tolist())
            return SimpleNamespace(logits=torch.arange(128,dtype=torch.float32).expand(*input_ids.shape,128))
        model=SimpleNamespace(torch=torch,tokenizer=Tokenizer(),model=forward)
        token={'word':'ab','start':2,'end':4}
        reference=Norbert.rank(model,'x ab y',token,['ab','ac'])
        self.assertEqual(len(seen),4);seen.clear()
        optimized=fast_rank(model,'x ab y',token,['ab','ac'])
        self.assertEqual(reference,optimized);self.assertEqual(len(seen),3)

if __name__=='__main__':unittest.main()
