import { esc, human, fieldLabel, fieldValue, fieldRole, empty, evidenceButton, recordLabel } from './ui.js';

/** Group only compatible reported scalars. Never interpolate or mix temporal roles. */
export function measurementGroups(records) {
  const groups = new Map();
  for (const record of records) for (const field of record.fields || []) {
    if (!['hasMeasurement','hasCondition'].includes(field.relationship)) continue;
    if (/derived|calculated|simulat|predicted/.test(field.qualifiers?.scientific_role || field.qualifiers?.modality || '')) continue;
    const value = field.value;
    if (!value || typeof value.reported_value !== 'number' || !Number.isFinite(value.reported_value) || value.lower != null || value.upper != null) continue;
    const unit = value.reported_unit;
    if (!unit || !field.evidence_ids?.length) continue;
    const key = JSON.stringify([field.property_id, unit, field.qualifiers?.context || 'reported', field.relationship]);
    if (!groups.has(key)) groups.set(key, { key, label: fieldLabel(field), unit, role: fieldRole(field), points: [] });
    groups.get(key).points.push({ value: value.reported_value, printed: fieldValue(field), approximate: !!value.approximate,
      record: recordLabel(record), recordId: record.id, evidenceId: field.evidence_ids[0], field });
  }
  return [...groups.values()].filter(g => g.points.length > 0);
}
export function measurementChart(group) {
  if (!group) return empty('No compatible values to plot', 'Charts appear only when source-backed scalar measurements or conditions with recorded units are available.');
  const points = group.points.slice(0, 16);
  const min = Math.min(0, ...points.map(p => p.value));
  const max = Math.max(0, ...points.map(p => p.value));
  const span = max - min || 1;
  const y = v => 205 - (v - min) / span * 155;
  const zero = y(0); const step = 480 / points.length;
  return `<div class="chart-heading"><div><h3>${esc(group.label)}</h3><p class="small muted">${esc(group.role)} · ${esc(group.unit)}</p></div><span class="mono small">${points.length} source records</span></div>
    <svg class="measurement-chart" viewBox="0 0 580 260" role="img" aria-label="${esc(group.label)} in ${esc(group.unit)} by source record. Each bar opens its original evidence.">
    ${[0,.25,.5,.75,1].map(t => { const value = min + span*t; const yy=y(value); return `<line x1="65" y1="${yy}" x2="555" y2="${yy}" stroke="var(--border)"/><text x="55" y="${yy+4}" text-anchor="end" class="axis">${Number(value.toPrecision(4))}</text>`; }).join('')}
    ${points.map((p,i) => { const x=75+i*step, yy=y(p.value); return `<g tabindex="0" role="button" data-evidence="${esc(p.evidenceId)}" aria-label="${esc(p.record)}: ${esc(p.printed)} ${esc(group.unit)}. Open source."><title>${esc(p.record)} · ${esc(p.printed)} ${esc(group.unit)}${p.approximate ? ' (approximate)' : ''}</title><rect class="data-bar" x="${x}" y="${Math.min(zero,yy)}" width="${Math.max(3, step-12)}" height="${Math.max(3,Math.abs(zero-yy))}" rx="3"/><text x="${x+Math.max(3,step-12)/2}" y="232" text-anchor="middle" class="axis">${esc(String(p.record).slice(0,8))}</text></g>`; }).join('')}
    </svg><p class="chart-note">Source values from the current record page. Click or focus a bar to open its evidence. Approximate entries retain their source qualifier. No interpolation or trend is inferred.</p>`;
}
export function relationshipGraph(data) {
  const center = data.center;
  const others = data.nodes.filter(n => n.id !== center.id).slice(0, 8);
  if (!others.length) return empty('No registered neighbors here', 'Try another entity. An absent connection in this library is not a NASA knowledge gap.');
  const coords = new Map([[center.id, [300,215]]]);
  others.forEach((n,i) => { const angle = -Math.PI/2 + i/others.length * Math.PI*2; coords.set(n.id,[300+230*Math.cos(angle),215+155*Math.sin(angle)]); });
  const edges = data.edges.filter(e => coords.has(e.from) && coords.has(e.to));
  return `<div class="relationship-canvas"><svg viewBox="0 0 600 430" aria-hidden="true"><defs><marker id="edge-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#5285b2"/></marker></defs>${edges.map(e => { const [x,y]=coords.get(e.from),[xx,yy]=coords.get(e.to);return `<line x1="${x}" y1="${y}" x2="${xx}" y2="${yy}" stroke="#325876" stroke-width="1" marker-end="url(#edge-arrow)"/>`;}).join('')}</svg>
    ${[center,...others].map(n => { const [x,y]=coords.get(n.id);return `<button class="graph-node ${n.id === center.id ? 'central' : ''}" style="left:${x/6}%;top:${y/4.3}%" data-graph-entity="${esc(n.id)}" title="${esc(n.title)}"><span class="node-dot"></span><strong>${esc(n.title.slice(0,66))}</strong><span>${esc(human(n.classes[0] || 'Scientific entity'))}</span></button>`; }).join('')}
    </div><p class="chart-note">Every line is a registered relationship. Arrows preserve its direction. Select a node to explore its connections; connectivity does not establish causality.</p><div class="edge-list">${edges.map(e => `<div><span>${esc(human(e.relation))}</span>${evidenceButton(e.evidence_ids[0], 'Relationship evidence')}</div>`).join('')}</div>`;
}
