"""Experimental separator policy, replayed on saved scores; not an app default."""
import re

class HyphenPolicy:
    def __init__(self, listed, known):
        self.listed=listed
        self.known=known

    def evidence(self, original, candidate):
        if '-' not in candidate:return 'no_hyphen'
        if '-' in original:return 'original_already_hyphenated'
        if self.listed(candidate.casefold()):return 'explicit_form'
        parts=candidate.split('-')
        if len(parts)==2:
            left,right=parts
            if (len(left)==1 and left.isalpha() or left.isdigit() or re.fullmatch(r'[A-ZÆØÅ]{2,6}',left)) and self.known(right.casefold()):
                return 'letter_number_or_uppercase_abbreviation'
        return None

    def apply(self, token, variant='guard'):
        if token['status']=='OK' or not token.get('scores'):return list(token['suggestions'])
        # No change to split/join or other special paths in this replay.
        if 'native_known' not in token:return list(token['suggestions'])
        original=token['word'];values=dict(token['scores'])
        choices=[w for w,s in token['scores'] if w!=original]
        if token['native_known']:
            choices=[w for w in choices if values[w]-values[original]>4.0]
        choices=[w for w in choices if self.evidence(original,w)]
        if variant=='guard_native_tiebreak':
            # Fixed small native-order contribution; an experiment, not confidence.
            native=token.get('native_suggestions',[])
            choices.sort(key=lambda w:values[w]-0.15*(native.index(w) if w in native else 24),reverse=True)
        if variant=='guard_gap' and choices:
            best=values[choices[0]]
            choices=[w for w in choices if values[w]>=best-2.0]
        return choices[:3]
