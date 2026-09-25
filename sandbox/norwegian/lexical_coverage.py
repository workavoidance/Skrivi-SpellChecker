"""Opt-in candidate coverage; cached assets only, never accepts compounds by frequency.

Mirrors the validated proposal-only experiment. The server serializes checks;
SQLite read-only connections may move between its sequential request threads.
"""
import sqlite3
from ordbank_resources import DATABASE as ORDBANK_DATABASE
from traditional_resources import DATABASE as FREQUENCY_DATABASE


def available():
    return ORDBANK_DATABASE.is_file() and FREQUENCY_DATABASE.is_file()


def request_safe_connection(resource):
    resource.connection.close()
    resource.connection = sqlite3.connect(
        f"file:{resource.database.as_posix()}?mode=ro", uri=True, check_same_thread=False)

from functools import lru_cache
from rapidfuzz import process
from rapidfuzz.distance import OSA
from engine import recase, single
from nuspell_backend import NativeNuspell
from ordbank_resources import OrdbankResources
from traditional_resources import TraditionalResources


class CandidateCoverage:
    def __init__(self, native=None, bank=None, frequency=None):
        self.native=native or NativeNuspell()
        self.bank=bank or OrdbankResources()
        self.frequency=frequency or TraditionalResources()
        # Server checks are serialized, but each request has a different thread.
        if bank is None:
            request_safe_connection(self.bank)
        if frequency is None:
            request_safe_connection(self.frequency)
        self.cache={}
        self.freq={w:n for w,n in self.frequency.connection.execute('select word,count from unigram where count>=5')
                   if w.isalpha() and w.islower() and len(w)>=8}
        self.choices=sorted(self.freq)

    @lru_cache(maxsize=50000)
    def noun(self,w):
        row=self.bank.lookup(w)
        return bool(row and not row['proper'] and row['tag'].startswith('subst ') and 'normert' in row['tag'].split())

    @lru_cache(maxsize=50000)
    def compound(self,w):
        for i in range(3,len(w)-1):
            left,right=w[:i],w[i:]
            if self.noun(right) and (self.noun(left) or (left.endswith('s') and self.noun(left[:-1]))):
                return True
        return False

    def genitive(self,w):
        return len(w)>=5 and w.endswith('s') and not w[-2] in 'sxz' and self.noun(w[:-1])

    def lookup(self,words):
        raw=self.native.lookup(words)
        for word in words:
            if word in self.cache:
                continue
            info=raw[word]
            if info['known'] or info['segmented'] or not word.isalpha():
                self.cache[word]=info
                continue
            lower=word.casefold()
            recognised=self.genitive(lower)
            if recognised:
                self.cache[word]=dict(known=True,suggestions=[],raw_suggestions=[],segmented=False)
                continue
            additions=[]
            if lower.endswith('s') and len(lower)>=5:
                base=lower[:-1]
                for candidate in self.native.lookup([base])[base]['suggestions'][:16]:
                    if not candidate.endswith(('s','x','z')) and self.noun(candidate.casefold()):
                        additions.append(candidate+'s')
            if len(lower)>=8:
                for candidate,_,_ in process.extract(lower,self.choices,scorer=OSA.distance,
                                                     score_cutoff=2,limit=32):
                    if candidate!=lower and candidate[0]==lower[0] and self.compound(candidate):
                        additions.append(candidate)
            if len(lower)>=7:
                for i in range(5,len(lower)-1):
                    left,right=lower[:i],lower[i:]
                    if left.endswith('sjon') and self.noun(left) and self.noun(right):
                        additions.append(left+'s'+right)
            additions=sorted(set(additions),key=lambda w:(OSA.distance(lower,w),-self.freq.get(w,0),w))[:8]
            additions=[recase(w,word) for w in additions if single(w)]
            # Preserve 16 native slots and reserve up to eight for new evidence.
            choices=list(dict.fromkeys(info['suggestions'][:16]+additions+info['suggestions'][16:]))[:24]
            self.cache[word]=dict(info,suggestions=choices,raw_suggestions=info['raw_suggestions'], coverage_candidates=additions)
        return {w:self.cache[w] for w in words}
