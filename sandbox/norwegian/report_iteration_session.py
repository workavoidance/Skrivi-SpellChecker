"""Regenerate a local, auditable progress report from completed checkpoints."""
import json
from pathlib import Path
from evaluate import expected

HERE=Path(__file__).parent/'iteration-2026-09-05'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    lines=['# Norwegian sandbox: sequential experiments','',
           'Local experiment session, 5 September 2026. See PLAN.md for the frozen protocol and LOG.md for progress. Production defaults remain unchanged.','',
           'Scores measure intended token restoration against provisional labels. Unresolved words and unsupported boundary operations are excluded. False alarms are flags on other words, not independently adjudicated linguistic errors. Source controls can contain names or editorial inconsistencies.','']
    for suite in ['development','fresh']:
        paths=list(HERE.glob(suite+'-*.json'))
        paths=[p for p in paths if 'rows' in read(p)]
        if not paths:continue
        cases={c['id']:c for c in read(HERE/(suite+'.json'))}
        lines += ['## '+suite.title(),'',
         '| Variant | Cases | Target errors | Detected | First | Top 3 | Candidate recall | Other flags | Clean untouched | Total check seconds* |',
         '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for p in sorted(paths):
            data=read(p);s=data['summary']
            lines.append(f"| {data['stage']} | {s['cases']} | {s['errors']} | {s['detected']} | {s['top1']} | {s['top3']} | {s['candidate_recall']} | {s['false_alarms']} | {s['clean_unflagged']}/{s['clean_cases']} | {s['total_seconds']:.2f} |")
            if data['stage']=='baseline':
                rows=data['rows'];v={k:sum(r['v2_metrics'][k] for r in rows if 'v2_metrics' in r) for k in ['errors','detected','top1','top3','candidate_recall','false_alarms']}
                clean=[r for r in rows if r['kind']=='clean' and 'v2_metrics' in r]
                lines.append(f"| default-v2 | {len(rows)} | {v['errors']} | {v['detected']} | {v['top1']} | {v['top3']} | {v['candidate_recall']} | {v['false_alarms']} | {sum(r['v2_metrics']['false_alarms']==0 for r in clean)}/{len(clean)} | {sum(r.get('v2_seconds',0) for r in rows):.2f} |")
        lines += ['', '*Exploratory accumulated check time excluding model startup. Context-only variants reuse saved v2 output and include the baseline v2 time; broader cleanup also includes its initial whole-word pass. These are not standalone end-to-end latency measurements. Baseline was resumed after a transient Windows checkpoint lock. Use the separate repeated timing study, if present, for speed claims.','']
        if suite=='development':
            lines += ['## User-supplied paragraph (local only)','',
                      '16 scored target occurrences. `am` and the proper name remain unresolved. `idag`, `imårn`, `bret spill` require boundary edits; `tiande` is a language-variety issue. These are recorded but not counted as token errors or false flags. Grammar and punctuation are preserved.','',
                      '| Variant | Detected /16 | First /16 | Top 3 /16 | Other flags | Seconds* |','|---|---:|---:|---:|---:|---:|']
            for p in sorted(paths):
                data=read(p);r=next((r for r in data['rows'] if r['id']=='natural-paragraph01'),None)
                if not r or 'metrics' not in r:continue
                m=r['metrics'];lines.append(f"| {data['stage']} | {m['detected']} | {m['top1']} | {m['top3']} | {m['false_alarms']} | {r['seconds']:.2f} |")
            lines+=['','### Changes from whole-word baseline','']
        baseline=HERE/(suite+'-baseline.json')
        if baseline.exists():
            base={r['id']:r for r in read(baseline)['rows']}
            for p in sorted(paths):
                data=read(p)
                if data['stage']=='baseline':continue
                lines+=['#### '+suite+'/'+data['stage'],'']
                changes=0;maxdiff=0
                for r in data['rows']:
                    if 'result' not in r or r['id'] not in base:continue
                    b=base[r['id']];old={w['id']:w for w in b['result']['words']}
                    for w in r['result']['words']:
                        prev=old[w['id']]
                        if w['status']!=prev['status'] or w['suggestions']!=prev['suggestions']:
                            changes+=1
                            lines.append(f"- {r['id']} token {w['id']} **{w['word']}**: {prev['status']} {prev['suggestions']} → {w['status']} {w['suggestions']}")
                        ps=dict(prev.get('scores') or [])
                        for c,v in w.get('scores') or []:
                            if c in ps:maxdiff=max(maxdiff,abs(v-ps[c]))
                lines+=['',f'{changes} token decisions/suggestion lists changed; maximum comparable raw score difference {maxdiff:.8g}.','']
    (HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Updated',HERE/'RESULTS.md')
if __name__=='__main__':main()
