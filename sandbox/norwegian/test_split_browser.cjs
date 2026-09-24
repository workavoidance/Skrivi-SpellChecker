const {chromium}=require('C:/Users/jon/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(process.argv[2]||'http://127.0.0.1:50991');
  assert.equal(await page.locator('#mode').inputValue(),'nuspell_context');
  await page.locator('#mode').selectOption('nuspell_compounds');
  await page.locator('#text').fill('idag skal jeg komme imårn.');
  await page.locator('#check').click();
  await page.locator('#review').waitFor({state:'visible',timeout:60000});
  await page.locator('#review button').filter({hasText:/^idag$/}).click();
  await page.getByRole('button',{name:'Bruk «i dag»',exact:true}).click();
  await page.locator('#review button').filter({hasText:/^imårn$/}).click();
  await page.getByRole('button',{name:'Bruk «i morgen»',exact:true}).click();
  assert.equal(await page.locator('#text').inputValue(),'i dag skal jeg komme i morgen.');
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('Optional split mode passed end-to-end in the son-facing POC.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
