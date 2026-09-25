"""POC: evaluate cached predictions, preserving all writing/results locally."""
import collections
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sandbox/norwegian'))
from dictionary_help import DictionaryHelp,cache_path
from compound_help import CompoundHelp,build_base_index
from setup_assets import ROOT


def main():
    root=Path(__file__).resolve().parents[1]
    folder=ROOT/'lexical/ordbank-20220201'
    base=folder/'help-baseforms.sqlite3'
    if not base.exists():
        print(json.dumps(build_base_index(folder/'20220201_norsk_ordbank_nob_2005.tar.gz',base)),flush=True)
    helper=CompoundHelp(DictionaryHelp(),base,folder/'ordbank.sqlite3')
    counts=collections.Counter();ranks=collections.defaultdict(collections.Counter);times=[];cache={};sources={};broad=collections.Counter()
    for path in sorted((root/'results/baseline-20260924').glob('*-nuspell_context.json')):
        sources[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        for row in json.loads(path.read_text(encoding='utf-8')):
            for word in row['result']['words']:
                for rank,s in enumerate(word.get('suggestions',[]),1):
                    if s not in cache:
                        start=time.perf_counter();cache[s]=helper.lookup(s);times.append(time.perf_counter()-start)
                    kind=cache[s]['kind'] if cache[s] else 'missing'
                    permissive=cache[s] or helper.lookup(s,noun_only=False)
                    broad[permissive['kind'] if permissive else 'missing']+=1
                    counts[kind]+=1;ranks[rank][kind]+=1
    private=root/'results/compound-help-20260925';private.mkdir(exist_ok=True)
    (private/'lookups.json').write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'unrestricted_recorded_parts_counts':dict(broad),'counts':dict(counts),'by_rank':dict(ranks),'unique_words':len(cache),
            'unique_counts':dict(collections.Counter(x['kind'] if x else 'missing' for x in cache.values())),
            'median_unique_lookup_ms':statistics.median(times)*1000,
            'p95_unique_lookup_ms':sorted(times)[int(.95*(len(times)-1))]*1000,
            'extra_cache_bytes':base.stat().st_size,'inputs':sources,
            'limitations':['Saved baseline suggestion occurrences, not intended-answer coverage or human-rated usefulness.',
                          'Component help is not a whole-word definition. No guessed decompositions or generated explanations.',
                          'Current dictionary already maps its own inflections; only additional Ordbank base links can add coverage.',
                          'No spelling/ranking, default application or UI changes.']}
    (root/'docs/benchmarks/2026-09-25-compound-help.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
