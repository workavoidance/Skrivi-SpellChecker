"""Aggregate private audit traces without exporting text or candidate words."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from audit_recovered_baseline import SUITES, MODES


def visible_top5(token, answers):
    """Counterfactual only: retain current known-word gap >4 and detection."""
    if token['status']=='OK':
        return False
    ranked = [x[0] for x in token.get('scores') or [] if x[0] != token['word']]
    if token.get('scores') and token.get('native_known'):
        values = dict(token['scores'])
        ranked = [w for w in ranked if values[w] - values[token['word']] > 4.0]
    elif not token.get('scores'):
        ranked = token['candidates']
    return bool(set(ranked[:5]) & set(answers))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('results',type=Path)
    args=p.parse_args()
    report={}
    for suite in SUITES:
        modes={mode:json.loads((args.results/f'{suite}-{mode}.json').read_text(encoding='utf-8')) for mode in MODES}
        groups={}
        for mode,rows in modes.items():
            by_kind={};known=Counter();unknown=Counter();clean=Counter();failure=Counter();top5=Counter()
            for row in rows:
                if 'failure' in row:continue
                by_kind.setdefault(row['kind'],Counter()).update(row['metrics'])
                if row['kind']=='clean':
                    clean.update(cases=1,tokens=len(row['result']['words']),flags=row['metrics'].get('non_target_flags',0),
                                 cases_flagged=bool(row['metrics'].get('non_target_flags',0)))
                words={w['id']:w for w in row['result']['words']}
                for detail in row['details']:
                    token=words[detail['token_id']]
                    visible = visible_top5(token, detail['answers'])
                    top5['same_policy_top5'] += visible
                    if row['case']=='natural-paragraph01':top5['natural_paragraph_same_policy_top5'] += visible
                    bucket=known if token.get('native_known') else unknown
                    bucket['errors']+=1;bucket['detected']+=detail['flagged'];bucket['top3']+=detail['bucket']=='success'
                    bucket['candidate_hit']+=detail['in_candidate_pool']
                    failure[detail['bucket']]+=1
                    if not detail['in_candidate_pool'] and set(detail['answers']) & set(token.get('native_suggestions',[])):
                        failure['native_present_but_missing_from_final_pool']+=1
            groups[mode]={'kind':by_kind,'dictionary_recognised_errors':dict(known),'dictionary_unknown_errors':dict(unknown),
                          'clean':dict(clean),'failure_partition':dict(failure),'top5_counterfactual':dict(top5)}
        comparisons={}
        for before,after in [('nuspell','nuspell_rank'),('nuspell_rank','nuspell_context')]:
            a={(r['case'],d['token_id']):d['bucket']=='success' for r in modes[before] if 'details' in r for d in r['details']}
            b={(r['case'],d['token_id']):d['bucket']=='success' for r in modes[after] if 'details' in r for d in r['details']}
            shared=a.keys()&b.keys()
            comparisons[before+' -> '+after]={'targets_compared':len(shared),'gained_top3':sum(not a[k] and b[k] for k in shared),
                                            'lost_top3':sum(a[k] and not b[k] for k in shared)}
        report[suite]={'modes':groups,'comparisons':comparisons}
    (args.results/'breakdown.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
