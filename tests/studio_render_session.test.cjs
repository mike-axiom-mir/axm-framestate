const assert = require('node:assert/strict');
const test = require('node:test');

const {
  formatElapsed,
  shortDigest,
  renderSessionView,
  newRenderSession,
} = require('../src/axm_framestate/studio_ui/render_session.js');

test('elapsed formatting stays factual and bounded', () => {
  assert.equal(formatElapsed(0), '0s');
  assert.equal(formatElapsed(59_999), '59s');
  assert.equal(formatElapsed(61_000), '1m 01s');
  assert.equal(formatElapsed(3_661_000), '1h 01m');
});

test('running view exposes snapshot identity without fake progress', () => {
  const session = {status: 'running', digest: 'sha256:1234567890abcdef', mode: 'adaptive', startedAt: 1000};
  const view = renderSessionView(session, 7000, false, session.digest);
  assert.equal(view.state, 'RENDERING LOCAL SNAPSHOT');
  assert.equal(view.snapshot, '1234567890ab');
  assert.equal(view.mode, 'ADAPTIVE');
  assert.equal(view.elapsed, '6s');
  assert.match(view.detail, /No percentage is shown/);
  assert.equal(view.receipt, 'waiting');
});

test('missing completion receipt is held and exact-snapshot retry stays available', () => {
  const session = {status: 'no_receipt', digest: 'sha256:abcdefabcdef1234', mode: 'exact', startedAt: 0};
  const view = renderSessionView(session, 12_000, true, 'sha256:newer');
  assert.equal(view.state, 'NO COMPLETION RECEIPT');
  assert.equal(view.receipt, 'none');
  assert.equal(view.retry, true);
  assert.match(view.detail, /Do not infer that output completed or failed/);
  assert.match(view.detail, /current Studio edits may be newer/i);
});

test('new render session owns a detached project snapshot', () => {
  const project = {id: 'film', title: 'A', layers: [{id: 'one'}]};
  const session = newRenderSession(project, 'sha256:1234567890abcdef', 'exact', 5000);
  project.title = 'B';
  project.layers[0].id = 'changed';
  assert.equal(session.project.title, 'A');
  assert.equal(session.project.layers[0].id, 'one');
  assert.equal(session.name, `film-${shortDigest(session.digest)}`);
  assert.equal(session.startedAt, 5000);
});
