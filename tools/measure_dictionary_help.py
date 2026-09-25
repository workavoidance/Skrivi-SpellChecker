"""Measure offline word-help coverage on saved baseline predictions; no inference."""
import collections
import json
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sandbox/norwegian'))
from dictionary_help import DictionaryHelp,cache_path

def main():
    root=Path(__file__).resolve().parents[1]
    help=DictionaryHelp();counts=collections.Counter();times=[];words=set()
    for path in sorted((root/'results/baseline-20260924').glob('*-nuspell_context.json')):
        for row in json.loads(path.read_text(encoding='utf-8')):
            for word in row['result']['words']:
                for suggestion in word.get('suggestions',[]):
                    counts['suggestion_occurrences']+=1;words.add(suggestion)
                    start=time.perf_counter();entry=help.lookup(suggestion);times.append(time.perf_counter()-start)
                    if entry:
                        counts['with_definition']+=1
                        counts['with_example']+=any(s['examples'] for s in entry['senses'])
    report={'counts':dict(counts),'unique_suggestions':len(words),
            'median_lookup_ms':statistics.median(times)*1000,'database_bytes':cache_path().stat().st_size,
            'limitation':'Reused baseline suggestion occurrences, not unique words or human-rated usefulness. No new spelling inference. Examples include phrases. No automatic context-based sense selection.'}
    out=root/'docs/benchmarks/2026-09-25-dictionary-help.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
