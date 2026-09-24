import json
from pathlib import Path
from evaluate import expected

HERE=Path(__file__).parent
report=json.loads((HERE/'extended-results.json').read_text(encoding='utf-8'))
cases={c['id']:c for c in json.loads((HERE/'extended-development.json').read_text(encoding='utf-8'))}
lines=['# Expanded Norwegian test — 5 September 2026','',
'63 synthetic sentences, 36 intended single-word errors and 27 clean controls. All three engines use the unchanged candidate generator and thresholds. These examples were written for this experiment; they are not a corpus of dyslexic writing or an independently reviewed benchmark. Some spellings overlap earlier examples, while contexts and coverage are expanded.', '',
'| Engine | Flagged /36 | Intended first /36 | Intended in top 3 /36 | False alarms | Clean sentences untouched /27 | Median check, seconds |',
'|---|---:|---:|---:|---:|---:|---:|']
for mode,s in report['summary'].items():
    lines.append(f"| {mode} | {s['detected']} | {s['top1']} | {s['top3']} | {s['false_alarms']} | {s['clean_cases_unflagged']} | {s['median_check_seconds']:.3f} |")
lines+=['','## Breakdown','', '| Engine | Category | Errors | Flagged | Top 1 | Top 3 | False alarms |','|---|---|---:|---:|---:|---:|---:|']
for mode in report['summary']:
    for kind in ['spelling','sound_based','context','clean']:
        rows=[r for r in report['runs'] if r['mode']==mode and r.get('kind')==kind and 'metrics' in r]
        t={k:sum(r['metrics'][k] for r in rows) for k in ['errors','detected','top1','top3','false_alarms']}
        lines.append(f"| {mode} | {kind} | {t['errors']} | {t['detected']} | {t['top1']} | {t['top3']} | {t['false_alarms']} |")
lines+=['','## NorBERT failure inspection','', '| Text | Target → intended | Observed |','|---|---|---|']
for r in report['runs']:
    if r['mode']!='norbert' or 'metrics' not in r: continue
    gold=expected(cases[r['case']])
    for w in r['result']['words']:
        if w['id'] in gold and not set(w['suggestions']) & set(gold[w['id']]):
            why=('Not flagged' if w['status']=='OK' else 'Suggestions: '+', '.join(w['suggestions']))
            if not set(w['candidates']) & set(gold[w['id']]): why+='; intended word absent from candidates'
            lines.append(f"| {r['result']['text']} | {w['word']} → {', '.join(gold[w['id']])} | {why} |")
        elif w['id'] not in gold and w['status']!='OK':
            lines.append(f"| {r['result']['text']} | {w['word']} (keep) | False alarm: {', '.join(w['suggestions'])} |")
lines+=['','## Interpretation and next experiment','',
'The candidate stage supplies the intended answer for 31 of 36 errors. Five errors are therefore impossible for either model to correct with the current choices. These include the unlisted viste/visste confusion, skule/skulle, borde/bordet and the severe synthetic jæmelighet/hemmelighet misspelling.', '',
'Candidate availability does not guarantee useful ranking. NorBERT fails on avtallen/avtalen, stasjonn/stasjonen and sjikkelig/skikkelig even though the intended answer is available. Its masked-subtoken score can prefer the wrong word. The Gjem/Hjem false alarm shows that adding more confusion pairs without checking correct uses can make the tool worse. The shared sikkerhets false alarm is a word-list/phrase coverage problem.', '',
'Recommended next experiment: extend candidate coverage in a controlled variant, include both correct and incorrect uses of every confusion pair, and evaluate more conservative ranking/abstention. Keep the current results as the baseline. No engine changes were made during this test.', '',
'24 additional sentences (12 intended errors and 12 clean controls) are saved in reserved-regression.json and have NOT been run. They are reserved for checking the next change. They share error families with development, so they test regression/generalisation to new sentences, not a fully independent linguistic benchmark. Once used for tuning, they must no longer be described as unseen.', '',
'## Timing and reproduction','',
'Each engine started with a fresh Checker and candidate cache. Checks ran sequentially on the same Windows machine, using cached CPU models. Timings exclude model loading, and recognised words outside confusion groups often receive no model work. These short-sentence medians are not latency estimates for 100-word paragraphs. No speed repeats were run because this experiment changes neither engine nor runtime.', '',
'Run with the cached Python environment: `python evaluate.py --cases extended-development.json --output extended-results.json`, then `python summarize_extended.py`. Raw results record dataset and engine SHA-256 hashes, Python/platform details, per-word candidates and scores, per-case latency and failures. Earlier results.json is preserved.', '',
'Correctness control: tunell is intentionally treated as correct, alongside other legitimate Bokmål variants. [Bokmålsordboka lists both tunnel and tunell](https://ordbokene.no/bm/TUNELL). Names are treated as intended names; labels still need native-speaker review before external accuracy claims. Split/join errors are outside this single-word benchmark. No Lingdys results are included.']
(HERE/'EXTENDED-RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(report['summary'],indent=2))
