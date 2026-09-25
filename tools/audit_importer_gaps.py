"""Audit expanded importer and residual lexical gaps on saved local predictions."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sandbox/norwegian'))
from dictionary_help import DictionaryHelp,cache_path,article_forms,norm
from compound_help import CompoundHelp
from setup_assets import ROOT
from ordbank_resources import OrdbankResources

def main():
    root=Path(__file__).resolve().parents[1]
    old=DictionaryHelp();new=DictionaryHelp(cache_path().with_name('dictionary-expanded.sqlite3'))
    bank=OrdbankResources();folder=ROOT/'lexical/ordbank-20220201'
    enhanced=CompoundHelp(new,folder/'help-baseforms.sqlite3',folder/'ordbank.sqlite3')
    counts=collections.Counter();gaps=collections.Counter();unique={};ranks=collections.defaultdict(collections.Counter);hashes={}
    source=Path.home()/'Documents/Skrivi/Research/Dictionary-Exploration/bokmaal-articles.json.gz'
    articles=json.load(gzip.open(source,'rt',encoding='utf-8'))
    source_forms=set()
    for a in articles.values():source_forms.update(w for w,_ in article_forms(a))
    for path in sorted((root/'results/baseline-20260924').glob('*-nuspell_context.json')):
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        for row in json.loads(path.read_text(encoding='utf-8')):
            for item in row['result']['words']:
                for rank,word in enumerate(item.get('suggestions',[]),1):
                    if word not in unique:
                        exact=new.lookup(word);before=old.lookup(word);e=enhanced.lookup(word)
                        related=new.lookup_expressions(word)
                        for base in enhanced.bases(word):
                            if norm(base)!=norm(word):related+=new.lookup_expressions(base)
                        analysis={'kind':e['kind'] if e else 'missing','before':bool(before),'direct':bool(exact),'related_expression':bool(related)}
                        if not e:
                            low=norm(word);info=bank.lookup(word)
                            if '-' in low or ' ' in low:
                                joined=low.replace('-','').replace(' ','')
                                analysis['gap']='separator_form_joined_has_help' if enhanced.lookup(joined) else 'separator_form_still_no_help'
                            elif related:analysis['gap']='expression_help_only'
                            elif low in source_forms:analysis['gap']='source_form_without_definition'
                            elif info and info['proper']:analysis['gap']='ordbank_proper_name'
                            elif enhanced.bases(word):analysis['gap']='ordbank_form_no_usable_dictionary_help'
                            else:analysis['gap']='no_recorded_form_link'
                        unique[word]=analysis
                    a=unique[word];counts['total']+=1;counts['old_direct']+=a['before'];counts['new_direct']+=a['direct'];counts[a['kind']]+=1
                    ranks[rank][a['kind']]+=1
                    if a['kind']=='missing':gaps[a['gap']]+=1
    bank.close()
    private=root/'results/importer-gaps-20260925';private.mkdir(exist_ok=True)
    (private/'word-audit.json').write_text(json.dumps(unique,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'counts':counts,'remaining_gap_categories':gaps,'by_rank':ranks,'unique_suggestions':len(unique),
            'unique_missing':sum(v['kind']=='missing' for v in unique.values()),'input_hashes':hashes,
            'limitations':['Categories are mechanical routing evidence, not correctness judgments.',
                          'Related expressions are not whole-word definitions and are excluded from definition/component coverage.',
                          'Joining separator forms is a diagnostic only, not a correction or acceptance rule.',
                          'Same reused baseline; no model inference or human usefulness claim.']}
    (root/'docs/benchmarks/2026-09-25-importer-gaps.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
