"""Contract tests for isolated lexical coverage; cached runtime supplies rapidfuzz."""
import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).parents[1]/'sandbox/norwegian'))

class Bank:
 def lookup(self,w):
  return {'proper':False,'tag':'subst mask appell ent be normert'} if w in {'boken','stasjon','kø'} else None

class Frequency:
 class Connection:
  def execute(self,q):return []
 connection=Connection()

class Native:
 def lookup(self,ws):
  return {w:dict(known=w=='trygt',suggestions=['boken'] if w=='boke' else [],raw_suggestions=[],segmented=False) for w in ws}

@unittest.skipUnless(importlib.util.find_spec('rapidfuzz'),'Uses existing cached Norwegian runtime')
class CoverageTests(unittest.TestCase):
 def make(self,policy):
  from experimental_lexical_coverage import CoverageNative
  return CoverageNative(policy,native=Native(),bank=Bank(),frequency=Frequency())
 def test_recognises_noun_genitive_but_not_arbitrary_suffix(self):
  r=self.make('genitive').lookup(['bokens','ukjents'])
  self.assertTrue(r['bokens']['known']);self.assertFalse(r['ukjents']['known'])
 def test_preserves_case_and_single_word_candidates(self):
  r=self.make('genitive').lookup(['Bokes'])['Bokes']
  self.assertIn('Bokens',r['suggestions'])
  self.assertTrue(all(not any(c.isspace() for c in w) for w in r['suggestions']))
 def test_productive_is_opt_in_and_accepts_linking_s(self):
  self.assertFalse(self.make('attested').lookup(['stasjonskø'])['stasjonskø']['known'])
  r=self.make('productive').lookup(['stasjonkø','stasjonskø'])
  self.assertIn('stasjonskø',r['stasjonkø']['suggestions']);self.assertTrue(r['stasjonskø']['known'])
 def test_proposal_only_adds_linking_candidate_without_acceptance(self):
  r=self.make('proposal_only').lookup(['stasjonkø','stasjonskø'])
  self.assertIn('stasjonskø',r['stasjonkø']['suggestions'])
  self.assertFalse(r['stasjonskø']['known'])
 def test_proposal_only_does_not_trust_frequency_for_acceptance(self):
  n=self.make('proposal_only');n.freq={'bokenstasjon':12};n.choices=['bokenstasjon']
  r=n.lookup(['bokenstasjon','bokenstason'])
  self.assertFalse(r['bokenstasjon']['known'])
  self.assertIn('bokenstasjon',r['bokenstason']['suggestions'])
 def test_keeps_existing_dictionary_acceptance(self):
  for policy in ['genitive','attested','productive']:
   self.assertTrue(self.make(policy).lookup(['trygt'])['trygt']['known'])

@unittest.skipUnless(importlib.util.find_spec('rapidfuzz'),'Uses existing cached Norwegian runtime')
class IntegratedCoverageTests(unittest.TestCase):
 def test_integrated_candidates_match_frozen_policy(self):
  from experimental_lexical_coverage import CoverageNative
  from lexical_coverage import CandidateCoverage
  old=CoverageNative('proposal_only',native=Native(),bank=Bank(),frequency=Frequency())
  new=CandidateCoverage(native=Native(),bank=Bank(),frequency=Frequency())
  words=['bokens','ukjents','Bokes','stasjonk\u00f8','stasjonsk\u00f8','trygt']
  a,b=old.lookup(words),new.lookup(words)
  for word in words:
   for field in ['known','suggestions','segmented']:
    self.assertEqual(a[word][field],b[word][field],(word,field))
  self.assertEqual(new.lookup(['Bokes'])['Bokes']['raw_suggestions'],[])

if __name__=='__main__':unittest.main()
