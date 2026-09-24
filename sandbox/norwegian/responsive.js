// Rearrange existing controls without replacing the checker, speech or decision logic.
const main=document.querySelector('main');
main.classList.add('writing');
const tools=$('check').parentElement;tools.classList.add('main-tools');
tools.prepend($('check'));tools.append($('copy'),$('stopAudio'));
const settings=document.createElement('details');settings.id='settings';
const settingsTitle=document.createElement('summary');settingsTitle.textContent='Innstillinger og utprøving';settings.append(settingsTitle);
const engineTools=document.createElement('div');engineTools.className='tools';
engineTools.append(document.querySelector('label[for="mode"]'),$('mode'));
settings.append(engineTools,document.querySelector('.help-tools'),$('practice'));
const personalTools=document.createElement('div');personalTools.className='tools';
const clearRemembered=document.createElement('button');clearRemembered.id='clearRemembered';clearRemembered.textContent='Glem alle huskede ord';
personalTools.append(clearRemembered);settings.append(personalTools);
const about=document.querySelector('main > details');
const exportTools=$('export').parentElement;settings.append(exportTools,about);
main.insertBefore(settings,document.querySelector('footer'));
const workspace=document.createElement('div');workspace.id='workspace';
main.insertBefore(workspace,$('text'));
const draftColumn=document.createElement('article');draftColumn.id='draftColumn';draftColumn.setAttribute('aria-label','Teksten din');
draftColumn.append($('text'),$('review'),document.querySelector('.legend'));
workspace.append(draftColumn,$('panel'));
tools.after($('status'));workspace.after($('audioStatus'));
document.querySelector('.legend').firstElementChild.textContent='Uten markering: ingen feil funnet';
const panelHeader=document.createElement('div');panelHeader.id='panelHeader';
$('progress').after(panelHeader);panelHeader.append($('target'),$('originalHelp'));
const remember=document.createElement('button');remember.id='remember';remember.textContent='Husk ordet på denne PC-en';$('keep').after(remember);
const previousCard=suggestionCard;
suggestionCard=function(w,s){
 const card=previousCard(w,s), actions=document.createElement('div');actions.className='candidate-actions';
 const audioActions=card.querySelector('.audio-actions'), details=card.querySelector('details');
 if(audioActions){
  const buttons=[...audioActions.children];
  if(details&&buttons[0])details.append(buttons[0]);
  if(buttons[1])actions.append(buttons[1]);
  audioActions.remove();
 }else{const hear=card.querySelector('button:not(.primary)');if(hear)actions.append(hear);}
 const note=card.querySelector('.meaning-note');if(note&&details)details.append(note);
 actions.append(card.querySelector('.primary'));card.append(actions);return card;
};
function syncLayout(){
 const writing=!$('text').classList.contains('hidden');main.classList.toggle('writing',writing);
 if(writing)$('panel').classList.add('hidden');
}
const responsiveRender=render;
render=function(){responsiveRender();syncLayout();};
for(const id of ['edit','check','undo']){
 const handler=$(id).onclick;
 $(id).onclick=async(...args)=>{const response=handler(...args);syncLayout();await response;syncLayout();};
}
remember.onclick=async()=>{
 if(selected===null||busy)return;
 const w=result.words.find(word=>word.id===selected);busy=true;remember.disabled=true;
 try{await request('/personal-word',{action:'add',word:w.word});decisions[selected]='remember';event('remember',{id:selected});advance();$('status').textContent='Ordet er husket på denne PC-en.';}
 catch(error){$('status').className='error';$('status').textContent=error.message;}
 finally{busy=false;remember.disabled=false;}
};
clearRemembered.onclick=async()=>{
 if(busy||!confirm('Glemme alle ordene Skrivi har husket på denne PC-en?'))return;
 busy=true;clearRemembered.disabled=true;
 try{const response=await request('/personal-word',{action:'clear'});$('status').className='';$('status').textContent=response.removed+' huskede ord er fjernet. Sjekk teksten på nytt for å vurdere dem.';}
 catch(error){$('status').className='error';$('status').textContent=error.message;}
 finally{busy=false;clearRemembered.disabled=false;}
};
// Only observe writing/review state; resizing is entirely CSS and preserves focus.
new MutationObserver(syncLayout).observe($('text'),{attributes:true,attributeFilter:['class']});
syncLayout();
