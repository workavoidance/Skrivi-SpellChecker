"""Score local per-target traces. This does not run a spell checker.

Usage: python candidate_audit.py traces.jsonl report.json
An adapter must capture generated candidates BEFORE context ranking/pruning.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import unicodedata


def norm(text):
    return unicodedata.normalize('NFC', text)


def strings(row, field):
    values = row.get(field)
    if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
        raise ValueError(f'{field} must be a list of nonempty strings')
    values = [norm(x) for x in values]
    if len(set(values)) != len(values):
        raise ValueError(f'{field} contains duplicates')
    return values


def classify(row):
    if not isinstance(row.get('id'), str) or not row['id']:
        raise ValueError('id must be a nonempty string')
    if type(row.get('is_error')) is not bool or type(row.get('flagged')) is not bool:
        raise ValueError('is_error and flagged must be explicit booleans')
    accepted = set(strings(row, 'acceptable'))
    if not accepted:
        raise ValueError('acceptable must contain at least one reviewed answer')
    generated = strings(row, 'generated')
    ranked = strings(row, 'ranked')
    displayed = strings(row, 'displayed')
    if not set(ranked) <= set(generated):
        raise ValueError('ranked contains candidates absent from generated; capture all sources')
    if not set(displayed) <= set(ranked):
        raise ValueError('displayed contains candidates absent from ranked')
    if len(displayed) > 3:
        raise ValueError('this experiment measures a three-choice UI')
    if not row['flagged'] and displayed:
        raise ValueError('unflagged targets must not have displayed suggestions')
    rank = next((i for i, x in enumerate(ranked, 1) if x in accepted), None)
    available = bool(accepted.intersection(generated))
    shown = bool(accepted.intersection(displayed))
    if not row['is_error']:
        outcome = 'false_alarm' if row['flagged'] else 'correctly_kept'
    elif shown:
        outcome = 'success'
    elif not available:
        outcome = 'candidate_missing'
    elif rank is None or rank > 3:
        outcome = 'ranking_or_pruning_failure'
    else:
        outcome = 'detection_or_display_failure'
    return {'id': row['id'], 'is_error': row['is_error'], 'flagged': row['flagged'],
            'available': available, 'rank': rank, 'shown': shown, 'outcome': outcome,
            'generated_count': len(generated),
            'group': row.get('writer_group', 'unspecified'),
            'error_type': row.get('error_type', 'unspecified')}


def summarize(rows):
    errors = [x for x in rows if x['is_error']]
    clean = [x for x in rows if not x['is_error']]
    available = [x for x in errors if x['available']]
    tp = sum(x['flagged'] for x in errors)
    fp = sum(x['flagged'] for x in clean)
    def rate(n, d):
        return {'numerator': n, 'denominator': d, 'rate': n / d if d else None}
    return {
        'targets': len(rows), 'errors': len(errors), 'clean_targets': len(clean),
        'outcomes': dict(Counter(x['outcome'] for x in rows)),
        'detection_recall': rate(tp, len(errors)),
        'detection_precision': rate(tp, tp + fp),
        'false_alarm_rate': rate(fp, len(clean)),
        'candidate_recall': rate(len(available), len(errors)),
        'conditional_top3': rate(sum(x['rank'] is not None and x['rank'] <= 3 for x in available), len(available)),
        'conditional_top5': rate(sum(x['rank'] is not None and x['rank'] <= 5 for x in available), len(available)),
        'end_to_end_displayed_top3': rate(sum(x['shown'] for x in errors), len(errors)),
    }


def audit(records):
    rows = [classify(x) for x in records]
    if not rows:
        raise ValueError('no traces; a missing baseline is not a zero-score run')
    if len({x['id'] for x in rows}) != len(rows):
        raise ValueError('duplicate target id')
    grouped = defaultdict(list)
    for x in rows:
        grouped[x['group']].append(x)
    return {'overall': summarize(rows),
            'by_writer_group': {k: summarize(v) for k, v in grouped.items()},
            'targets': rows,
            'scope': 'Per-target audit only. Full-text false-alarm measurement requires traces for every token, including correct tokens. Input completeness must be checked against the frozen benchmark by the adapter.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('traces', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    records = [json.loads(x) for x in args.traces.read_text(encoding='utf-8').splitlines() if x.strip()]
    result = audit(records)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result['overall'], indent=2))
