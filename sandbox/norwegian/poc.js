// Local, curated sense examples. Clues are explanatory, never replacement suggestions.
// These senses are not automatically selected to match the writer's sentence.
meanings.push(
 {forms:['masse'],definition:'Mye eller mange, når vi snakker om en stor mengde.',clue:'mye / mange',example:'Det ligger masse snø i hagen.',source:'https://www.riksmalsforbundet.no/qa_faqs/hva-er-forskjellen-mellom-masse-og-mange/'},
 {forms:['gjerne'],definition:'Brukes når du har lyst til noe eller gjør noe med glede.',clue:'med glede',example:'Jeg vil gjerne bli med på tur.',source:'https://ordbokene.no/bm/gjerne'},
 {forms:['hjerne','hjernen'],definition:'Den delen inne i hodet som vi blant annet bruker til å tenke og huske.',example:'Hjernen hjelper oss å lære nye ting.',source:'https://ordbokene.no/bm/hjerne'},
 {forms:['gjøre','gjør','gjorde','gjort'],definition:'Å utføre noe, for eksempel en oppgave.',clue:'utføre',example:'Vi skal gjøre oppgaven sammen.',source:'https://ordbokene.no/bm/gjøre'},
 {forms:['huske','husker','husket'],definition:'Å ha noe i minnet, slik at du ikke glemmer det.',clue:'minnes',example:'Jeg må huske å ta med matpakken.',source:'https://ordbokene.no/bm/huske'}
);
meaningFor('mase').clue='gnåle';
let voiceReady=false,voiceName='',audio=null,audioGeneration=0,speechPreparing=false;
const audioCache=new Map();
function stopSpeech(){
 audioGeneration++;if(audio){audio.pause();audio.src='';audio=null;}
 $('stopAudio').disabled=true;
 if(voiceReady)$('audioStatus').textContent='Norsk opplesning er klar. Trykk på «Hør» når du vil lytte.';
}
async function hear(content,kind,word){
 stopSpeech();const generation=audioGeneration;
 if(!voiceReady){$('audioStatus').textContent='Norsk opplesning er ikke tilgjengelig. Du kan lese ordhjelpen.';return;}
 if(speechPreparing){$('audioStatus').textContent='Lyden klargjøres. Prøv igjen om et øyeblikk.';return;}
 $('stopAudio').disabled=false;$('audioStatus').textContent='Klargjør lyd …';
 try{
  let data=audioCache.get(content);
  if(!data){speechPreparing=true;try{data=await request('/speech',{text:content});}finally{speechPreparing=false;}
   if(audioCache.size>=20)audioCache.delete(audioCache.keys().next().value);audioCache.set(content,data);}
  if(generation!==audioGeneration)return;
  audio=new Audio('data:audio/wav;base64,'+data.audio);
  audio.onended=()=>{if(generation===audioGeneration){$('stopAudio').disabled=true;$('audioStatus').textContent='Ferdig. Hjalp det deg å kjenne igjen ordet?';}};
  audio.onerror=()=>{if(generation===audioGeneration){$('stopAudio').disabled=true;$('audioStatus').textContent='Lyden kunne ikke spilles av. Prøv igjen.';}};
  await audio.play();if(generation!==audioGeneration)return;
  $('audioStatus').textContent='Leser opp …';event('listen',{kind,word,help_style:$('helpStyle').value});
 }catch(e){if(generation===audioGeneration){$('stopAudio').disabled=true;$('audioStatus').textContent=e.message||'Lyden kunne ikke spilles av.';}}
}
function listenButton(label,content,kind,word){const b=document.createElement('button');b.textContent=label;b.disabled=!voiceReady;b.setAttribute('aria-label',label+' – '+word);b.onclick=()=>hear(content,kind,word);return b;}
function helpContent(word){
 const meaning=meaningFor(word),style=$('helpStyle').value;
 if(!meaning)return null;
 if(style==='example')return {label:'Et eksempel',text:meaning.example,kind:'example',meaning};
 if(style==='synonym'&&meaning.clue)return {label:'Lignende betydning i denne bruken',text:meaning.clue,kind:'synonym',meaning};
 return {label:style==='synonym'?'Kort forklaring – ingen enklere synonym her':'En mulig betydning',text:meaning.definition,kind:'definition',meaning};
}
suggestionCard=function(w,s){
 const card=document.createElement('section');card.className='choice-card';
 const title=document.createElement('h3');title.textContent=s;card.append(title);
 const info=helpContent(s);
 if(info){
  const label=document.createElement('div');label.className='hint-label';label.textContent=info.label;
  const p=document.createElement('p');p.textContent=info.text;card.append(label,p);
  const actions=document.createElement('div');actions.className='audio-actions';
  actions.append(listenButton('Hør ordet',s,'word',s),listenButton('Hør ord og hjelp',s+'. '+info.text,info.kind,s));card.append(actions);
  const details=document.createElement('details'),summary=document.createElement('summary'),extra=document.createElement('p');
  const exampleFirst=info.kind==='example';summary.textContent=exampleFirst?'Se forklaringen':'Se et eksempel';
  extra.textContent=exampleFirst?info.meaning.definition:info.meaning.example;
  details.append(summary,extra,listenButton(exampleFirst?'Hør forklaringen':'Hør eksemplet',s+'. '+extra.textContent,exampleFirst?'definition':'example',s));
  details.ontoggle=()=>{if(details.open)event('open_help',{word:s,help_style:$('helpStyle').value});};card.append(details);
  const note=document.createElement('p');note.className='meaning-note';note.textContent='Ordet kan ha flere betydninger. ';
  const link=document.createElement('a');link.textContent='Kilde (nettside)';link.href=info.meaning.source;link.target='_blank';link.rel='noopener noreferrer';note.append(link);card.append(note);
 }else{
  const p=document.createElement('p');p.textContent='Vi har ikke en forklaring på dette ordet ennå. Du kan høre ordet eller hoppe over.';card.append(p,listenButton('Hør ordet',s,'word',s));
 }
 const use=document.createElement('button');use.className='primary';use.textContent=w.practice?'Dette er ordet jeg mener':'Bruk «'+s+'»';
 use.onclick=()=>{stopSpeech();if(w.practice){$('practiceFeedback').textContent='Du valgte «'+s+'». Teksten din er ikke endret.';event('practice_choice',{word:s,help_style:$('helpStyle').value});}else accept(w,s);};card.append(use);
 return card;
};
const originalRender=render;
render=function(){
 stopSpeech();originalRender();$('originalHelp').replaceChildren();
 if(result){const buttons=$('review').querySelectorAll('button.word');result.words.forEach((w,i)=>{if(decisions[w.id]==='skip'){buttons[i].classList.remove('OK');buttons[i].classList.add('skipped');buttons[i].setAttribute('aria-label',w.word+': hoppet over, fortsatt usikker');}});}
 if(!result||selected===null)return;
 const w=result.words.find(x=>x.id===selected),info=helpContent(w.word);
 const box=document.createElement('div');box.className='original-help';
 box.append(listenButton('Hør det du skrev',w.word,'original',w.word));
 if(info){const details=document.createElement('details'),summary=document.createElement('summary'),p=document.createElement('p');summary.textContent='Hva kan «'+w.word+'» bety?';p.textContent=info.meaning.definition;details.append(summary,p,listenButton('Hør betydningen',w.word+'. '+p.textContent,'original_definition',w.word));box.append(details);}
 $('originalHelp').append(box);
 // Keep implementation scores out of the writing flow.
 $('reason').textContent=w.status==='OK'?'Ingen feil funnet her. Du kan beholde ordet.':'Er dette ordet du mente? Les eller hør forslagene. Du bestemmer.';
};
const originalAdvance=advance;
advance=function(){originalAdvance();if(selected===null){const skipped=Object.values(decisions).filter(x=>x==='skip').length;if(skipped)$('status').textContent='Gjennomgangen er ferdig. '+skipped+' ord er hoppet over og fortsatt usikre.';}};
let practicePair=['lekser','lakser'];
function renderPractice(){ $('practiceChoices').replaceChildren();for(const s of practicePair)$('practiceChoices').append(suggestionCard({practice:true},s)); }
$('practiceToggle').onclick=()=>{stopSpeech();$('practice').classList.toggle('hidden');renderPractice();};
for(const [id,pair] of [['pairSchool',['lekser','lakser']],['pairAmount',['mase','masse']],['pairWish',['gjerne','hjerne']]])$(id).onclick=()=>{stopSpeech();practicePair=pair;$('practiceFeedback').textContent='';renderPractice();};
$('helpStyle').onchange=()=>{event('help_style',{style:$('helpStyle').value});render();renderPractice();};
$('stopAudio').onclick=()=>{stopSpeech();event('stop_audio');};
for(const id of ['edit','check','undo','keep','skip','close']){const original=$(id).onclick;$(id).onclick=(...args)=>{stopSpeech();return original(...args);};}
window.addEventListener('pagehide',stopSpeech);
request('/voices',{}).then(data=>{voiceReady=Boolean(data.local&&data.voices?.length);voiceName=data.voices?.[0]?.name||'';render();renderPractice();$('audioStatus').textContent=voiceReady?'Norsk opplesning er klar. Trykk på «Hør» når du vil lytte.':'Ingen norsk stemme er tilgjengelig. Ordhjelpen virker fortsatt uten lyd.';}).catch(()=>{$('audioStatus').textContent='Opplesning er ikke tilgjengelig. Du kan fortsatt lese ordhjelpen.';});
