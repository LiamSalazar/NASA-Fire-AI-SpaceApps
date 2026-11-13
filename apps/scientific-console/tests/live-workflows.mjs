/** Manual live demonstrations, excluded from deterministic tests. */
import { chromium } from '@playwright/test';
import { mkdir,writeFile,readFile,access } from 'node:fs/promises';
const output=new URL('../../../artifacts/scientific_console_release_20261112/live_browser/',import.meta.url);await mkdir(output,{recursive:true});
if(!process.argv.includes('--after-solid')) {
  try { await access(new URL('receipt.json',output)); throw new Error('Existing live receipts must not be overwritten. Use a new output directory for a new authorized campaign.'); } catch(error) { if(error.code!=='ENOENT') throw error; }
}
const receipt=process.argv.includes('--after-solid') ? JSON.parse(await readFile(new URL('receipt.json',output),'utf8')) : {boundary:'Live demonstrations, exposed questions; not independent scientific acceptance.',workflows:[],errors:[]};
if(process.argv.includes('--after-solid') && (receipt.workflows.length!==1 || receipt.workflows[0].label!=='A-solid-fuel')) throw new Error('This resume mode requires exactly one completed solid-fuel answer; no calls were made.');
const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(180000);
page.on('pageerror',e=>receipt.errors.push(e.message));
const save=()=>writeFile(new URL('receipt.json',output),JSON.stringify(receipt,null,2)+'\n');
const shot=label=>page.screenshot({path:new URL(label+'.png',output).pathname,fullPage:true,animations:'disabled'});
async function ask(label,question){
 const before=await page.locator('.assistant-message .answer-prose').count();await page.locator('#research-question').fill(question);
 const pending=page.waitForResponse(r=>r.url().endsWith('/api/v1/chat')&&r.request().method()==='POST',{timeout:600000});
 const start=Date.now();await page.getByRole('button',{name:'Send scientific question'}).click();const response=await pending,body=await response.json();
 await page.locator('.assistant-message .answer-prose').nth(before).waitFor({timeout:600000});
 receipt.workflows.push({label,question,status:response.status(),seconds:(Date.now()-start)/1000,answer:body.answer,citation_count:body.citations?.length,conversation_id:body.conversation_id});await save();await shot(label);
 const citation=page.locator('.assistant-message').last().locator('.citation').first();if(await citation.count()){await citation.click();await page.locator('.original-excerpt').waitFor();await page.keyboard.press('Escape');}console.log(label,response.status(),receipt.workflows.at(-1).seconds);
}
try{
 delete receipt.failure;
 await page.goto('http://127.0.0.1:5173/');await page.locator('#library-status').filter({hasText:'connected'}).waitFor();
 if(!process.argv.includes('--after-solid')) await ask('A-solid-fuel','What limitations does the BASS-II report document for interpreting low-velocity flame-spread observations?');
 await page.goto('http://127.0.0.1:5173/#/investigations?id=psi-25');await page.locator('.record-card').first().waitFor();await shot('A-records');
 await page.getByRole('button',{name:'New conversation',exact:true}).click();
 await ask('B-flex-diagnostics','How do the FLEX backlit, ultraviolet and color-camera diagnostics differ, and what limitations are documented?');
 await ask('B-flex-followup','Which uncertainties are documented for those diagnostics, and which original source supports them?');
 await page.goto('http://127.0.0.1:5173/#/compare?left=psi-10&right=psi-107');await page.locator('#left-record option').first().waitFor({state:'attached'});await page.locator('#right-record option').first().waitFor({state:'attached'});
 await page.getByRole('button',{name:'Compare selected evidence'}).click();await page.locator('.comparison-table').waitFor();receipt.acme_spice_record_comparison=await page.locator('.comparison-table').innerText();await save();await shot('C-acme-spice-records');
 await page.getByRole('tab',{name:'Investigation context'}).click();await page.getByRole('button',{name:'Compare selected evidence'}).click();await page.getByRole('heading',{name:'Registered scientific connections'}).waitFor();await shot('C-acme-spice-context');
 await page.getByRole('button',{name:'New conversation',exact:true}).click();await ask('C-gas-flame','Which documented methods and experimental conditions can be compared between ACME Flame Design and SPICE, and where is evidence insufficient?');
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>document.querySelector('#new-conversation').click());await page.evaluate(()=>document.fonts.ready);await shot('mobile-landing');receipt.mobile_no_horizontal_overflow=await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
}catch(e){receipt.failure=e.message;console.error(e.message);process.exitCode=1;}finally{await save();await browser.close();}
