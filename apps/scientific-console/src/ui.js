export const esc = (v = '') => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const human = (v = '') => String(v).replace(/^source:/, '').replace(/([a-z])([A-Z])/g, '$1 $2').replaceAll('_',' ').replace(/^./, c => c.toUpperCase());
export const categories = {
  DIRECT: 'Original experimental evidence that matches the requested scientific constraints.',
  RELATED: 'A documented scientific association. Similarities do not establish experimental equivalence.',
  DOCUMENTARY: 'Original descriptions, methods, objectives, attributed findings or limitations.',
  DISCOVERY: 'A retrieved source candidate. Relevance to this question has not been established.',
  EXPLORATORY: 'A question or research path to investigate, not a verified finding.',
};
export const badge = (category) => categories[category] ? `<span class="badge ${category.toLowerCase()}" title="${esc(categories[category])}">${esc(category)}</span>` : '';
export const icon = (name, cls = '') => {
  const paths = {
    assistant:'<path d="M7 4h10a3 3 0 0 1 3 3v7a3 3 0 0 1-3 3h-5l-5 4v-4a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3Z"/><path d="m9 10 2 2 4-4"/>',
    investigations:'<path d="M9 3h6M10 3v6L5 18a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M8 14h8"/>',
    compare:'<path d="M4 4v16M20 4v16M4 8h6M14 16h6m-13-5 3-3-3-3m10 8-3 3 3 3"/>',
    discover:'<circle cx="12" cy="12" r="3"/><circle cx="4" cy="5" r="2"/><circle cx="20" cy="5" r="2"/><circle cx="4" cy="19" r="2"/><circle cx="20" cy="19" r="2"/><path d="m6 6 4 4m4 0 4-4M6 18l4-4m4 0 4 4"/>',
    evidence:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Zm0 0v6h6M8 13h8M8 17h6"/>',
    arrow:'<path d="M4 12h15m-6-6 6 6-6 6"/>', search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
    plus:'<path d="M12 5v14M5 12h14"/>', close:'<path d="m6 6 12 12M18 6 6 18"/>',
    external:'<path d="M14 3h7v7m0-7L10 14M10 4H5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-5"/>',
    chevron:'<path d="m9 5 7 7-7 7"/>', menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
    check:'<path d="m5 12 4 4 10-10"/>', orbit:'<ellipse cx="12" cy="12" rx="11" ry="5" transform="rotate(-35 12 12)"/><circle cx="12" cy="12" r="4"/>',
    flame:'<path d="M13 2c2 6-3 7-1 11 2-1 3-3 3-5 5 5 6 8 3 12-3 4-11 3-13-2C3 12 10 9 13 2Z"/>',
  };
  return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.orbit}</svg>`;
};
export const loading = (message = 'Opening the research library…') => `<div class="loading" role="status"><span class="loader"></span><span>${esc(message)}</span></div>`;
export const empty = (title, body, action = '') => `<div class="empty-state">${icon('orbit')}<h3>${esc(title)}</h3><p>${esc(body)}</p>${action}</div>`;
export const errorState = (error) => `<div class="error-state" role="alert"><h3>Unable to open this research</h3><p>${esc(error.message)}</p><button class="button secondary" data-retry>Try again ${icon('arrow')}</button></div>`;
export const evidenceButton = (id, text = 'Open evidence') => id ? `<button class="text-button" data-evidence="${esc(id)}">${esc(text)} ${icon('chevron')}</button>` : '';
export const pageHeading = (eyebrow, title, body, action = '') => `<header class="page-heading"><div><span class="eyebrow">${esc(eyebrow)}</span><h1>${esc(title)}</h1><p>${esc(body)}</p></div>${action}</header>`;
export const option = (value, label, selected = '') => `<option value="${esc(value)}" ${String(value) === String(selected) ? 'selected' : ''}>${esc(label)}</option>`;
export function sourceText(e) {
  if (!e.text?.trim().startsWith('{')) return e.text || '';
  try { const v = JSON.parse(e.text); return ['title','description','abstract','text','objectives'].map(k => typeof v[k] === 'string' ? v[k] : '').filter(Boolean).join('\n\n') || 'This is a catalogue entry. Open the original source to inspect its recorded metadata.'; }
  catch { return 'Open the original source to inspect this catalogue entry.'; }
}
export function recordLabel(r) {
  const parts=[r.record?.reported_identifier, r.record?.reported_material_description];
  const fields=(r.fields || []).filter(f=>!['',null,undefined].includes(f.qualifiers?.original_value ?? f.value?.reported_value));
  const priority=f=> /fuel|material|test|session|experiment|date|oxygen|pressure|flow|temperature/i.test(f.qualifiers?.source_header || f.property_id);
  for(const f of fields.filter(priority).slice(0,3))parts.push(fieldLabel(f)+': '+fieldValue(f));
  if(!parts.some(Boolean))for(const f of fields.slice(0,2))parts.push(fieldLabel(f)+': '+fieldValue(f));
  const row=r.evidence?.[0]?.structured_location?.row_ordinal;
  return [...new Set(parts.filter(Boolean))].join(' · ') || r.title || human(r.classes?.[0] || 'Source record')+(row ? ' · row '+row : '');
}
export function fieldLabel(f) { return f.qualifiers?.source_header || human(f.property_id); }
export function fieldValue(f) {
  const raw = f.qualifiers?.original_value;
  if (raw !== undefined && raw !== null) return raw === '' ? 'Not recorded' : String(raw);
  const v = f.value || {}; const value = v.raw_expression ?? v.reported_value;
  return value === null || value === undefined || value === '' ? 'Not recorded' : String(value) + (v.reported_unit ? ' ' + v.reported_unit : '');
}
export function fieldRole(f) {
  const role = f.qualifiers?.scientific_role || f.qualifiers?.modality;
  if (/derived|calculated|predicted|simulat/.test(role || '')) return 'Calculated or derived field';
  if (f.relationship === 'hasMeasurement') return 'Reported measurement';
  if (f.relationship === 'hasCondition') return 'Reported condition';
  return 'Reported field';
}
export function titleOf(item) { return item.payload?.title || item.payload?.reported_identifier || item.source?.title || item.document_id || item.id || 'Source record'; }
export function resultCards(groups, max = 8) {
  return Object.entries(groups).map(([type, rows]) => !rows.length ? '' : `<section class="result-group"><div class="section-heading"><h3>${human(type)} evidence</h3><span class="muted mono">${rows.length} returned</span></div><p class="small muted">${esc(categories[type.toUpperCase()])}</p><div class="result-list">${rows.slice(0, max).map(row => `<article class="result-card">${badge(row.category || type.toUpperCase())}<h4>${esc(titleOf(row))}</h4>${row.payload?.reported_material_description ? `<p>${esc(row.payload.reported_material_description)}</p>` : ''}${row.text ? `<p class="excerpt">${esc(sourceText(row).slice(0,360))}</p>` : ''}<div class="card-actions">${evidenceButton(row.evidence_id || row.evidence?.[0]?.evidence_id)}${row.id ? `<button class="text-button" data-entity="${esc(row.id)}">Explore record ${icon('arrow')}</button>` : ''}</div></article>`).join('')}</div></section>`).join('');
}

/** A canonical property can cover several printed source columns. Keep that distinction. */
export function comparisonLabel(propertyId, fields) {
  const headers=[...new Set(fields.filter(f=>f.property_id===propertyId).map(f=>f.qualifiers?.source_header).filter(Boolean))];
  return headers.length===1 ? headers[0] : human(propertyId);
}
