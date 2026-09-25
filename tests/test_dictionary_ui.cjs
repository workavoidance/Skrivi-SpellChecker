const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element{
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.className='';}
 append(...xs){for(const x of xs){x.parent=this;this.children.push(x);}}
 prepend(x){x.parent=this;this.children.unshift(x);}
 remove(){this.parent.children=this.parent.children.filter(x=>x!==this);}
 insertBefore(x,before){x.parent=this;this.children.splice(this.children.indexOf(before),0,x);}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
 querySelectorAll(selector){const all=this.children.flatMap(x=>[x,...x.querySelectorAll('*')]);if(selector==='*')return all;if(selector==='.candidate-actions')return all.filter(x=>x.className==='candidate-actions');if(selector==='button:not(.primary)')return all.filter(x=>x.tagName==='BUTTON'&&x.className!=='primary');return [];}
}
const nodes={check:{onclick:async()=>{}},helpStyle:{value:'example'},status:{textContent:''}};
const context=vm.createContext({document:{createElement:t=>new Element(t)},$:id=>nodes[id],result:null,render(){},request(){},listenButton:()=>new Element('button'),suggestionCard(){const card=new Element('section'),actions=new Element('div'),use=new Element('button');actions.className='candidate-actions';use.className='primary';use.onclick=()=>{context.accepted=true;};actions.append(use);card.append(new Element('h3'),new Element('p'),actions);return card;},assert});
vm.runInContext(fs.readFileSync('sandbox/norwegian/dictionary.js','utf8'),context);
vm.runInContext(`
dictionaryEntries.test={senses:[{definition:'meaning one',examples:[{text:'example one',explanation:''}],lemma:'test',source_url:'https://ordbokene.no/bm/1'},{definition:'meaning two',examples:[],lemma:'test',source_url:'https://ordbokene.no/bm/2'}]};
const card=suggestionCard({},'test');
const text=el=>[el.textContent||'',...el.children.map(text)].join(' ');
assert(text(card).includes('example one'));assert(text(card).includes('meaning one'));assert(!text(card).includes('meaning two'));
const details=card.querySelectorAll('*').find(x=>x.tagName==='DETAILS');details.open=true;details.ontoggle();assert(text(card).includes('meaning two'));assert(text(card).includes('Ingen eksempeltekst'));
assert(!globalThis.accepted);card.querySelector('.candidate-actions').children.find(x=>x.className==='primary').onclick();assert(globalThis.accepted);
$('helpStyle').value='definition';const other=suggestionCard({},'test');assert(text(other).indexOf('meaning one')<text(other).indexOf('example one'));
`,context);
console.log('Dictionary UI: sense/example pairing, details, missing examples and explicit acceptance passed.');
