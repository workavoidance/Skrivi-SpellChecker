"""Experimental offline base-form and recorded-component help; no spelling changes."""
from __future__ import annotations
from contextlib import closing
import csv
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tarfile
from dictionary_help import DictionaryHelp, norm


def build_base_index(archive, target):
    archive, target = Path(archive), Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix('.partial.sqlite3')
    partial.unlink(missing_ok=True)
    db = sqlite3.connect(partial)
    def rows(bundle, name):
        with io.TextIOWrapper(bundle.extractfile(name), encoding='latin-1') as stream:
            yield from csv.DictReader(stream, delimiter='\t')
    try:
        db.executescript('''CREATE TABLE base(form TEXT,lemma TEXT,tag TEXT,
                            PRIMARY KEY(form,lemma,tag)) WITHOUT ROWID;
                            CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);''')
        with tarfile.open(archive, 'r:gz') as bundle:
            lemmas = {r['LEMMA_ID']: norm(r['GRUNNFORM']) for r in rows(bundle,'lemma.txt')}
            batch = []
            today = date.today().isoformat().replace('-','')
            for row in rows(bundle,'fullformsliste.txt'):
                start = row['FRADATO'].strip().replace('-','')
                end = row['TILDATO'].strip().replace('-','')
                # Archive dates use year precision; 4000 denotes open-ended.
                if start and start[:4].isdigit() and int(start[:4]) > int(today[:4]):continue
                if end and end[:4].isdigit() and int(end[:4]) < int(today[:4]):continue
                if row['NORMERING'].casefold() != 'normert' or 'prop' in row['TAG'].split():continue
                lemma = lemmas.get(row['LEMMA_ID'])
                if not lemma:continue
                batch.append((norm(row['OPPSLAG']),lemma,row['TAG']))
                if len(batch)>=10000:
                    db.executemany('INSERT OR IGNORE INTO base VALUES(?,?,?)',batch);batch.clear()
            db.executemany('INSERT OR IGNORE INTO base VALUES(?,?,?)',batch)
        meta={'source_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
              'source':'Norsk ordbank 2022-02-01; CC BY 4.0',
              'filter':'normert, non-proper, year-valid at build time',
              'build_date':date.today().isoformat()}
        db.executemany('INSERT INTO metadata VALUES(?,?)',meta.items());db.commit();db.execute('VACUUM')
        count=db.execute('SELECT count(*) FROM base').fetchone()[0]
    except BaseException:
        db.close();partial.unlink(missing_ok=True);raise
    db.close();partial.replace(target)
    return dict(meta,rows=count,bytes=target.stat().st_size)

class CompoundHelp:
    def __init__(self, dictionary, base_database, compound_database):
        self.dictionary=dictionary
        self.base_database=Path(base_database)
        self.compound_database=Path(compound_database)

    def bases(self, word):
        with closing(sqlite3.connect(self.base_database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            return [r[0] for r in db.execute('SELECT DISTINCT lemma FROM base WHERE form=? ORDER BY lemma',(norm(word),))]

    def whole(self, word):
        exact=self.dictionary.lookup(word)
        if exact:return dict(exact,kind='exact')
        matches=[]
        for lemma in self.bases(word):
            if norm(lemma)==norm(word):continue
            entry=self.dictionary.lookup(lemma)
            if entry:matches.append({'base':lemma,'entry':entry})
        if not matches:return None
        return {'word':word,'kind':'base','matches':matches}

    def noun(self, word):
        with closing(sqlite3.connect(self.base_database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
            return db.execute("SELECT 1 FROM base WHERE form=? AND tag LIKE 'subst %' LIMIT 1",(norm(word),)).fetchone() is not None

    def lookup(self, word, noun_only=True):
        if not isinstance(word,str) or not 0<len(word)<=100:return None
        whole=self.whole(word)
        if whole:return whole
        alternatives=[];seen=set()
        # Exact recorded boundaries only. Never strip hyphens or guess suffixes.
        for base in dict.fromkeys([norm(word),*self.bases(word)]):
            with closing(sqlite3.connect(self.compound_database.resolve().as_uri()+'?mode=ro',uri=True)) as db:
                rows=db.execute('SELECT first,fugue,second FROM compound WHERE form=? ORDER BY first,fugue,second',(base,)).fetchall()
            for first,link,second in rows:
                if first+(link or '')+second != base:continue
                if noun_only and not self.noun(second):continue
                key=(base,first,link,second)
                if key in seen:continue
                seen.add(key)
                left,right=self.whole(first),self.whole(second)
                # Count complete two-part help only. No recursive decomposition.
                if not left or not right:continue
                alternatives.append({'base':base,'first':first,'linking':link or '',
                                     'second':second,'parts':[left,right]})
        if alternatives:
            return {'word':word,'kind':'components','analyses':alternatives,
                    'label':'Forklaringer på delene av ordet',
                    'notice':'Dette er ikke en definisjon av hele ordet. Eksemplene gjelder delene.',
                    'analysis_source':'Norsk ordbank 2022-02-01'}
        return None
