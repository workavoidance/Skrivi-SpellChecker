"""Measure lexical-help coverage without changing spell-checker scoring."""

from collections import Counter
import json
from pathlib import Path

from wordnet_help import WordnetHelp


HERE = Path(__file__).parent
CURATED = {
    'lekse', 'lekser', 'budsjett', 'budsjettet', 'venninne', 'venninnen', 'venninna',
    'brettspill', 'brettspell', 'trinn', 'trinnet', 'laks', 'lakser', 'mase', 'maser',
    'masse', 'gjerne', 'hjerne', 'hjernen', 'gjøre', 'gjør', 'gjorde', 'gjort',
    'huske', 'husker', 'husket',
}


def covered(help_index, word):
    return word.casefold() in CURATED or help_index.lookup(word) is not None


def measure(words, predicate):
    words = list(dict.fromkeys(words))
    hits = [word for word in words if predicate(word)]
    return {
        'unique_words': len(words), 'covered': len(hits),
        'coverage_percent': round(100 * len(hits) / len(words), 1) if words else 0,
        'missing': [word for word in words if word not in hits],
    }


def main(database, output=None):
    help_index = WordnetHelp(Path(database))
    cases = json.loads((HERE / 'cases.json').read_text(encoding='utf-8'))
    intended = [suggestion for case in cases for error in case.get('errors', [])
                for suggestion in error.get('suggestions', [])]
    son = next(case for case in cases if case['id'] == 'natural-paragraph01')
    son_intended = [suggestion for error in son['errors'] for suggestion in error['suggestions']]

    saved = json.loads((HERE / 'nuspell-experiments' / 'development-nuspell_context.json').read_text(encoding='utf-8'))
    actual = [suggestion for run in saved['runs'] for word in run['result']['words']
              for suggestion in word.get('suggestions', [])]
    groups = {
        'intended_corrections_all_cases': intended,
        'intended_corrections_son_paragraph': son_intended,
        'actual_candidates_saved_development_run': actual,
    }
    report = {
        'source': 'Norsk ordvev 1.1.2 plus the existing 12 curated word families',
        'curated_baseline': {name: measure(words, lambda word: word.casefold() in CURATED)
                             for name, words in groups.items()},
        'curated_plus_wordnet': {name: measure(words, lambda word: covered(help_index, word))
                                 for name, words in groups.items()},
        'most_common_actual_candidates': Counter(actual).most_common(20),
        'limitation': 'Coverage means a semantic relation exists. It does not mean the clue is simple, relevant to the sentence, or sufficient for choosing the intended word.',
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(rendered + '\n', encoding='utf-8')
    print(rendered)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('database')
    parser.add_argument('--output')
    args = parser.parse_args()
    main(args.database, args.output)
