const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};function element(){return {classList:{add(){},remove(){},toggle(){}},append(){},replaceChildren(){},setAttribute(){},focus(){}}}
const document={getElementById:id=>nodes[id]??=(element()),createElement:element,createTextNode:s=>s};
const ctx=vm.createContext({document,performance:{now:()=>0},assert});
const html=fs.readFileSync(__dirname+'/index.html','utf8');
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],ctx);
vm.runInContext(`
text='😀 idag går vi hjem.';
result={text,words:[
 {id:0,word:'idag',start_utf16:3,end_utf16:7,status:'UNCERTAIN',suggestions:['i dag'],operation:'split'},
 {id:1,word:'går',start_utf16:8,end_utf16:11,status:'OK',suggestions:[]}
]};selected=0;
accept(result.words[0],'i dag');
assert.equal(text,'😀 i dag går vi hjem.');
assert.equal(result.words[1].start_utf16,9);
$('undo').onclick();assert.equal(text,'😀 idag går vi hjem.');
accept(result.words[0],'i  dag');assert.equal(text,'😀 idag går vi hjem.');
accept(result.words[0],'i dag nå');assert.equal(text,'😀 idag går vi hjem.');
result.words[0].operation=undefined;
accept(result.words[0],'i dag');assert.equal(text,'😀 idag går vi hjem.');
`,ctx);
console.log('Split replacement, exact occurrence, offsets, undo and strict whitespace validation passed.');
