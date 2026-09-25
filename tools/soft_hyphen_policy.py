"""Softer candidate policy. Supported choices first; no eligible candidate deleted."""
from hyphen_policy import HyphenPolicy

class SoftHyphenPolicy(HyphenPolicy):
    def __init__(self, listed, known, properties):
        super().__init__(listed,known)
        self.properties=properties

    def extended_evidence(self, original, candidate):
        evidence=self.evidence(original,candidate)
        if evidence:return evidence
        parts=candidate.split('-')
        if len(parts)!=2:return None
        left,right=parts
        lp=self.properties(left.casefold()) or {}
        rp=self.properties(right.casefold()) or {}
        if lp.get('proper') and left[:1].isupper() and self.known(right.casefold()):
            return 'recorded_name_plus_word'
        if lp.get('adjective',False) and rp.get('adjective',False):
            return 'recorded_adjective_pair'
        display=lp.get('display','')
        if len(display)>1 and display.isupper() and display.isalpha() and self.known(right.casefold()):
            return 'recorded_abbreviation_plus_word'
        return None

    def partition(self, token, extended=True):
        if token['status']=='OK' or not token.get('scores') or 'native_known' not in token:
            return {'shown':list(token['suggestions']),'more':[], 'uncertain':[]}
        # Do not disturb original hyphenated text or boundary-repair paths.
        if '-' in token['word']:
            return {'shown':list(token['suggestions']),'more':[], 'uncertain':[]}
        values=dict(token['scores'])
        choices=[w for w,_ in token['scores'] if w!=token['word']]
        if token['native_known']:
            choices=[w for w in choices if values[w]-values[token['word']]>4.0]
        choices=list(dict.fromkeys(choices))
        supported=[];uncertain=[]
        evidence=self.extended_evidence if extended else self.evidence
        for word in choices:
            (supported if evidence(token['word'],word) else uncertain).append(word)
        ordered=supported+uncertain
        assert len(ordered)==len(choices) and set(ordered)==set(choices)
        return {'shown':ordered[:3],'more':ordered[3:],'uncertain':uncertain}

    def apply(self, token, variant='soft_extended'):
        return self.partition(token,extended=variant=='soft_extended')['shown']
