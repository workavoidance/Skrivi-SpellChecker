import unittest
from engine import words, single, replace_word, context
from evaluate import score

class Contracts(unittest.TestCase):
    def test_repeated_word_and_unicode(self):
        text='😀 Min sykel er rød; din sykel er blå.'
        token=[w for w in words(text) if w['word']=='sykel'][1]
        self.assertEqual(replace_word(text,token,'sykkel'),'😀 Min sykel er rød; din sykkel er blå.')
        with self.assertRaises(ValueError): replace_word(text,token,'en sykkel')
        with self.assertRaises(ValueError): replace_word('changed',token,'sykkel')
    def test_whitespace_and_markup(self):
        for bad in ['to ord','a\nb','a\u00a0b','<script>','']:
            self.assertFalse(single(bad))
        self.assertTrue(single('blåbær'))
    def test_sentence_context(self):
        text='Hei. Jeg vil hjerne lese. Takk.'
        token=next(w for w in words(text) if w['word']=='hjerne')
        sentence,a,b=context(text,token)
        self.assertEqual(sentence[a:b],'hjerne')
        self.assertNotIn('Takk',sentence)
    def test_metrics_count_occurrences(self):
        case={'text':'sykel sykel','errors':[{'word':'sykel','occurrence':1,'suggestions':['sykkel']}]}
        result={'words':[{'id':0,'status':'UNCERTAIN','suggestions':['sykkel'],'candidates':['sykkel']},
                         {'id':1,'status':'OK','suggestions':[],'candidates':['sykkel']}]}
        self.assertEqual(score(case,result)['false_alarms'],1)
        self.assertEqual(score(case,result)['top3'],0)

if __name__=='__main__': unittest.main()
