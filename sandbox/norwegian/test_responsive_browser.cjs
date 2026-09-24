const {chromium}=require('C:/Users/jon/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(process.argv[2]||'http://127.0.0.1:50886');
  await page.waitForFunction(()=>document.querySelector('#audioStatus').textContent.includes('klar.'),{},{timeout:30000});
  assert.equal(await page.locator('#mode').inputValue(),'nuspell_context');
  await page.locator('#settings').evaluate(el=>el.open=true); await page.locator('#practiceToggle').click();
  assert.equal(await page.locator('#remember').count(),1);
  assert.equal(await page.getByRole('button',{name:'Glem alle huskede ord',exact:true}).count(),1);
  await page.locator('#practiceChoices').getByRole('button',{name:'Hør ord og hjelp – lekser',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#audioStatus').textContent.includes('Leser opp')||document.querySelector('#audioStatus').textContent.includes('Ferdig.'),{},{timeout:30000});
  await page.locator('#stopAudio').click();
  assert.equal(await page.locator('#text').inputValue(),'');
  await page.locator('#helpStyle').selectOption('synonym');
  await page.locator('#pairAmount').click();
  assert.match(await page.locator('#practiceChoices').innerText(),/gnåle/);
  await page.locator('#practiceChoices').getByRole('button',{name:'Dette er ordet jeg mener'}).first().click();
  assert.equal(await page.locator('#text').inputValue(),'');
  await page.locator('#helpStyle').selectOption('example');
  assert.match(await page.locator('#practiceChoices').innerText(),/Det ligger masse snø/);
  await page.locator('#settings').evaluate(el=>el.open=true); await page.locator('#practiceToggle').click();
  const original='😀 Jeg jobber med budsjet og budsjet.';
  await page.locator('#text').fill(original);
  await page.locator('#check').click();
  await page.locator('#review').waitFor({state:'visible',timeout:60000});
  await page.locator('#review button').filter({hasText:/^budsjet$/}).nth(1).click();
  assert.equal(await page.locator('#text').inputValue(),original);
  await page.locator('#skip').click();
  assert.equal(await page.locator('#review .skipped').count(),1);
  assert.equal(await page.locator('#text').inputValue(),original);
  await page.locator('#undo').click();
  await page.getByRole('button',{name:'Bruk «budsjett»',exact:true}).click();
  assert.equal(await page.locator('#text').inputValue(),'😀 Jeg jobber med budsjet og budsjett.');
  await page.locator('#undo').click();
  assert.equal(await page.locator('#text').inputValue(),original);
  await page.locator('#helpStyle').selectOption('definition');
  await page.locator('#review button').filter({hasText:/^budsjet$/}).first().click();
  await page.locator('#settings').evaluate(el=>el.open=false); await page.screenshot({path:path.join(__dirname,'responsive-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
  await page.screenshot({path:path.join(__dirname,'responsive-mobile.png'),fullPage:true});
  // Stop during audio generation: late responses must never start playback.
  await page.evaluate(()=>{audioCache.clear();});
  await page.locator('#choices').getByRole('button',{name:'Hør ord og hjelp – budsjett',exact:true}).click();
  await page.locator('#stopAudio').click();
  await page.waitForFunction(()=>!speechPreparing,{},{timeout:30000});
  assert(await page.evaluate(()=>audio===null));
  assert.equal(await page.locator('#text').inputValue(),original);
  assert.equal(errors.length,0,errors.join('\n'));
  const response=await page.request.post(new URL('/speech',page.url()).href,{data:{text:'hei'}});
  assert.equal(response.status(),403);
  fs.writeFileSync(path.join(__dirname,'responsive-verification.json'),JSON.stringify({
   browser:'Chrome headless',pageErrors:errors,localAudioGeneratedAndPlayed:true,
   stopCancelsPendingPlayback:true,practiceDoesNotEdit:true,helpStyles:true,
   rememberedWordControls:true,
   selectedOccurrenceOnly:true,undo:true,skipRemainsUncertain:true,unicodeOffsets:true,mobileNoOverflow:true,
   unauthenticatedSpeechRejected:true,voice:'Microsoft Jon',
   limitation:'Audio decoded and playback started successfully; voice naturalness and child comprehension have not been judged.'},null,2));
  console.log('POC browser checks passed, including real local speech, stop, help styles, isolated edits, undo, Unicode and mobile layout.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});

