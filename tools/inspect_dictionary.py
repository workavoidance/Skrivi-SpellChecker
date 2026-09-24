"""Reproducible structural audit; not a production dictionary importer."""
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'local' / 'dictionary'
ROOT.mkdir(parents=True, exist_ok=True)
source = ROOT / 'bokmaal-articles.json.gz'
raw = gzip.decompress(source.read_bytes())
articles = json.loads(raw)
counts = collections.Counter()
statuses = collections.Counter()
types = collections.Counter()
compact = []
samples = {}
special_nodes = {}
by_status = collections.defaultdict(collections.Counter)
targets = {'gjerne', 'hjerne', 'nøkkel', 'bibliotek', 'lekse', 'budsjett',
           'venninne', 'brettspill', 'sommerfugl', 'kompenserende', 'kompensere'}
unique_lemmas = set()
unique_forms = set()

def scan(nodes):
    definitions, examples = [], []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        kind = n.get('type_')
        if kind in ('sub_article', 'compound_list') and kind not in special_nodes:
            special_nodes[kind] = n
        types[kind] += 1
        if kind == 'explanation' and (n.get('content', '').strip() or n.get('items')):
            definitions.append(n)
        elif kind == 'example' and (n.get('quote', {}).get('content', '').strip() or n.get('quote', {}).get('items')):
            examples.append(n)
        a, b = scan(n.get('elements', []))
        definitions.extend(a)
        examples.extend(b)
        if kind == 'sub_article':
            a, b = scan(n.get('article', {}).get('body', {}).get('definitions', []))
            definitions.extend(a)
            examples.extend(b)
    return definitions, examples

for key, article in articles.items():
    statuses[str(article.get('status'))] += 1
    nodes = article.get('body', {}).get('definitions', [])
    defs, exs = scan(nodes)
    counts['articles'] += 1
    by_status[str(article.get('status'))].update({'articles': 1, 'definitions': int(bool(defs)), 'examples': int(bool(exs))})
    counts['with_definition_element'] += bool(defs)
    counts['with_example_element'] += bool(exs)
    counts['with_both'] += bool(defs and exs)
    counts['with_neither'] += not defs and not exs
    counts['definition_elements'] += len(defs)
    counts['example_elements'] += len(exs)
    counts['definition_elements_with_placeholders'] += sum('$' in x.get('content', '') for x in defs)
    names = [x.get('lemma') for x in article.get('lemmas', []) if x.get('lemma')]
    unique_lemmas.update(names)
    forms = set(names)
    for lemma in article.get('lemmas', []):
        for paradigm in lemma.get('paradigm_info', []):
            if paradigm.get('to') is None and paradigm.get('standardisation') == 'STANDARD':
                forms.update(x['word_form'] for x in paradigm.get('inflection', []) if x.get('word_form'))
    unique_forms.update(forms)
    compact.append({'id': article.get('article_id', key), 'lemmas': names,
                    'forms': sorted(forms), 'definitions': nodes})
    for name in set(names) & targets:
        samples.setdefault(name, []).append({'id': article.get('article_id', key),
            'definition_elements': len(defs), 'example_elements': len(exs),
            'definitions': defs[:2], 'examples': exs[:2]})

payload = json.dumps(compact, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
packed = gzip.compress(payload, compresslevel=9, mtime=0)
(ROOT / 'bokmaal-compact-prototype.json.gz').write_bytes(packed)
metrics = {
    'source': 'https://ord.uib.no/bm/fil/article.json.gz',
    'download_date': '2026-09-21',
    'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'download_bytes': source.stat().st_size,
    'uncompressed_bytes': len(raw),
    'compact_json_bytes': len(payload),
    'compact_gzip_bytes': len(packed),
    'counts': dict(counts), 'statuses': dict(statuses),
    'coverage_by_status': dict(by_status),
    'unique_lemma_strings': len(unique_lemmas),
    'unique_headword_and_current_standard_form_strings': len(unique_forms),
    'definition_tree_node_types': dict(types),
    'limitations': [
        'Counts are structural article-level coverage, not quality or suggestion coverage.',
        'Examples include phrases, sentences and examples within nested senses/expressions.',
        'Definition elements can contain cross-references and unresolved entity placeholders.',
        'Prototype retains definition trees but is not a rendered, licensed production package.',
        'Prototype form list omits grammar tags; production should retain these.',
        'No automatic contextual sense selection has been evaluated.'
    ]
}
(ROOT / 'bokmaal-inspection-metrics.json').write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
(ROOT / 'bokmaal-inspection-samples.json').write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(metrics, indent=2, ensure_ascii=True))
print('Sample coverage:', json.dumps({k: [(x['definition_elements'], x['example_elements']) for x in v] for k, v in samples.items()}, ensure_ascii=True))
print('Special node structures:', json.dumps(special_nodes, ensure_ascii=True)[:6500])
