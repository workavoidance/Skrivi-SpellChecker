// Experimental fallback meaning clues from the local Norsk ordvev index.
// Curated definitions and examples always take precedence.
let wordnetEntries={};

function wordnetSenseClue(sense, preferSynonyms){
 const primary=preferSynonyms?sense.synonyms:sense.broader;
 const fallback=preferSynonyms?sense.broader:sense.synonyms;
 const terms=(primary&&primary.length?primary:fallback)||[];
 return terms[terms.length-1]||null;
}
function wordnetSummary(entry){
 const preferSynonyms=$('helpStyle').value==='synonym',terms=[];
 for(const sense of entry.senses||[]){
  const clue=wordnetSenseClue(sense,preferSynonyms);
  if(clue&&!terms.includes(clue))terms.push(clue);
  if(terms.length===3)break;
 }
 return terms;
}
function addWordnetHelp(card,word,entry){
 if(!entry||card.querySelector('.hint-label'))return;
 const actions=card.querySelector('.candidate-actions');
 const oldText=[...card.children].find(el=>el.tagName==='P'&&!el.classList.contains('meaning-note'));
 if(oldText)oldText.remove();
 const oldHear=actions?.querySelector('button:not(.primary)');if(oldHear)oldHear.remove();
 const terms=wordnetSummary(entry);
 if(!terms.length)return;
 const label=document.createElement('div');label.className='hint-label';
 label.textContent=$('helpStyle').value==='synonym'?'Lignende eller overordnede ord':'Korte betydningshint';
 const clue=document.createElement('p');clue.textContent=terms.join(' / ');
 const details=document.createElement('details'),summary=document.createElement('summary');
 summary.textContent='Se mulige betydninger';details.append(summary);
 for(const [index,sense] of (entry.senses||[]).entries()){
  const pieces=[];
  if(sense.broader?.length)pieces.push('En slags '+sense.broader.slice(-2).join(' eller '));
  if(sense.synonyms?.length)pieces.push('Lignende betydning: '+sense.synonyms.slice(0,3).join(', '));
  if(sense.related?.length)pieces.push('Beslektet med: '+sense.related.slice(0,2).join(', '));
  if(!pieces.length)continue;
  const p=document.createElement('p');p.textContent=(entry.senses.length>1?'Mulighet '+(index+1)+': ':'')+pieces.join('. ')+'.';details.append(p);
 }
 const note=document.createElement('p');note.className='meaning-note';
 note.textContent='Automatisk betydningshint fra Norsk ordvev. Det kan vise feil betydning. ';
 const link=document.createElement('a');link.textContent='Om kilden';link.href=entry.source_url;link.target='_blank';link.rel='noopener noreferrer';note.append(link);details.append(note);
 details.ontoggle=()=>{if(details.open)event('open_wordnet_help',{word,lemma:entry.lemma});};
 card.insertBefore(label,actions);card.insertBefore(clue,actions);card.insertBefore(details,actions);
 if(actions)actions.prepend(listenButton('Hør ord og betydningshint',word+'. '+terms.join('. '),'wordnet',word));
}

const wordnetSuggestionCard=suggestionCard;
suggestionCard=function(w,s){
 const card=wordnetSuggestionCard(w,s);
 if(!meaningFor(s))addWordnetHelp(card,s,wordnetEntries[s]);
 return card;
};

async function loadWordnetForResult(){
 if(!result)return;
 const words=[];
 for(const item of result.words){
  if(item.status!=='OK'){
   words.push(item.word);
   for(const suggestion of item.suggestions||[])words.push(suggestion);
  }
 }
 if(!words.length)return;
 try{
  const response=await request('/word-help',{words});
  wordnetEntries=response.entries||{};
  event('wordnet_help_loaded',{requested:[...new Set(words)].length,covered:Object.keys(wordnetEntries).length});
  render();
 }catch(error){
  event('wordnet_help_failed',{message:error.message});
 }
}

const wordnetCheck=$('check').onclick;
$('check').onclick=async(...args)=>{
 wordnetEntries={};
 await wordnetCheck(...args);
 await loadWordnetForResult();
};

const wordnetHelpStyle=$('helpStyle').onchange;
$('helpStyle').onchange=(...args)=>{const response=wordnetHelpStyle(...args);render();return response;};
