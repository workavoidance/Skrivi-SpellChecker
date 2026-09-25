// Dictionary senses stay paired with their own examples. Text is never inserted as HTML.
let dictionaryEntries={};
const dictionaryPreviousCard=suggestionCard;
suggestionCard=function(w,s){
 const card=dictionaryPreviousCard(w,s),entry=dictionaryEntries[s];
 if(!entry)return card;
 const actions=card.querySelector('.candidate-actions');
 for(const child of [...card.children])if(child!==actions&&child.tagName!=='H3')child.remove();
 for(const button of [...actions.querySelectorAll('button:not(.primary)')])button.remove();
 const senses=entry.senses||[],exampleFirst=$('helpStyle').value==='example';
 // Prefer a sense with an example only when the writer requests examples.
 const first=(exampleFirst?senses.find(x=>x.examples.length):null)||senses[0];
 if(!first)return card;
 function showSense(parent,sense){
  const meaning=document.createElement('p');meaning.textContent=sense.definition;
  const example=sense.examples[0];
  if(exampleFirst&&example){const p=document.createElement('p');p.textContent='«'+example.text+'»';parent.append(p);}
  parent.append(meaning);
  if(!exampleFirst&&example){const p=document.createElement('p');p.textContent='Eksempel: '+example.text;parent.append(p);}
  if(example?.explanation){const p=document.createElement('p');p.textContent=example.explanation;parent.append(p);}
  if(!example){const p=document.createElement('p');p.className='meaning-note';p.textContent='Ingen eksempeltekst i denne betydningen.';parent.append(p);}
  const text=exampleFirst&&example?example.text:sense.definition;
  parent.append(listenButton('Hør ord og hjelp',s+'. '+text,'dictionary',s));
  const link=document.createElement('a');link.textContent='Bokmålsordboka: '+sense.lemma;link.href=sense.source_url;link.target='_blank';link.rel='noopener noreferrer';parent.append(link);
 }
 const help=document.createElement('div');help.className='dictionary-help';
 const label=document.createElement('div');label.className='hint-label';label.textContent='En mulig betydning';help.append(label);showSense(help,first);
 if(senses.length>1){const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Andre betydninger ('+(senses.length-1)+')';details.append(summary);
  details.ontoggle=()=>{if(details.open&&!details.dataset.loaded){details.dataset.loaded='yes';for(const sense of senses){if(sense===first)continue;const section=document.createElement('section');showSense(section,sense);details.append(section);}}};help.append(details);}
 const note=document.createElement('p');note.className='meaning-note';note.textContent='Bokmålsordboka · UiB og Språkrådet. Betydningen er ikke valgt ut fra setningen din.';help.append(note);
 card.insertBefore(help,actions);actions.prepend(listenButton('Hør ordet',s,'word',s));return card;
};
const dictionaryCheck=$('check').onclick;
$('check').onclick=async(...args)=>{
 dictionaryEntries={};await dictionaryCheck(...args);if(!result)return;
 const checked=result,words=[...new Set(result.words.filter(x=>x.status!=='OK').flatMap(x=>[x.word,...x.suggestions]))];
 try{const loaded={};for(let i=0;i<words.length;i+=100){const response=await request('/word-help',{words:words.slice(i,i+100)});Object.assign(loaded,response.entries);}
  if(result!==checked)return;dictionaryEntries=loaded;render();
 }catch(error){$('status').textContent+=' Ordbokhjelpen kunne ikke lastes: '+error.message;}
};
