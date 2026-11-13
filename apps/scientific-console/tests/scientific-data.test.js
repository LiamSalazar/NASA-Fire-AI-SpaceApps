import test from 'node:test';
import assert from 'node:assert/strict';
import { fieldValue, comparisonLabel } from '../src/ui.js';
import { measurementGroups } from '../src/visualizations.js';
import { safeURL, evidenceView } from '../src/api.js';

test('source expressions, missing fields and zero are distinct',()=>{
  assert.equal(fieldValue({qualifiers:{original_value:'0'}}),'0');
  assert.equal(fieldValue({qualifiers:{original_value:''}}),'Not recorded');
  assert.equal(fieldValue({qualifiers:{original_value:'RAMPED'}}),'RAMPED');
  assert.equal(fieldValue({qualifiers:{original_value:'~7.4 mm'},value:{canonical_value:.0074}}),'~7.4 mm');
});
const field=(value,unit,context='initial',role='reported_condition')=>({property_id:'invented:width',relationship:'hasCondition',evidence_ids:['invented-source'],qualifiers:{context,scientific_role:role,source_header:'Violet width'},value:{reported_value:value,reported_unit:unit}});
const record=fields=>({record:{reported_identifier:'Violet 7'},fields});
test('plots retain original units, temporal context and evidence',()=>{
  const groups=measurementGroups([record([field(7,'mm'),field(12,'cm'),field(7,'mm','final')])]);
  assert.equal(groups.length,3);
  assert.deepEqual(groups.map(g=>g.points[0].value),[7,12,7]);
  assert.deepEqual(groups.map(g=>g.unit),['mm','cm','mm']);
  assert.ok(groups.every(g=>g.points[0].evidenceId==='invented-source'));
});
test('derived quantities, unresolved ranges and unlocated values do not become observation points',()=>{
  const derived=field(9,'mm','initial','reported_derived_quantity');
  const range=field(4,'mm');range.value.lower=2;range.value.upper=6;
  const unlocated=field(2,'mm');unlocated.evidence_ids=[];
  assert.equal(measurementGroups([record([derived,range,unlocated,field(null,'mm')])]).length,0);
});
test('source links reject executable and local-file URLs; evidence does not carry local paths',()=>{
  assert.equal(safeURL('javascript:alert(1)'),null);assert.equal(safeURL('file:///private/source.pdf'),null);
  assert.equal(safeURL('https://example.org/original'),'https://example.org/original');
  const projected=evidenceView({raw_file:'/private/source.pdf',checksum:'private-checksum',source:{raw_file:'/private',url:'javascript:bad()'},source_cells:[{raw_file:'/private',original_header:'Width',original_value:'7 mm'}]});
  assert.ok(!JSON.stringify(projected).includes('/private'));assert.equal(projected.source.url,null);
});


test('a property shared by two original columns is not mislabeled as the last column',()=>{
 const fields=[{property_id:'source:detector_record',qualifiers:{source_header:'Violet detector'}},{property_id:'source:detector_record',qualifiers:{source_header:'Amber detector'}}];
 assert.equal(comparisonLabel('source:detector_record',fields),'Detector record');
 assert.equal(comparisonLabel('source:detector_record',[fields[0]]),'Violet detector');
});
