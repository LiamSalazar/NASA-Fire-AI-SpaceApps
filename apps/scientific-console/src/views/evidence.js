import { safeURL } from '../api.js';
import { esc, human, icon, badge, loading, empty, errorState, pageHeading, option, resultCards } from '../ui.js';
export async function renderEvidence(ctx) {
  ctx.view(pageHeading('ORIGINAL SOURCES','Evidence, within reach','Inspect the original source behind a scientific statement. Search passages or browse the registered source collection.')+
    `<form class="evidence-search panel" id="evidence-search"><label for="evidence-query">Search original evidence</label><div class="search-row"><span>${icon('search')}</span><input id="evidence-query" name="query" maxlength="12000" required placeholder="A scientific question, a document identifier, or a source title" value="${esc(ctx.params.query || '')}"><button class="button primary">Search evidence ${icon('arrow')}</button></div></form><div id="evidence-search-results"></div><section class="source-collection"><div class="section-heading"><div><span class="eyebrow">SOURCE COLLECTION</span><h2>From the original record</h2></div><span class="small muted" id="source-page-label"></span></div><div id="source-library">${loading('Opening the source collection…')}</div></section>`);
  const form=ctx.root.querySelector('#evidence-search');
  async function search(query) {
    const fresh=ctx.latest("search");
    const host=ctx.root.querySelector('#evidence-search-results');host.innerHTML=loading('Retrieving source-backed evidence…');
    try {
      const exact=query.length<=500 ? await fresh.api.resolve(query) : {identifier:false};
      if(!ctx.active() || !fresh())return;
      if(exact.identifier){
        host.innerHTML=`<div class="section-heading"><h2>Registered identifier matches</h2><span>${exact.total} matches</span></div><p class="scope-note">Identity lookup preserves the registered source. A matching identifier does not establish direct support for a scientific claim.</p>${exact.items.map(item=>`<article class="result-card"><span class="eyebrow">${esc(human(item.kind))}</span><h3>${esc(item.title || item.source?.title || item.evidence_id || item.id)}</h3><p class="mono small">${esc(item.source_id || item.evidence_id || item.id)}</p><div class="card-actions">${item.evidence_id || item.evidence_ids?.[0] ? `<button class="text-button" data-evidence="${esc(item.evidence_id || item.evidence_ids[0])}">Inspect registered evidence ${icon('evidence')}</button>` : ''}${item.id ? `<button class="text-button" data-graph-entity="${esc(item.id)}">Explore registered relations ${icon('discover')}</button>` : ''}${safeURL(item.url) ? `<a class="text-button" href="${esc(safeURL(item.url))}" target="_blank" rel="noopener noreferrer">Original source ${icon('external')}</a>` : ''}</div></article>`).join('') || empty('Identifier not registered','Check the exact identifier. No related source has been substituted.')}`;return;
      }
      const groups=await fresh.api.search(query);if(!ctx.active() || !fresh())return;const count=Object.values(groups).reduce((n,v)=>n+v.length,0);
      host.innerHTML=`<div class="section-heading"><h2>Evidence for your question</h2><span class="mono small muted">${count} RETURNED ITEMS</span></div><div class="classification-key">${['DIRECT','RELATED','DOCUMENTARY','DISCOVERY'].map(c=>badge(c)).join('')}<button class="text-button" data-classifications>What do these labels mean?</button></div>${resultCards(groups,20) || empty('No evidence returned','Refine the question or browse original sources. This is not evidence of a NASA-wide knowledge gap.')}`;
    }catch(e){if(ctx.active())host.innerHTML=errorState(e);}
  }
  form.onsubmit=e=>{e.preventDefault();search(String(new FormData(form).get('query')).trim());};
  async function library(offset=0){
    const fresh=ctx.latest("library");
    const host=ctx.root.querySelector('#source-library');host.innerHTML=loading('Opening the source collection…');
    try {const page=await fresh.api.catalog({offset,limit:12});const sources=await Promise.all(page.items.map(item=>fresh.api.source(item.source_id).catch(()=>({title:'Source metadata unavailable',source_type:'Registered reference'}))));if(!ctx.active() || !fresh())return;
      ctx.root.querySelector('#source-page-label').textContent=`${offset+1}–${Math.min(offset+12,page.total)} of ${page.total} registered sources`;
      host.innerHTML=`<div class="source-grid">${sources.map(s=>`<article class="source-card"><div class="source-card-icon">${icon('evidence')}</div><span class="eyebrow">${esc(human(s.source_type || 'Registered source'))}</span><h3>${esc(s.title || 'Title not recorded')}</h3>${s.nasa_id ? `<p class="small mono muted">${esc(s.nasa_id)}</p>` : ''}<div class="card-actions">${s.title && s.source_type!=='Registered reference' ? `<button class="text-button" data-evidence-query="${esc(s.nasa_id || s.title)}">Find passages ${icon('search')}</button>` : ''}${s.url ? `<a class="text-button" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">Original source ${icon('external')}</a>` : '<span class="small muted">No original URL registered</span>'}</div></article>`).join('')}</div><div class="pagination"><button class="button secondary" id="sources-prev" ${offset===0?'disabled':''}>Previous</button><span>${offset+1}–${Math.min(offset+12,page.total)} of ${page.total}</span><button class="button secondary" id="sources-next" ${offset+12>=page.total?'disabled':''}>Next ${icon('arrow')}</button></div><p class="small muted">The collection includes original documents, table records and bibliographic or catalogue references. A listed reference is not proof that its full text supports a finding.</p>`;
      host.querySelector('#sources-prev').onclick=()=>library(Math.max(0,offset-12));host.querySelector('#sources-next').onclick=()=>library(offset+12);
    }catch(e){if(ctx.active()){host.innerHTML=errorState(e);host.querySelector('[data-retry]').onclick=()=>library(offset);}}
  }
  if(ctx.params.query) await search(ctx.params.query);
  await library();
}
