import { esc, icon, badge, empty, resultCards } from '../ui.js';

const prompts = [
  { tag:'SOLID FUELS', title:'Combustion in low airflow', text:'What limitations does the BASS-II report document for interpreting low-velocity flame-spread observations?', icon:'flame' },
  { tag:'DROPLET DIAGNOSTICS', title:'See what FLEX measured', text:'How do the FLEX backlit, ultraviolet and color-camera diagnostics differ, and what limitations are documented?', icon:'investigations' },
  { tag:'GAS FLAMES', title:'Connect ACME and SPICE', text:'Which documented methods and experimental conditions can be compared between ACME Flame Design and SPICE, and where is evidence insufficient?', icon:'discover' },
];
function answerHTML(answer, citations) {
  // Representation-only backend wording is not researcher-facing product copy.
  return answer.split('\n\n').map(p => {
    p=p.replace(/^The engine retains (.+?) as a (configuration summary|session summary);/, 'Source scope: $1 is a $2;');
    let html = esc(p);
    html = html.replace(/\[(\d+)\]/g, (match,n) => { const c=citations.find(c => c.number===Number(n)); return c ? `<button class="citation" data-evidence="${esc(c.evidence_id)}" aria-label="Open source ${n}">${n}</button>` : match; });
    return `<p>${html.replaceAll('\n','<br>')}</p>`;
  }).join('');
}
function messageHTML(message, index) {
  if (message.role === 'user') return `<article class="user-message"><span class="mono message-label">YOUR QUESTION</span><p>${esc(message.text)}</p></article>`;
  const body=message.body;
  if (!body) return `<div class="error-state" role="alert"><p>${esc(message.text)}</p></div>`;
  const records = [...body.groups.direct,...body.groups.related].filter(r => r.id);
  return `<article class="assistant-message"><div class="answer-label"><span class="answer-mark">${icon('orbit')}</span><span class="eyebrow">EVIDENCE-GROUNDED RESPONSE</span></div>${body.excerptsOnly ? '<div class="scope-note">Original excerpts are shown where a full explanation is unavailable.</div>' : ''}<div class="answer-prose">${answerHTML(body.answer,body.citations)}</div>
  <div class="answer-toolbar"><button class="text-button" data-show-sources="${index}">${icon('evidence')} ${body.citations.length} source references</button>${records[0] ? `<button class="text-button" data-entity="${esc(records[0].id)}">Open research record ${icon('arrow')}</button><button class="text-button" data-compare-record="${esc(records[0].id)}">Compare record ${icon('compare')}</button>` : ''}</div>
  <div class="answer-sources" id="sources-${index}" hidden>${body.citations.map(c=>`<button class="source-reference" data-evidence="${esc(c.evidence_id)}"><span class="source-number">${c.number}</span><span><strong>${esc(c.source?.title || c.document_id)}</strong><small>${esc(c.source?.source_type || 'Registered source')}${c.page ? ' · PDF page '+c.page : ''}</small></span>${icon('chevron')}</button>`).join('')}</div>
  <details class="evidence-details"><summary>Explore the retrieved evidence</summary>${resultCards(body.groups,4) || '<p>No additional evidence groups were returned.</p>'}</details>
  ${body.suggestions.filter(s=>s.query || s.question).length ? `<div class="followups"><span class="eyebrow">NEXT RESEARCH PATHS</span>${body.suggestions.filter(s=>s.query || s.question).slice(0,3).map(s=>`<button data-ask="${esc(s.query || s.question)}">${badge('EXPLORATORY')}<span>${esc(s.query || s.question)}</span>${icon('arrow')}</button>`).join('')}</div>` : ''}</article>`;
}
export async function renderAssistant(ctx) {
  const session=ctx.state.session;
  const active=session.messages.length>0;
  ctx.view(`<div class="assistant-layout ${active ? 'has-conversation' : ''}"><div class="conversation" id="conversation" aria-live="polite">
  ${active ? session.messages.map(messageHTML).join('') : `<section class="assistant-welcome"><div class="orbital-art" aria-hidden="true"><i></i><i></i><i></i><span></span></div><span class="eyebrow orange">MICROGRAVITY COMBUSTION · SCIENTIFIC RESEARCH</span><h1>A better question.<br><span>A clearer understanding.</span></h1><p>Explore what the research actually shows. Ask a question, follow the experimental context, and trace every finding back to its source.</p><div class="welcome-tags"><span>${icon('check')} Original NASA sources</span><span>${icon('discover')} Connected scientific knowledge</span></div></section><div class="prompt-grid">${prompts.map(p=>`<button class="prompt-card" data-ask="${esc(p.text)}"><span class="prompt-icon">${icon(p.icon)}</span><span class="eyebrow">${p.tag}</span><strong>${p.title}</strong><span class="prompt-description">${esc(p.text)}</span>${icon('arrow','prompt-arrow')}</button>`).join('')}</div>`}
  ${ctx.state.chatBusy ? `<div class="chat-loading" role="status"><span class="loader"></span><div><strong id="chat-progress">${esc(ctx.state.chatProgress || "Preparing your question")}</strong><p>Source context can take a few minutes to review. You can browse while this continues.</p></div><button class="text-button" id="stop-waiting">Cancel question</button></div>` : ''}</div>
  <div class="composer-wrap"><form class="composer" id="question-form"><label for="research-question" class="sr-only">Ask a scientific question</label><textarea id="research-question" name="question" rows="2" maxlength="12000" placeholder="Ask about an experiment, a measurement, or a documented finding…" ${ctx.state.chatBusy ? 'disabled' : ''}></textarea><div class="composer-bottom"><span>${icon('evidence')} Grounded in the research library</span><div><label class="detail-select"><span class="sr-only">Answer detail</span><select name="detail"><option value="standard">Standard detail</option><option value="concise">Concise</option><option value="technical">Technical detail</option></select></label><button class="send-button" type="submit" aria-label="Send scientific question" ${ctx.state.chatBusy ? 'disabled' : ''}>${icon('arrow')}</button></div></div></form><p class="composer-note">Evidence can be incomplete. Related research is not equivalent evidence. <button class="inline-button" data-classifications>Understand the evidence labels</button></p></div></div>`);
  const form=ctx.root.querySelector('#question-form');
  form.addEventListener('submit', e=>{e.preventDefault();const f=new FormData(form);send(String(f.get('question')||'').trim(),String(f.get('detail')));});
  ctx.root.querySelector('#research-question').addEventListener('keydown',e=>{if(e.key==='Enter' && !e.shiftKey){e.preventDefault();form.requestSubmit();}});
  ctx.root.querySelectorAll('[data-show-sources]').forEach(button=>button.onclick=()=>{const panel=ctx.root.querySelector('#sources-'+button.dataset.showSources);panel.hidden=!panel.hidden;button.setAttribute('aria-expanded',String(!panel.hidden));});
  ctx.root.querySelector('#stop-waiting')?.addEventListener('click',()=>{ctx.state.chatController?.abort();ctx.state.chatController=null;ctx.state.chatBusy=false;ctx.state.chatProgress=null;session.messages.push({role:'assistant',text:'Cancellation requested. The active review will stop at the next safe checkpoint. You can submit a new question now; it may wait in the queue.'});ctx.save();ctx.rerender();});
  if (ctx.state.pendingQuestion && !ctx.state.chatBusy) { const question=ctx.state.pendingQuestion;ctx.state.pendingQuestion='';send(question,'standard'); }
  async function send(question,detail) {
    if (!question || ctx.state.chatBusy) return;
    session.messages.push({role:'user',text:question});ctx.state.chatBusy=true;
    const controller=new AbortController();ctx.state.chatController=controller;
    ctx.save();ctx.rerender();
    try {
      const result=await (ctx.chatAPI || ctx.api).chat({message:question,detail, max_queries:2,evidence_limit:12,max_output_tokens:3000,...(session.id ? {conversation_id:session.id} : {})},controller.signal,progress=>{
        if(ctx.state.chatController!==controller)return;
        const labels={retrieval:'Finding source evidence',generation:'Preparing a source-backed explanation',verification:'Checking statements against their sources',context:'Reviewing experimental context',publishing:'Finalizing the response'};
        ctx.state.chatProgress=progress.status==='queued' ? 'Question queued · position '+progress.queue_position : progress.status==='cancellation_requested' ? 'Cancellation pending · finishing the current review stage' : labels[progress.stage] || 'Consulting the scientific evidence';
        const node=ctx.root.querySelector('#chat-progress');if(node && ctx.state.session===session)node.textContent=ctx.state.chatProgress;
      });
      if(controller.signal.aborted || ctx.state.chatController!==controller || ctx.state.session!==session)return;
      session.id=result.conversationId;session.messages.push({role:'assistant',body:result});
    } catch(error) {
      if(ctx.state.chatController!==controller || ctx.state.session!==session)return;
      if (error.name==='AbortError') session.messages.push({role:'assistant',text:'Cancellation requested. The review stops at the next safe checkpoint. New questions can wait in the queue.'});
      else { if(error.status===404) session.id=null;session.messages.push({role:'assistant',text:error.message}); }
    } finally { if(ctx.state.chatController===controller){ctx.state.chatBusy=false;ctx.state.chatController=null;ctx.state.chatProgress=null;ctx.save();if(ctx.state.routeKey.startsWith("assistant?"))ctx.rerender();} }
  }
  if(active) {
    const focus=ctx.state.chatBusy ? ctx.root.querySelector('.chat-loading') : [...ctx.root.querySelectorAll('.assistant-message')].at(-1);
    (focus || ctx.root.querySelector('.composer-wrap'))?.scrollIntoView({block:'start',behavior:'instant'});
  }
}
