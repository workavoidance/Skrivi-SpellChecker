"""Offline Bokmaalsordboka index. No network or model dependencies."""
from __future__ import annotations
import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import unicodedata

SOURCE = 'https://ord.uib.no/bm/fil/article.json.gz'
VERSION = '1'
NOTICE = ('Bokmålsordboka © Universitetet i Bergen og Språkrådet. '
          'Extracted and indexed by Skrivi. Local evaluation under the published open-use '
          'statement; exact licence document pending verification. No endorsement implied.')

def cache_path():
    root = Path(os.environ.get('SKRIVI_CACHE_DIR') or Path(os.environ['LOCALAPPDATA']) / 'Skrivi')
    return root / 'lexical' / 'bokmaal' / 'dictionary.sqlite3'

def norm(text):
    return unicodedata.normalize('NFC', text).casefold().strip()

class Renderer:
    def __init__(self, articles, concepts):
        self.articles = articles
        self.concepts = concepts.get('concepts', concepts)
        self.errors = collections.Counter()

    def text(self, node, depth=0):
        if depth > 20:
            raise ValueError('nested_text_depth')
        content = node.get('content', node.get('text', ''))
        if not isinstance(content, str):
            content = node.get('text')
        if not isinstance(content, str):
            raise ValueError('non_text_content')
        items = node.get('items', [])
        if content.count('$') != len(items):
            raise ValueError('placeholder_count')
        pieces = content.split('$')
        out = pieces[0]
        for item, tail in zip(items, pieces[1:]):
            out += self.item(item, depth + 1) + tail
        return ' '.join(out.split())

    def item(self, item, depth):
        kind = item.get('type_')
        if kind == 'article_ref':
            if item.get('word_form'):
                return item['word_form']
            names = [x['lemma'] for x in item.get('lemmas', []) if x.get('lemma')]
            if not names:
                target = self.articles.get(str(item.get('article_id')), {})
                names = [x['lemma'] for x in target.get('lemmas', []) if x.get('lemma')]
            if not names:
                raise ValueError('missing_reference')
            # Display reference labels; never recursively borrow an unrelated sense.
            return ' / '.join(dict.fromkeys(names))
        if kind == 'fraction':
            return str(item['numerator']) + '/' + str(item['denominator'])
        if 'content' in item or 'text' in item:
            return self.text(item, depth)
        concept = self.concepts.get(str(item.get('id')), {})
        if isinstance(concept, dict) and concept.get('expansion'):
            return concept['expansion']
        raise ValueError('unknown_entity')

    def safe(self, node):
        try:
            return self.text(node)
        except (ValueError, KeyError, TypeError) as exc:
            self.errors[str(exc)] += 1
            return None

    def senses(self, nodes, inherited=(), path=()):
        result = []
        for i, node in enumerate(nodes):
            if node.get('type_') != 'definition':
                continue
            children = node.get('elements', [])
            definitions = [self.safe(x) for x in children if x.get('type_') == 'explanation']
            # Suppress the affected sense rather than silently omit part of its meaning.
            if any(x is None for x in definitions):
                self.errors['suppressed_sense'] += 1
                continue
            context = inherited + tuple(x for x in definitions if x)
            examples = []
            for x in children:
                if x.get('type_') == 'example':
                    quote = self.safe(x.get('quote', {}))
                    explanation = self.safe(x.get('explanation', {}))
                    if quote and explanation is not None:
                        examples.append({'text': quote, 'explanation': explanation})
            nested = [x for x in children if x.get('type_') == 'definition']
            current = path + (str(node.get('id', i)),)
            if context and (definitions or examples or not nested):
                result.append({'sense_id': '/'.join(current), 'definition': '; '.join(context),
                               'examples': examples})
            result.extend(self.senses(nested, context, current))
            # Sub-articles/idioms aren't definitions of the enclosing headword.
        return result

