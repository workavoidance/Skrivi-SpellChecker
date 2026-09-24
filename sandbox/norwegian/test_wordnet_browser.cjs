const {chromium}=require('C:/Users/jon/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');

(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.goto(process.argv[2]||'http://127.0.0.1:50987');
  assert.match(await page.locator('header').innerText(),/Norsk ordvev-eksperiment/);
  const direct=await page.evaluate(()=>request('/word-help',{words:['hjerne','gjerne','lekser','lakser']}));
  assert.equal(direct.available,true);
  assert(direct.entries.hjerne.senses.some(sense=>sense.broader.includes('organ')));
  assert(direct.entries.lekser.senses.some(sense=>sense.broader.includes('skolearbeid')));
  assert(direct.entries.lakser.senses.some(sense=>sense.broader.includes('fisk')));
  // Gjerne has curated help and is not expected in this noun-heavy WordNet.
  assert.equal(direct.entries.gjerne,undefined);

  await page.locator('#settings').evaluate(element=>element.open=true);
  await page.locator('#mode').selectOption('nuspell');
  await page.locator('#text').fill('Jeg går til biblteke.');
  await page.locator('#check').click();
  await page.locator('#review').waitFor({state:'visible',timeout:60000});
  const card=page.locator('.choice-card').filter({hasText:'biblioteket'}).first();
  await card.waitFor({state:'visible'});
  assert.match(await card.innerText(),/Korte betydningshint/);
  assert.match(await card.innerText(),/institusjon|samling|bygning/);
  await card.locator('details').evaluate(element=>element.open=true);
  assert.match(await card.innerText(),/Automatisk betydningshint fra Norsk ordvev/);
  assert.equal(await page.locator('#text').inputValue(),'Jeg går til biblteke.');
  await page.locator('#helpStyle').selectOption('synonym');
  assert.match(await card.innerText(),/Lignende eller overordnede ord/);
  assert.equal(errors.length,0,errors.join('\n'));
  console.log('WordNet experiment browser checks passed: offline lookup, UI fallback, help-style rerender and no automatic edit.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
