"""Report exact source restoration separately from flags on untouched corpus text."""
import csv
import json
from pathlib import Path
from collections import Counter
from engine import words, replace_word

HERE=Path(__file__).parent
cases=json.loads((HERE/'sourced-cases.json').read_text(encoding='utf-8'))
by_id={c['id']:c for c in cases}
manifest=json.loads((HERE/'sourced-manifest.json').read_text())
source_texts={}
for block in (HERE/'corpus-source/no_bokmaal-ud-dev.conllu').read_text(encoding='utf-8').strip().split('\n\n'):
    fields=dict(line[2:].split(' = ',1) for line in block.splitlines() if line.startswith('# ') and ' = ' in line)
    if 'sent_id' in fields:source_texts[fields['sent_id']]=fields['text']
for c in cases:
    assert c['source']['original_text']==source_texts[c['source']['sent_id']]
    if c['errors']:
        m=c['mutation'];tokens=words(c['text'])
        assert tokens[m['token_id']]['word']==m['injected']
        assert replace_word(c['text'],tokens[m['token_id']],m['original'])==c['source']['original_text']
        a,b=words(c['source']['original_text']),tokens
        assert len(a)==len(b) and sum(x['word']!=y['word'] for x,y in zip(a,b))==1
    else:assert c['text']==c['source']['original_text']

