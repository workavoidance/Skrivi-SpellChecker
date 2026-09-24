const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};
function element(tag){return {tag,children:[],classList:{add(){},remove(){},toggle(){}},append(...items){this.children.push(...items)},replaceChildren(){this.children=[]},setAttribute(){},focus(){}}}
const document={getElementById:id=>nodes[id]??=element('div'),createElement:element,createTextNode:s=>s};
const ctx=vm.createContext({document,performance:{now:()=>0},assert});
vm.runInContext(fs.readFileSync(__dirname+'/index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1],ctx);
vm.runInContext(`
text='lakser og lakser';
result={text,words:[{id:0,word:'lakser',start_utf16:0,end_utf16:6,status:'UNCERTAIN',suggestions:['lekser'],reason:''},{id:1,word:'lakser',start_utf16:10,end_utf16:16,status:'UNCERTAIN',suggestions:['lekser'],reason:''}]};selected=0;
render();
const card=$('choices').children[0];
assert.equal(card.children[1].textContent,'Skolearbeid du gjør hjemme.');
assert.equal(card.children.find(c=>c.tag==='details').children[1].textContent,'Sara gjør lekser før middag.');
assert.equal(text,'lakser og lakser'); // Rendering/explaining never accepts.
assert.equal(meaningFor('Lekser'),meaningFor('lekser'));
const missing=suggestionCard(result.words[0],'ukjentord');
assert(missing.children[1].textContent.includes('ikke en forklaring'));
assert.equal(missing.children.filter(c=>c.tag==='button').length,1);
card.children.find(c=>c.tag==='button').onclick();
assert.equal(text,'lekser og lakser');
$('undo').onclick();assert.equal(text,'lakser og lakser');
$('skip').onclick();assert.equal(text,'lakser og lakser');assert.equal(decisions[0],'skip');
`,ctx);
console.log('Meaning/example rendering, missing entries, explicit acceptance, occurrence isolation, undo and skip passed.');
