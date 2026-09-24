const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes={};function element(){return {classList:{add(){},remove(){},toggle(){}},append(){},replaceChildren(){},setAttribute(){},focus(){}}}
const document={getElementById:id=>nodes[id]??=(element()),createElement:element,createTextNode:s=>s};
const ctx=vm.createContext({document,performance:{now:()=>0},assert});
const html=fs.readFileSync(__dirname+'/index.html','utf8');
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],ctx);
vm.runInContext(`
text='😀 jakke lomma, jakke lomma.';
result={text,words:[{id:0,word:'jakke lomma',start_utf16:3,end_utf16:14,status:'UNCERTAIN',suggestions:['jakkelomma'],operation:'join'},
{id:2,word:'jakke lomma',start_utf16:16,end_utf16:27,status:'UNCERTAIN',suggestions:['jakkelomma'],operation:'join'}]};
selected=2;
accept(result.words[1],'jakkelomma');
assert.equal(text,'😀 jakke lomma, jakkelomma.');
assert.equal(result.words[0].word,'jakke lomma');
$('undo').onclick();assert.equal(text,'😀 jakke lomma, jakke lomma.');
accept(result.words[0],'jakkelomma');
assert.equal(text,'😀 jakkelomma, jakke lomma.');
assert.equal(text.slice(result.words[1].start_utf16,result.words[1].end_utf16),'jakke lomma');
accept(result.words[1],'two words');assert.equal(text,'😀 jakkelomma, jakke lomma.');
`,ctx);
console.log('Join, occurrence isolation, emoji offsets, subsequent offsets, undo and whitespace rejection passed.');