def build_index(source, concepts, target):
    source, concepts, target = map(Path, (source, concepts, target))
    packed = source.read_bytes()
    articles = json.loads(gzip.decompress(packed))
    concept_bytes = concepts.read_bytes()
    renderer = Renderer(articles, json.loads(concept_bytes))
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix('.building.sqlite3')
    partial.unlink(missing_ok=True)
    counts = collections.Counter()
    statuses = collections.Counter()
    db = sqlite3.connect(partial)
    try:
        db.executescript('''
          CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE entries(id TEXT PRIMARY KEY,lemma TEXT NOT NULL,status TEXT,senses TEXT NOT NULL);
          CREATE TABLE forms(form TEXT NOT NULL,article TEXT NOT NULL,tags TEXT NOT NULL,
                             PRIMARY KEY(form,article,tags)) WITHOUT ROWID;
        ''')
        for key, article in articles.items():
            senses = renderer.senses(article.get('body', {}).get('definitions', []))
            counts['source_articles'] += 1
            if not senses:
                continue
            names = [x['lemma'] for x in article.get('lemmas', []) if x.get('lemma')]
            if not names:
                continue
            aid = str(article.get('article_id', key))
            status = str(article.get('status'))
            statuses[status] += 1
            db.execute('INSERT INTO entries VALUES(?,?,?,?)',
                       (aid, ' / '.join(names), status, json.dumps(senses, ensure_ascii=False)))
            forms = {(norm(x), aid, '[]') for x in names}
            for lemma in article.get('lemmas', []):
                for paradigm in lemma.get('paradigm_info', []):
                    if paradigm.get('to') is None and paradigm.get('standardisation') == 'STANDARD':
                        for form in paradigm.get('inflection', []):
                            if form.get('word_form'):
                                tags = paradigm.get('tags', []) + form.get('tags', [])
                                forms.add((norm(form['word_form']), aid, json.dumps(tags)))
            db.executemany('INSERT OR IGNORE INTO forms VALUES(?,?,?)', sorted(forms))
            counts['indexed_articles'] += 1
            counts['senses'] += len(senses)
            counts['articles_with_examples'] += any(s['examples'] for s in senses)
        counts['distinct_forms'] = db.execute('SELECT count(DISTINCT form) FROM forms').fetchone()[0]
        metadata = {'version': VERSION, 'source': SOURCE, 'source_sha256': hashlib.sha256(packed).hexdigest(),
                    'concepts_sha256': hashlib.sha256(concept_bytes).hexdigest(), 'notice': NOTICE,
                    'licence_status': 'open-use statement accepted for local testing; exact terms unverified',
                    'publication_filter': 'none; numeric editorial status meanings unverified',
                    'counts': dict(counts), 'render_errors': dict(renderer.errors), 'statuses': dict(statuses)}
        db.executemany('INSERT INTO metadata VALUES(?,?)',
                       [(k, json.dumps(v, ensure_ascii=False)) for k,v in metadata.items()])
        db.commit()
        db.execute('VACUUM')
    except BaseException:
        db.close()
        partial.unlink(missing_ok=True)
        raise
    else:
        db.close()
    partial.replace(target)
    metadata['database_bytes'] = target.stat().st_size
    return metadata

class DictionaryHelp:
    def __init__(self, database=None):
        self.database = Path(database) if database else cache_path()
        self.available = self.database.is_file()

    def lookup(self, word):
        if not self.available or not isinstance(word, str) or not 0 < len(word) <= 100:
            return None
        db = sqlite3.connect(self.database.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            version = db.execute("SELECT value FROM metadata WHERE key='version'").fetchone()
            if not version or json.loads(version[0]) != VERSION:
                raise ValueError('Dictionary index needs rebuilding.')
            rows = db.execute('''SELECT DISTINCT e.id,e.lemma,e.senses FROM entries e
                                 JOIN forms f ON f.article=e.id WHERE f.form=? ORDER BY e.id''',
                              (norm(word),)).fetchall()
            senses = []
            for aid, lemma, content in rows:
                for sense in json.loads(content):
                    senses.append(dict(sense, lemma=lemma, article_id=aid,
                                       source_url='https://ordbokene.no/bm/'+aid))
            if not senses:
                return None
            return {'word': word, 'source': 'Bokmålsordboka', 'notice': NOTICE, 'senses': senses}
        finally:
            db.close()

    def lookup_many(self, words):
        if not isinstance(words, list) or len(words) > 500:
            raise ValueError('Expected at most 500 words.')
        return {w: value for w in dict.fromkeys(w for w in words if isinstance(w,str))
                if (value := self.lookup(w))}
