/** Explicitly validated transport. Only scientific presentation fields enter UI state. */
export class ResearchError extends Error {
  constructor(message, status = 0) { super(message); this.status = status; }
}
const array = (v) => Array.isArray(v) ? v : [];
const object = (v) => v && typeof v === 'object' && !Array.isArray(v);
const requireShape = (v, test) => { if (!object(v) || !test(v)) throw new ResearchError('The library returned an unreadable response. Please retry.'); return v; };
export function safeURL(value) {
  try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) ? u.href : null; } catch { return null; }
}
export function sourceView(s = {}) { s = s || {}; return { title: s.title, source_id: s.source_id, source_type: s.source_type, nasa_id: s.nasa_id, url: safeURL(s.url), doi: s.doi }; }
export function evidenceView(e = {}) {
  return { evidence_id: e.evidence_id, document_id: e.document_id, page: e.page, section: e.section,
    text: e.text, source: sourceView(e.source), category: e.category,
    structured_location: e.structured_location,
    source_cells: array(e.source_cells).map(c => ({ original_header: c.original_header, original_value: c.original_value, row_ordinal: c.row_ordinal })),
    number: e.number, supporting_passage: e.supporting_passage,
    supports: array(e.supports).map(s => ({ claim_text: s.claim_text, passage: s.passage, category: s.category, support_role: s.support_role, evidence_id: s.evidence_id })) };
}
function itemView(r = {}) {
  if (r.evidence_id) return evidenceView(r);
  return { id: r.id, category: r.category, classes: array(r.classes), payload: { title: r.payload?.title, reported_identifier: r.payload?.reported_identifier, reported_material_description: r.payload?.reported_material_description },
    evidence: array(r.evidence).map(evidenceView), constraints: array(r.constraints), reason_not_direct: r.reason_not_direct };
}
function chatView(v) {
  requireShape(v, v => typeof v.answer === 'string' && typeof v.conversation_id === 'string' && Array.isArray(v.citations) && object(v.evidence_groups));
  return { answer: v.answer, conversationId: v.conversation_id, citations: v.citations.map(evidenceView),
    groups: Object.fromEntries(['direct', 'related', 'documentary', 'discovery'].map(k => [k, array(v.evidence_groups[k]).map(itemView)])),
    suggestions: array(v.discovery_suggestions).map(s => ({ query: s.query, question: s.question, label: s.label })),
    excerptsOnly: v.generation_status?.explanation_status === 'EXTRACTIVE_FALLBACK' };
}
export function createAPI(base = '/api/v1', cache = new Map(), scopeSignal) {
  if (!base.startsWith('/') && !safeURL(base)) throw new ResearchError('Invalid research library address.');

  async function request(path, { body, signal, cacheable = true } = {}) {
    signal ||= scopeSignal;
    if (signal?.aborted) throw new DOMException("Request canceled", "AbortError");
    const key = base + path;
    if (!body && cacheable && cache.has(key)) return cache.get(key);
    const execute = async () => {
      if (signal?.aborted) throw new DOMException('Stopped waiting', 'AbortError');
      let response;
      try { response = await fetch(key, { method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined, signal }); }
      catch (e) { if (e.name === 'AbortError') throw e; throw new ResearchError('The research library could not be reached. Check the connection and retry.'); }
      if (!response.ok) {
        const messages = { 404: 'This record or conversation is no longer available.', 422: 'Please check the selected records or question.', 429: 'The library is reviewing another question. Please try again shortly.', 503: 'The research library is temporarily unavailable. Please try again.' };
        throw new ResearchError(path==='/chat/operations' && response.status===503 ? 'The question queue is full. Please try again shortly; source browsing remains available.' : messages[response.status] || 'The request could not be completed. Please retry.', response.status);
      }
      const data = await response.json();
      if (!object(data)) throw new ResearchError('The library returned an unreadable response.');
      if (!body && cacheable) { cache.set(key, data); if (cache.size > 100) cache.delete(cache.keys().next().value); }
      return data;
    };
    return execute();
  }
  const page = (v) => requireShape(v, v => Array.isArray(v.items) && Number.isInteger(v.total));
  const qs = (params) => new URLSearchParams(Object.entries(params).filter(([,v]) => v !== '' && v !== null && v !== undefined)).toString();
  return {
    scoped: signal => createAPI(base, cache, signal),
    resolve: query => request("/resolve?" + qs({query})),
    overview: async () => requireShape(await request('/research/overview'), v => Number.isInteger(v.investigations) && object(v.facets) && Array.isArray(v.properties)),
    investigations: async (params = {}) => page(await request('/research/investigations?' + qs(params))),
    investigation: async id => requireShape(await request('/research/investigations/' + encodeURIComponent(id)), v => typeof v.id === 'string' && Array.isArray(v.sections)),
    entity: async id => requireShape(await request('/research/entities/' + encodeURIComponent(id)),v=>typeof v.id==='string' && typeof v.title==='string' && Array.isArray(v.classes) && Array.isArray(v.evidence_ids)),
    neighbors: async (id, params = {}) => requireShape(await request('/research/entities/' + encodeURIComponent(id) + '/neighbors?' + qs(params)), v => Array.isArray(v.nodes) && Array.isArray(v.edges)),
    records: async (params) => { const v=page(await request('/records?' + qs(params))); return requireShape(v, v=>v.items.every(r=>object(r) && typeof r.id==='string' && Array.isArray(r.classes) && object(r.record) && Array.isArray(r.fields) && Array.isArray(r.evidence) && r.fields.every(f=>object(f) && typeof f.property_id==='string' && object(f.value) && Array.isArray(f.evidence_ids)))); },
    evidence: async id => evidenceView(requireShape(await request('/evidence/' + encodeURIComponent(id)), v => typeof v.evidence_id === 'string' && typeof v.text === 'string')),
    source: async id => sourceView(await request('/sources/' + encodeURIComponent(id))),
    catalog: async (params = {}) => page(await request('/catalog?' + qs(params))),
    search: async query => { const v = requireShape(await request('/search', { body: { query, limit: 20, research: true } }), v => ['direct','related','documentary','discovery'].every(k => Array.isArray(v[k]))); return Object.fromEntries(['direct','related','documentary','discovery'].map(k => [k, v[k].map(itemView)])); },
    chat: async (body, signal, progress = () => {}) => {
      // Creation must finish so that even an immediate browser abort can cancel
      // the actual server operation rather than orphaning an unknown job.
      const op = await request('/chat/operations', { body, signal: undefined, cacheable: false });
      let done = false;
      const cancel = () => fetch(base + '/chat/operations/' + op.operation_id + '/cancel', {method:'POST', keepalive:true});
      const abort = () => { void cancel().catch(() => {}); };
      signal?.addEventListener('abort', abort, {once:true});
      try {
        while (true) {
          if (signal?.aborted) { await cancel(); throw new DOMException('Question canceled', 'AbortError'); }
          const state = await request('/chat/operations/' + op.operation_id, {signal, cacheable:false});
          progress(state);
          if (state.status === 'completed') { done=true; return chatView(state.result); }
          if (state.status === 'failed') { done=true; throw new ResearchError(state.error?.message || 'The question could not be completed. Please retry.', state.error?.status); }
          if (state.status === 'canceled') { done=true; throw new DOMException('Question canceled', 'AbortError'); }
          await new Promise(resolve => { const timer=setTimeout(finish,700); function finish(){clearTimeout(timer);signal?.removeEventListener('abort',finish);resolve();} signal?.addEventListener('abort',finish,{once:true}); });
        }
      } finally { signal?.removeEventListener('abort',abort); if (!done) void cancel().catch(() => {}); }
    },
    compareInvestigations: async (subjects, dimensions) => requireShape(await request('/research/investigation-comparison', { body: { subjects, dimensions } }), v => Array.isArray(v.rows) && Array.isArray(v.subjects)),
    compareRecords: async (subjects, dimensions) => requireShape(await request('/comparisons', { body: { subjects, dimensions } }), v => Array.isArray(v.matrix)),
  };
}
