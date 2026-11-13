import { test, expect } from '@playwright/test';

const output='../../artifacts/product_finalize_20261113/screenshots';
test('exact source identities, unknown identifiers and all five responsive views',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/#/evidence?query=PSI-100');
  await expect(page.getByRole('heading',{name:'Registered identifier matches'})).toBeVisible();
  await expect(page.locator('#evidence-search-results')).toContainText('psi-100');
  await page.locator('#evidence-search-results [data-evidence]').first().click();
  await expect(page.locator('.original-excerpt')).toBeVisible();await page.keyboard.press('Escape');
  await page.locator('#evidence-query').fill('PSI-9999999');await page.getByRole('button',{name:'Search evidence',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Identifier not registered'})).toBeVisible();
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:1000});
    for(const view of ['assistant','investigations','compare','discover','evidence']){
      await page.goto('/#/'+view);
      await expect(page.locator('main .loading')).toHaveCount(0,{timeout:120000});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
      await expect(page.locator('.sidebar .source-principle,#library-status,#library-counts')).toHaveCount(0);
      await page.screenshot({path:`${output}/${view}-${width}.png`,fullPage:true,animations:'disabled'});
    }
  }
  expect(errors).toEqual([]);
});

test('cancel creation, start a new conversation and discard the abandoned response',async({page})=>{
  let release;const held=new Promise(resolve=>release=resolve);let created;const began=new Promise(resolve=>created=resolve);let once=true;
  await page.route('**/api/v1/chat/operations',async route=>{
    if(!once || route.request().method()!=='POST')return route.continue();
    once=false;const response=await route.fetch();created(await response.json());await held;await route.fulfill({response});
  });
  await page.goto('/#/assistant');
  await page.locator('#research-question').fill('Saffire-III sample S1 airflow');await page.getByRole('button',{name:'Send scientific question'}).click();
  const abandoned=await began;
  // These routes use real scientific backend data during the in-flight request.
  await page.getByRole('link',{name:'Investigations',exact:true}).click();
  await expect(page.locator('.investigation-card').first()).toBeVisible();
  await page.getByRole('button',{name:'New conversation',exact:true}).click();
  await expect(page.locator('#research-question')).toBeEnabled();
  release();
  await page.locator('#research-question').fill('Saffire-III sample S2 airflow');await page.getByRole('button',{name:'Send scientific question'}).click();
  await expect(page.locator('.assistant-message .answer-prose')).toHaveCount(1,{timeout:180000});
  await expect(page.locator('.user-message')).toHaveCount(1);
  await expect(page.locator('.user-message')).toContainText('sample S2');
  const previous=await page.request.get('/api/v1/chat/operations/'+abandoned.operation_id);
  expect(['canceled','completed']).toContain((await previous.json()).status);
});

test('obsolete filter response cannot replace newer results',async({page})=>{
  let release;const held=new Promise(resolve=>release=resolve);let entered;const began=new Promise(resolve=>entered=resolve);
  await page.route('**/api/v1/research/investigations?**',async route=>{
    if(!new URL(route.request().url()).searchParams.get('query')?.includes('Saffire'))return route.continue();
    const response=await route.fetch();entered();await held;try{await route.fulfill({response});}catch{/* Aborted obsolete request. */}
  });
  await page.goto('/#/investigations');await expect(page.locator('.investigation-card').first()).toBeVisible();
  await page.getByRole('textbox',{name:'Search investigations'}).fill('Saffire');await page.getByRole('button',{name:'Apply filters'}).click();await began;
  await page.getByRole('textbox',{name:'Search investigations'}).fill('unmatched violet apparatus');await page.getByRole('button',{name:'Apply filters'}).click();
  await expect(page.getByRole('heading',{name:'No investigations match these filters'})).toBeVisible();release();
  await expect(page.locator('.investigation-card')).toHaveCount(0);
});
