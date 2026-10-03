// Recompute the entire retrospective fixture with the released importer.
// This validates software arithmetic, not human usability or source authorship.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import crypto from 'node:crypto';
import {parseJSONL, compareRecords} from '../../../docs/explorer/import/core.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const read = name => fs.readFileSync(path.join(here, name), 'utf8');
const sha = text => crypto.createHash('sha256').update(text).digest('hex');
const data = read('diagnostic_import.jsonl');
const evidence = JSON.parse(read('CASE_EVIDENCE.json'));
const parsed = parseJSONL(data);
assert.equal(parsed.ok, true, JSON.stringify(parsed.errors));
assert.equal(parsed.records.length, 48);
assert.equal(parsed.groups.length, 12);
const comparisons = [];
for (const group of parsed.groups) {
  const get = condition => group.records.find(r => r.raw.condition === condition);
  const diagnostic = compareRecords(get('diagnostic_last_position_only'), get('diagnostic_stock_full_position'));
  const repeat = compareRecords(get('repeat_stock_full_position_a'), get('repeat_stock_full_position_b'));
  const maximum = Math.max(...diagnostic.candidates.map(c => Math.abs(c.delta)));
  const expected = evidence.subsequent_diagnosis.fixtures.find(f => f.fixture === group.itemId);
  assert.ok(Math.abs(maximum - expected.diagnostic_max_abs_probability_difference) < 1e-14);
  assert.equal(diagnostic.label_changed, false);
  assert.equal(diagnostic.reference, null);
  assert.equal(diagnostic.a.recorded_latency_ms, null);
  assert.equal(diagnostic.b.recorded_latency_ms, null);
  assert.ok(repeat.candidates.every(c => c.delta === 0));
  assert.equal(diagnostic.declared_physical_identities.unique, 2);
  assert.equal(repeat.declared_physical_identities.unique, 2);
  comparisons.push({fixture: group.itemId, type: group.type,
    diagnostic_max_abs_probability_difference: maximum,
    diagnostic_label_changed: false, repeat_max_abs_probability_difference: 0,
    probability_threshold_exceeded: maximum > evidence.subsequent_diagnosis.probability_atol});
}
assert.equal(comparisons.filter(c => c.probability_threshold_exceeded).length, 2);
const output = {passed: true, checker: 'released importer core, current local bytes',
  importer_core_sha256: sha(fs.readFileSync(path.join(here, '../../../docs/explorer/import/core.mjs'))),
  fixture_sha256: sha(data), records: 48, groups: 12,
  input_warnings: {missing_reference: parsed.warnings.filter(w => w.code === 'UNKNOWN_REFERENCE').length,
    missing_latency: parsed.warnings.filter(w => w.code === 'UNKNOWN_LATENCY').length},
  comparisons, new_inference_calls: 0, human_participants: 0,
  scope: 'Arithmetic/schema validation only; browser rendering and human comparative usability are separate.'};
console.log(JSON.stringify(output, null, 2));
