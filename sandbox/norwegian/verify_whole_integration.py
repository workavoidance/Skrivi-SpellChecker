"""Verify production mode matches the frozen offline whole-mask policy."""
import json
from pathlib import Path
from engine import Checker
from context_experiments import proposal
HERE=Path(__file__).parent
rows=json.loads((HERE/'scoring-development-cache.json').read_text(encoding='utf-8'))['rows']
checker=Checker();results=[]
for row in rows:
    expected=json.loads(json.dumps(row['baseline']))
    for c in row['comparisons']:
        suggestions=proposal(c,'whole_mask')
        if suggestions:
            next(w for w in expected['words'] if w['id']==c['id']).update(status='UNCERTAIN',suggestions=suggestions)
    actual=checker.check(row['case']['text'],'norbert_v4')
    signature=lambda r:[(w['id'],w['word'],w['status'],w['suggestions']) for w in r['words']]
    assert signature(actual)==signature(expected),row['case']['id']
    results.append(dict(id=row['case']['id'],result=actual))
    print(row['case']['id'],'matches frozen policy',flush=True)
(HERE/'whole-integration-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('All',len(rows),'production results match the offline policy.')
