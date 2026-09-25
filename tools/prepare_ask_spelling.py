"""Prepare private ASK spelling-review candidates; never print source text.

No automatic label is a reviewed answer key. A separate local review file is
required to finalize a sample. Downloads are deliberately outside this tool.
"""
import argparse
from collections import Counter
import difflib
import hashlib
import json
from pathlib import Path
import random
import re

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'\w+|[^\w\s]')


def isolated_edit(row):
    source, correction = row['source'], row['correction']
    matches = list(TOKEN.finditer(source))
    a = [m.group() for m in matches]
    b = TOKEN.findall(correction)
    edits = [o for o in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
             if o[0] != 'equal']
    if len(edits) != 1:
        return None
    op, lo, hi, start, end = edits[0]
    if op != 'replace' or hi-lo != 1 or end-start != 1:
        return None
    original, answer = a[lo], b[start]
    if (not original.isalpha() or not answer.isalpha()
            or original.casefold() == answer.casefold()
            or min(len(original), len(answer)) < 3
            or not 5 <= len(a) <= 35
            or difflib.SequenceMatcher(None, original.casefold(), answer.casefold()).ratio() < .60):
        return None
    left, right = matches[lo].span()
    if source[:left] + answer + source[right:] != correction:
        return None
    return dict(original=original, corrected=answer, start=left, end=right,
                source=source, correction=correction)


def edit_category(original, corrected):
    # Mechanical taxonomy, not a claim about the writer's cognitive process.
    a, b = original.casefold(), corrected.casefold()
    edits = [o for o in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
             if o[0] != 'equal']
    if len(a) == len(b):
        for i in range(len(a)-1):
            if a[:i]+a[i+1]+a[i]+a[i+2:] == b:
                return 'adjacent_transposition'
    if len(edits) == 1:
        op, lo, hi, start, end = edits[0]
        if op == 'insert':
            return 'omitted_letters'
        if op == 'delete':
            return 'extra_letters'
        if op == 'replace':
            return 'substitution'
    return 'multiple_edits'


def build_candidates(rows, seed=20260924):
    result, seen = [], set()
    for index, row in enumerate(rows):
        item = isolated_edit(row)
        if item:
            key = (item['original'].casefold(), item['corrected'].casefold())
            if key in seen:
                continue
            seen.add(key)
            item.update(source_row=index, category=edit_category(*key))
            result.append(item)
    random.Random(seed).shuffle(result)
    return result


def finalize(candidates, reviews, reserve=20):
    """Use explicit accepted indices only; reserve before any model prediction."""
    accepted = []
    seen = set()
    for review in reviews:
        i = review['candidate_index']
        if i in seen or not 0 <= i < len(candidates):
            raise ValueError('Duplicate or invalid review index')
        seen.add(i)
        if review['decision'] != 'accept':
            continue
        if not review.get('reason'):
            raise ValueError('Accepted edit requires a review reason')
        item = dict(candidates[i], review=review)
        accepted.append(item)
    if len(accepted) <= reserve:
        raise ValueError('Not enough reviewed pairs for requested reserve')
    random.Random(24092026).shuffle(accepted)
    cases = []
    for n, item in enumerate(accepted):
        group = 'reserved' if n < reserve else 'evaluation'
        for corrected in (False, True):
            source = item['correction'] if corrected else item['source']
            word = item['corrected'] if corrected else item['original']
            cases.append(dict(id=f"ask-train-{item['source_row']}-{'control' if corrected else 'error'}",
                pair_id=f"ask-train-{item['source_row']}", partition=group,
                text=source, target_start=item['start'], target_end=item['start']+len(word),
                target_word=word, acceptable=[item['corrected']],
                kind='target_control' if corrected else 'spelling_error', category=item['category'],
                source_record_id=item['source_row'], source='ltg/ask-gec train',
                writer_group='norwegian_l2', formal_dyslexia_diagnosis=None,
                review_scope='isolated word pair; full sentence not independently adjudicated',
                review_reason=item['review']['reason'], redistributable=False))
    return cases


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--reviews', type=Path)
    parser.add_argument('--reserve', type=int, default=20)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_relative_to(ROOT/'data/local'):
        parser.error('Corpus files must remain in ignored data/local')
    raw = directory/'train.jsonl'
    rows = [json.loads(line) for line in raw.read_text(encoding='utf8').splitlines()]
    candidates = build_candidates(rows)
    write_json(directory/'candidates.json', candidates)
    meta = dict(source_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
                source_revision=(directory/'revision.txt').read_text().strip(),
                source_rows=len(rows), candidate_pairs=len(candidates), seed=20260924,
                candidate_categories=dict(Counter(c['category'] for c in candidates)),
                downloaded_split='train', untouched_source_splits=['validation','test'])
    if args.reviews:
        reviews = json.loads(args.reviews.read_text(encoding='utf8'))
        cases = finalize(candidates, reviews, args.reserve)
        write_json(directory/'reviewed-cases.json', cases)
        meta.update(reviewed_pairs=len(cases)//2, reserved_pairs=args.reserve,
                    evaluation_pairs=len(cases)//2-args.reserve,
                    reviewed_sha256=hashlib.sha256((directory/'reviewed-cases.json').read_bytes()).hexdigest())
    write_json(directory/'preparation.json', meta)
    print(json.dumps(meta, indent=2))


if __name__ == '__main__':
    main()
