import unittest
from types import SimpleNamespace
import torch
from context_scoring import whole_scores
from context_experiments import proposal

class Tokenizer:
    mask_token_id=1
    pad_token_id=0
    def __call__(self,text,**kwargs):
        return {'input_ids':[2]+[ord(c) for c in text]+[3],
                'offset_mapping':[(0,0)]+[(i,i+1) for i in range(len(text))]+[(0,0)]}

class ContextChecks(unittest.TestCase):
    def test_candidate_letters_are_all_hidden(self):
        seen=[]
        def forward(input_ids,attention_mask):
            seen.extend(input_ids.tolist())
            return SimpleNamespace(logits=torch.zeros((*input_ids.shape,128)))
        model=SimpleNamespace(torch=torch,tokenizer=Tokenizer(),model=forward)
        scores,lengths=whole_scores(model,'x ab y',{'word':'ab','start':2,'end':4},['ab','ac'])
        self.assertEqual(seen[0],seen[1])
        self.assertEqual(seen[0][3:5],[1,1])
        self.assertIn(ord('x'),seen[0]);self.assertIn(ord('y'),seen[0])
        self.assertEqual(lengths,{'ab':2,'ac':2})
        self.assertEqual(scores['ab'],scores['ac'])

    def test_agreement_abstains_on_disagreement(self):
        c={'original':'a','whole':{'a':-10,'b':-1,'c':-8},
           'partial':{'a':-10,'b':-8,'c':-1},'neutral':{'a':-1,'b':-1,'c':-1},
           'lengths':{'a':1,'b':1,'c':1}}
        self.assertEqual(proposal(c,'whole_mask'),['b'])
        self.assertEqual(proposal(c,'agreement'),[])
        c['lengths']['a']=2
        self.assertEqual(proposal(c,'single_token'),[])

if __name__=='__main__':unittest.main()
