"""Offline, checkpointed audit of the recovered UI modes. Raw output is private."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'sandbox/norwegian'
MODES = ('nuspell', 'nuspell_rank', 'nuspell_context')
SUITES = {'development': 'iteration-2026-09-05/development.json',
          'previously_fresh': 'iteration-2026-09-05/fresh.json',
          'source_restoration': 'sourced-cases.json'}


def gold_map(case, tokens, key='errors'):
    result = {}
    for entry in case.get(key, []):
        matches = [t for t in tokens if t['word'] == entry['word']]
        token = matches[entry.get('occurrence', 0)]
        if token['id'] in result:
            raise ValueError('Duplicate gold token')
        result[token['id']] = entry.get('suggestions', [])
    return result


def diagnose(case, result):
    """Exact source/key restoration; case variants are not silently accepted."""
    tokens = result['words']
    gold = gold_map(case, tokens)
    ignored = gold_map(case, tokens, 'unscored')
    if set(gold) & set(ignored):
        raise ValueError('Scored and unscored targets overlap')
    counts = Counter(errors=len(gold), tokens=len(tokens), ignored=len(ignored))
    details = []
    for token in tokens:
        i = token['id']
        if i in ignored:
            continue
        flagged = token['status'] != 'OK'
        if i not in gold:
            counts['non_target_tokens'] += 1
            counts['non_target_flags'] += flagged
            continue
        answers = set(gold[i])
        suggestions = token['suggestions']
        candidates = token['candidates']
        pool = bool(answers.intersection(candidates))
        hit = flagged and bool(answers.intersection(suggestions[:3]))
        counts['detected'] += flagged
        counts['native_candidate_hit'] += bool(answers.intersection(token.get('native_suggestions', [])))
        counts['candidate_hit'] += pool
        counts['top1'] += flagged and bool(suggestions) and suggestions[0] in answers
        counts['top3'] += hit
        ranked = [x[0] for x in token.get('scores') or [] if x[0] != token['word']]
        if not token.get('scores'):
            ranked = candidates
        counts['ranked_top5_potential'] += bool(answers.intersection(ranked[:5]))
        # These independent misses overlap: failure to flag and failure to
        # generate can happen on the same token.
        counts['detection_misses'] += not flagged
        counts['candidate_misses'] += not pool
        counts['pool_present_not_shown'] += pool and not hit
        bucket = ('success' if hit else 'not_flagged' if not flagged else
                  'candidate_missing' if not pool else 'ranking_or_threshold')
        counts['partition_' + bucket] += 1
        details.append({'token_id': i, 'word': token['word'], 'answers': sorted(answers),
                        'bucket': bucket, 'flagged': flagged, 'in_candidate_pool': pool,
                        'suggestions': suggestions})
    return dict(counts), details


def curated_forms():
    # Read the actual UI's tables, not the historical hard-coded coverage list.
    result = set()
    for name in ['responsive.html', 'poc.js']:
        text = (ENGINE / name).read_text(encoding='utf-8')
        for forms in re.findall(r'forms:\s*\[([^\]]+)\]', text):
            result.update(x.casefold() for x in re.findall(r"'([^']+)'", forms))
    if not result:
        raise ValueError('No UI help forms found')
    return result


def help_metrics(result, curated, lexical):
    displayed = [w for w in result['words'] if w['status'] != 'OK']
    request = [s for w in displayed for s in [w['word'], *w['suggestions']]]
    # Match the UI endpoint's per-request 60-word cap.
    entries = lexical.lookup_many(request) if lexical.available else {}
    out = Counter()
    for token in displayed:
        for suggestion in token['suggestions']:
            out['suggestion_occurrences'] += 1
            defined = suggestion.casefold() in curated
            entry = entries.get(suggestion)
            hint = bool(entry and any(s.get('synonyms') or s.get('broader')
                                     for s in entry.get('senses', [])))
            out['curated_definition_and_example'] += defined
            out['curated_or_optional_wordnet_hint'] += defined or hint
    return dict(out)


def checkpoint(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'results'):
        p.error('Raw writing must remain under the ignored results directory')
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ENGINE))
    from engine import Checker, words
    from setup_assets import ROOT as CACHE, REV, DICT_REV
    from wordnet_help import WordnetHelp
    curated = curated_forms()
    lexical = WordnetHelp(CACHE/'lexical/norsk-ordvev-1.1.2/wordnet-help.sqlite3')
    suites = {name: json.loads((args.data / filename).read_text(encoding='utf-8'))
              for name, filename in SUITES.items()}
    # Label/token alignment and app length limit checked before expensive work.
    for cases in suites.values():
        for case in cases:
            tokens = words(case['text'])
            gold_map(case, tokens)
            gold_map(case, tokens, 'unscored')
            if not 1 <= len(tokens) <= 100 or len(case['text']) > 4000:
                raise ValueError('Case exceeds application limits: ' + case['id'])
    hashes = {name: hashlib.sha256((args.data/file).read_bytes()).hexdigest()
              for name, file in SUITES.items()}
    meta = {'started_utc': datetime.now(timezone.utc).isoformat(), 'suite_sha256': hashes,
            'source_sha256': {str(x.relative_to(ROOT)): hashlib.sha256(x.read_bytes()).hexdigest()
                              for x in [*ENGINE.glob('*.py'), ENGINE/'responsive.html', ENGINE/'poc.js', ENGINE/'wordnet.js']},
            'model_revision': REV, 'dictionary_revision': DICT_REV,
            'personal_dictionary': 'Bypassed for reproducible baseline; user data unchanged.',
            'wordnet_available': lexical.available, 'curated_forms': len(curated),
            'timing': 'Single pass, CPU, new Checker per mode; session caches persist across suites. Lazy model load recorded separately. No timing repetitions.',
            'limitations': 'Previously inspected exploratory labels, not an independent or clinically representative benchmark. Exact key/source restoration. Non-target flags are not adjudicated false positives. WordNet hints are not definitions or verified useful explanations. Top-five is hypothetical ranked-pool coverage, not a tested UI change.',
            'cross_suite_duplicate_texts': {a+' / '+b: len({c['text'] for c in suites[a]} & {c['text'] for c in suites[b]})
                                           for i,a in enumerate(suites) for b in list(suites)[i+1:]}}
    checkpoint(output/'metadata.json', meta)
    summary = {}
    for mode in MODES:
        checker = Checker()
        for suite, cases in suites.items():
            rows=[]
            for n, case in enumerate(cases):
                try:
                    result = checker.check(case['text'], mode)
                    metrics, details = diagnose(case, result)
                    help_counts = help_metrics(result, curated, lexical)
                    row = {'case': case['id'], 'kind': case['kind'], 'result': result,
                           'metrics': metrics, 'details': details, 'help': help_counts}
                except Exception as exc:
                    row = {'case': case['id'], 'failure': str(exc)}
                rows.append(row)
                checkpoint(output/f'{suite}-{mode}.json', rows)
                if n % 20 == 0 or n+1 == len(cases):
                    print(mode, suite, n+1, '/', len(cases), 'failures', sum('failure' in x for x in rows), flush=True)
            valid = [r for r in rows if 'metrics' in r]
            totals=Counter(); help_totals=Counter()
            for r in valid:
                totals.update(r['metrics']); help_totals.update(r['help'])
            group = {'cases': len(cases), 'completed': len(valid), 'failed': len(rows)-len(valid),
                     'metrics': dict(totals), 'help': dict(help_totals),
                     'clean_cases': sum(r['kind']=='clean' for r in valid),
                     'clean_cases_unflagged': sum(r['kind']=='clean' and not r['metrics'].get('non_target_flags',0) for r in valid),
                     'median_check_seconds': statistics.median(r['result']['elapsed_seconds']-r['result']['load_seconds'] for r in valid) if valid else None,
                     'load_seconds': sum(r['result']['load_seconds'] for r in valid)}
            natural = [r for r in valid if r['case']=='natural-paragraph01']
            if natural:
                group['natural_paragraph'] = {k: natural[0][k] for k in ['metrics','help']}
            summary[suite+' / '+mode] = group
            checkpoint(output/'summary.json', summary)
    meta['finished_utc']=datetime.now(timezone.utc).isoformat()
    checkpoint(output/'metadata.json',meta)
    print('COMPLETE', output, flush=True)


if __name__ == '__main__':
    main()
