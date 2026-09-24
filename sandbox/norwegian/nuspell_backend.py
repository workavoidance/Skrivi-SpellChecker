"""Optional Nuspell + cached NorBERT experiments. Never downloads on checking."""
import re
import subprocess
import time
from engine import GROUPS, Lexicon, Norbert, recase, single, words
from experimental_inference import fast_whole
from setup_assets import ROOT, DICT_REV
from setup_nuspell import RUNTIME

MODES = ('nuspell', 'nuspell_rank', 'nuspell_context', 'nuspell_confusions')

def parse_output(output, inputs):
    output = output.removeprefix('Enter some text: ')
    blocks = output.replace('\r\n', '\n').split('\n\n')
    while blocks and not blocks[-1].strip():
        blocks.pop()
    if len(blocks) != len(inputs):
        raise RuntimeError('Nuspell response could not be aligned safely with input words.')
    result = {}
    for word, block in zip(inputs, blocks):
        lines = block.strip().splitlines()
        if lines == ['* OK']:
            result[word] = dict(known=True, suggestions=[], raw_suggestions=[], segmented=False)
            continue
        prefix = '& Wrong: ' + word + '. How about: '
        if len(lines) == 1 and lines[0].startswith(prefix):
            raw = lines[0][len(prefix):].split(', ')
            choices = list(dict.fromkeys(w for w in raw if single(w) and w != word))
            result[word] = dict(known=False, suggestions=choices, raw_suggestions=raw, segmented=False)
        elif len(lines) == 1 and lines[0] == '# Wrong: ' + word + '. No suggestions.':
            result[word] = dict(known=False, suggestions=[], raw_suggestions=[], segmented=False)
        elif not lines or len(lines) != 1:
            # The CLI may split punctuation-containing words or skip numbers.
            # Never turn multiple fragment suggestions into a whole-word edit.
            result[word] = dict(known=word.isnumeric(), suggestions=[], raw_suggestions=[], segmented=True)
        else:
            raise RuntimeError('Unrecognised Nuspell output; no corrections applied.')
    return result

class NativeNuspell:
    def __init__(self):
        self.exe = RUNTIME / 'ucrt64/bin/nuspell.exe'
        self.dictionary = ROOT / 'models' / ('bokmal-lexicon-' + DICT_REV[:12]) / 'nb_NO.aff'
        if not self.exe.exists():
            raise RuntimeError('Run Setup-Nuspell.cmd once to enable this experiment.')
        self.cache = {}

    def lookup(self, input_words):
        for w in input_words:
            if single(w) and not w.isalpha() and not w.isnumeric():
                self.cache[w] = dict(known=False, suggestions=[], raw_suggestions=[], segmented=True)
        missing = list(dict.fromkeys(w for w in input_words if w not in self.cache and not w.isnumeric()))
        if any(not single(w) for w in missing):
            raise ValueError('Nuspell input must contain single words.')
        if missing:
            p = subprocess.run([str(self.exe), '-d', str(self.dictionary), '--encoding=UTF-8'],
                input='\n'.join(missing) + '\n', text=True, encoding='utf-8',
                capture_output=True, timeout=120,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if p.returncode:
                raise RuntimeError('Nuspell failed to load or check the local dictionary.')
            self.cache.update(parse_output(p.stdout, missing))
        return {w: self.cache[w] if not w.isnumeric() else
                dict(known=True, suggestions=[], raw_suggestions=[], segmented=False) for w in input_words}

class NuspellChecker:
    def __init__(self, model=None):
        self.native = NativeNuspell()
        self.model = model
        self.lexicon = None

    def check(self, text, mode):
        if mode not in MODES:
            raise ValueError('Unknown Nuspell mode')
        tokens = words(text)
        if not tokens or len(tokens) > 100 or len(text) > 4000:
            raise ValueError('Please enter 1–100 words, at most 4,000 characters.')
        started = time.perf_counter()
        load_seconds = 0
        if mode != 'nuspell' and self.model is None:
            self.model = Norbert()
            load_seconds = time.perf_counter() - started
        if mode != 'nuspell' and self.lexicon is None:
            self.lexicon = Lexicon(revised=True)
        native = self.native.lookup([t['word'] for t in tokens])
        output = []
        for token in tokens:
            word = token['word']; info = native[word]; known = info['known']
            candidates = info['suggestions'][:24]
            status = 'OK' if known else 'UNCERTAIN'
            suggestions = candidates[:3]
            reason = 'Godkjent av Nuspell; sammenhengen er ikke kontrollert.' if known else 'Nuspell kjenner ikke igjen skrivemåten. Vurder forslagene.'
            context_checked = False; scores = None
            if mode in ('nuspell_context', 'nuspell_confusions') and known:
                lower = word.casefold()
                candidates = [recase(w,word) for g in GROUPS if lower in g for w in g if w != lower]
                if mode == 'nuspell_context' and word.islower() and word.isalpha() and len(word) >= 3:
                    matches = self.lexicon.process.extract(word, self.lexicon.choices,
                        scorer=self.lexicon.distance, score_cutoff=1, limit=64)
                    doubled = [word[:p]+word[p]+word[p:] for p in range(len(word))]
                    candidates += [w for w in doubled if w in self.lexicon.vocab]
                    candidates += [w for w,_,_ in matches if w != word and w.isalpha()]
                candidates = list(dict.fromkeys(candidates))[:24]
            if mode != 'nuspell' and candidates and not info['segmented']:
                values,_ = fast_whole(self.model, text, token, [word] + candidates)
                if not known:
                    values = {w:s - 1.5*max(0,self.lexicon.distance(word.casefold(),w.casefold())-1)
                              for w,s in values.items()}
                scores = sorted(values.items(), key=lambda x:x[1], reverse=True)
                alternatives = [(w,s) for w,s in scores if w != word]
                context_checked = True
                if known:
                    suggestions = [w for w,s in alternatives if s-values[word] > 4.0][:3]
                    if suggestions:
                        status = 'UNCERTAIN'
                        reason = 'En lignende skrivemåte passer kanskje bedre i sammenhengen. Vurder selv.'
                    else:
                        reason = 'Ordet er beholdt etter sammenligning med alternative skrivemåter.'
                else:
                    suggestions = [w for w,_ in alternatives[:3]]
                    gap = alternatives[0][1] - values[word]
                    status = 'LIKELY_ERROR' if gap > 3 else 'UNCERTAIN'
                    reason = 'Nuspells forslag er sortert med den lokale norske kontekstmodellen.'
            if info['segmented']:
                reason = 'Denne skrivemåten må vurderes manuelt.'
            output.append({**token, 'status':status, 'suggestions':suggestions,
                'candidates':candidates, 'scores':scores, 'reason':reason,
                'native_known':known, 'native_suggestions':info['raw_suggestions'],
                'context_checked':context_checked,
                'start_utf16':len(text[:token['start']].encode('utf-16-le'))//2,
                'end_utf16':len(text[:token['end']].encode('utf-16-le'))//2})
        return dict(text=text, mode=mode, words=output, elapsed_seconds=time.perf_counter()-started,
                    load_seconds=load_seconds, coverage='Experimental Nuspell spelling and optional constrained NorBERT context; no rewriting or boundary edits.')