with (HERE/'sourced-pairs.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['pair','source sentence ID','original','altered','original word','injected word','operation','source URL'])
    for c in cases:
        if c['errors']:
            m=c['mutation'];w.writerow([c['pair_id'],c['source']['sent_id'],c['source']['original_text'],c['text'],m['original'],m['injected'],m['operation'],c['source']['source_url']])

result=json.loads((HERE/'sourced-results.json').read_text(encoding='utf-8'))
assert len(result['runs'])==600 and len(result['summary'])==3, 'Wait for all three engines to finish.'
assert all(s['completed']==200 and s['failed']==0 for s in result['summary'].values()), 'Inspect incomplete checks before publishing.'
lines=['# Sourced Norwegian restoration test','',
'100 source sentences, each tested unchanged and with exactly one injected word error: 200 inputs per engine, 600 checks total. The original wording comes from UD Norwegian-Bokmaal, based on the Norwegian Dependency Treebank (NDT), rather than model-authored sentences. Source records have human morphosyntactic annotations; this is not certification that every spelling in the published texts is correct.', '',
'## Provenance and permitted reuse','',
f"Source revision: `{manifest['revision']}`. Source file: `no_bokmaal-ud-dev.conllu`. SHA-256: `{manifest['corpus_sha256']}`. Dataset seed: {manifest['seed']}. Downloaded 5 September 2026.", '',
'[Corpus and attribution](https://github.com/UniversalDependencies/UD_Norwegian-Bokmaal). NDT was developed at the National Library of Norway with the Text Laboratory and Department of Informatics at the University of Oslo. Original annotation credit includes Pål Kristian Eriksen, Kari Kinn and Per Erik Solberg; UD conversion contributors are credited in corpus-source/README.md. Source license is **CC BY-SA 4.0**; see corpus-source/LICENSE.txt and [license terms](https://creativecommons.org/licenses/by-sa/4.0/). The derived sentence pairs and their mutation records are also CC BY-SA 4.0. Changes consist solely of the documented injected spelling errors; no source endorsement is implied.', '',
'Every pair in sourced-pairs.csv and sourced-cases.json retains the unedited source sentence, corpus sentence ID, revision URL, original word, injected word, operation and exact position. Automated checks verified that all 100 originals match the downloaded source exactly, every altered copy changes only one word, and reversing that edit restores the source byte-for-byte when UTF-8 encoded.', '',
'## Selection and limitations','',
'Sentences have 7–25 words and final punctuation, are not marked Typo=Yes, and were selected with a fixed shuffled order without using checker results. There are 20 deletions, 20 duplicated letters, 20 adjacent transpositions and 20 letter substitutions in content words, plus 20 targeted contextual probes. Mechanical mutations already attested in this corpus were skipped; absence from this corpus does not prove a string is not a valid Norwegian word. No checker dictionary was used to select errors.', '',
'Context probes change eight infinitive-marker å occurrences to og (using source POS annotations), four vært to hvert, four gjerne to hjerne, and four verbal får to for. These are deliberately narrow and overlap the current candidate groups. Their results must not be interpreted as broad contextual detection accuracy. I reviewed the selected context sentences, but they have not had a new independent human review.', '',
'Exact-source restoration measures whether the original word is offered, not whether every different suggestion is linguistically wrong. Norwegian permits alternatives. The untouched corpus contains names, compounds, quotes and possibly pre-existing spelling issues. Accordingly, the table calls marks on originals **flags**, not verified false alarms. Språkrådet explains the limitation of single-answer benchmarks in its [2025 testing report, pages 3–4](https://sprakradet.no/wp-content/uploads/rapport_fra_sluttkorrektur_29.9.2025.pdf).', '',
'This controlled corruption set is more traceable than our earlier generated sentences, but it is not observed dyslexic writing, a language-authority-approved spelling benchmark, or proof that source text was absent from model pretraining. No engine settings were tuned against this set. Earlier reserved-regression.json remains untested.', '',
'## Results','',
'| Engine | Injected targets flagged /100 | Source word first /100 | Source word in top 3 /100 | Untouched sentences flagged /100 | Flags on untouched words |',
'|---|---:|---:|---:|---:|---:|']
summary={}
for mode in result['summary']:
    runs=[r for r in result['runs'] if r['mode']==mode and 'metrics' in r]
    originals=[r for r in runs if r['kind']=='clean'];changed=[r for r in runs if r['kind']!='clean']
    s={k:sum(r['metrics'][k] for r in changed) for k in ['detected','top1','top3','candidate_recall']}
    s['untouched_sentences_flagged']=sum(any(w['status']!='OK' for w in r['result']['words']) for r in originals)
    s['untouched_word_flags']=sum(w['status']!='OK' for r in originals for w in r['result']['words'])
    s['completed']=len(runs);s['failed']=result['summary'][mode]['failed']
    summary[mode]=s
    lines.append(f"| {mode} | {s['detected']} | {s['top1']} | {s['top3']} | {s['untouched_sentences_flagged']} | {s['untouched_word_flags']} |")
lines+=['','The generic raw evaluator calls non-target flags `false_alarms`; for this corpus they are unverified non-target flags, not adjudicated mistakes. Above we count only the 100 untouched originals for review burden, so the same sentence is not counted twice.', '',
'| Engine | Mutation | Targets | Flagged | Source first | Source in top 3 | Source in candidate pool |',
'|---|---|---:|---:|---:|---:|---:|']
for mode in result['summary']:
    for kind in ['delete_letter','duplicate_letter','transpose_letters','substitute_letter','context']:
        rows=[r for r in result['runs'] if r['mode']==mode and r.get('kind')==kind and 'metrics' in r]
        sums=[sum(r['metrics'][k] for r in rows) for k in ['errors','detected','top1','top3','candidate_recall']]
        lines.append('| '+mode+' | '+kind+' | '+' | '.join(map(str,sums))+' |')
lines+=['','## NorBERT inspection','', '| Source sentence ID | Injected → source | Suggestions | Source in candidates? |','|---|---|---|---|']
for r in result['runs']:
    if r['mode']!='norbert' or r.get('kind')=='clean' or 'metrics' not in r:continue
    c=by_id[r['case']];m=c['mutation'];w=r['result']['words'][m['token_id']]
    if m['original'] not in w['suggestions']:
        lines.append(f"| {c['source']['sent_id']} | {m['injected']} → {m['original']} | {', '.join(w['suggestions']) or '(none)'} | {m['original'] in w['candidates']} |")
flags=Counter(w['word'] for r in result['runs'] if r['mode']=='norbert' and r.get('kind')=='clean' for w in r['result']['words'] if w['status']!='OK')
lines+=['','Most frequent flags on unmodified source text: '+', '.join(f'{w} ({n})' for w,n in flags.most_common(15))+'.', '',
'## Reproduction','',
'Run build_sourced_cases.py against the preserved corpus-source files, then evaluate.py --cases sourced-cases.json --output sourced-results.json, then summarize_sourced.py, using the cached Python environment. No model downloads are needed. The evaluator records dataset/engine hashes, platform, timings and every token result. Each mode has its own candidate cache, but original and altered sentence pairs share that cache; timing is secondary here. No claim of verified overall Norwegian accuracy or superiority to Lingdys follows from this experiment.']
(HERE/'SOURCED-RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(HERE/'sourced-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
