'use strict';
const $ = (id) => document.getElementById(id);
// A URL fragment needs no extra server route and never changes the API payload.
let presentationMode = window.location.hash.startsWith('#presentation');
document.documentElement.classList.toggle('presentation', presentationMode);
const EXAMPLES = {
  'urgent-billing': 'Since this morning, I have been charged twice for the same subscription. Please fix this urgently; the extra charge is blocking today’s payment.',
  'routine-account': 'Hi, I would like to change the email address on my account. There is no rush; next week is fine.'
};
const QUESTIONS = [
  {id: 'routing', type: 'choice', name: 'Support queue', instructions: 'Which support queue should handle this customer message?', criteria: [['billing', 'Payments, invoices, refunds, or duplicate charges'], ['account', 'Profile, email address, login, or account access'], ['technical', 'Software errors, broken features, or technical faults']]},
  {id: 'urgent', type: 'noul', name: 'Explicit urgency', instructions: 'Does the customer explicitly request urgent or immediate handling?', criteria: [['false', 'No explicit request for urgent or immediate handling'], ['true', 'Explicitly asks for urgent or immediate handling']]},
  {id: 'priority', type: 'score', name: 'Requested priority', instructions: 'Assign the priority expressed by this message using its requested response timing.', criteria: [['0', 'Routine: no urgency; the normal queue is acceptable'], ['1', 'Soon: prompt help is requested, but immediate handling is not explicitly required'], ['2', 'Immediate: urgent or immediate handling is explicitly requested']]}
];
let busy = false;
let ready = false;
let lastResponse = null;
let completedRequest = null;
let decisionTimeout = 43000;

function probabilityPercent(value) {
  if (value > 0 && value < .001) return '<0.1%';
  if (value > .999 && value < 1) return '>99.9%';
  return `${(value * 100).toFixed(1)}%`;
}

function boundedDecimal(value, digits) {
  const edge = 10 ** -digits;
  if (value > 0 && value < edge) return `<${edge.toFixed(digits)}`;
  if (value > 1 - edge && value < 1) return `>${(1 - edge).toFixed(digits)}`;
  return value.toFixed(digits);
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function labelInput(parent, name, id, value, className, maximum = 8192) {
  const label = node('label', 'sr-only', name); label.htmlFor = id;
  const multiline = presentationMode && className === 'criterion-description';
  const input = node(multiline ? 'textarea' : 'input', className); input.id = id; input.value = value;
  if (multiline) input.rows = 2;
  input.maxLength = maximum; input.required = true; input.autocomplete = 'off';
  parent.append(label, input);
  return input;
}

function renderCriteria(question, container) {
  container.replaceChildren();
  question.criteria.forEach(([key, description], index) => {
    const row = node('div', 'criterion-row');
    if (question.type === 'choice') {
      const input = labelInput(row, `${question.name}: candidate ${index + 1} key`, `${question.id}-key-${index}`, key, 'criterion-key', 64);
      input.addEventListener('input', () => { question.criteria[index][0] = input.value; changed(); });
    } else {
      row.append(node('span', 'stage-key', question.type === 'score' ? `Stage ${index}` : key));
    }
    const input = labelInput(row, `${question.name}: ${question.type === 'score' ? 'stage ' + index : key} description`, `${question.id}-description-${index}`, description, 'criterion-description');
    input.addEventListener('input', () => { question.criteria[index][1] = input.value; changed(); });
    if (question.type !== 'noul') {
      const remove = node('button', 'remove-button', '×'); remove.type = 'button';
      remove.setAttribute('aria-label', `Remove ${question.type === 'score' ? 'stage ' + index : 'candidate ' + key}`);
      remove.disabled = question.criteria.length <= 2;
      remove.addEventListener('click', () => {
        question.criteria.splice(index, 1); renderCriteria(question, container); changed();
        container.querySelector('input')?.focus();
      });
      row.append(remove);
    } else row.append(node('span'));
    container.append(row);
  });
  if (question.type !== 'noul') {
    const add = node('button', 'text-button add-button', question.type === 'score' ? 'Add a stage' : 'Add a candidate');
    add.type = 'button'; add.disabled = question.criteria.length >= 26;
    add.addEventListener('click', () => {
      let key = `option_${question.criteria.length}`;
      while (question.criteria.some((entry) => entry[0] === key)) key += '_';
      question.criteria.push([key, '']); renderCriteria(question, container); changed();
      container.querySelectorAll('.criterion-description')[question.criteria.length - 1].focus();
    });
    container.append(add);
  }
}

function buildEditors() {
  QUESTIONS.forEach((question, index) => {
    const details = node('details', 'question-editor'); details.open = index === 0;
    const summary = node('summary');
    summary.append(node('span', 'type-small', question.type === 'noul' ? 'Noul' : question.type === 'score' ? 'Score' : 'Choice'), node('span', 'question-name', question.name));
    const body = node('div', 'question-body');
    const label = node('label', 'field-label', 'Instructions'); label.htmlFor = `${question.id}-instructions`;
    const input = node('textarea'); input.id = label.htmlFor; input.value = question.instructions;
    input.rows = 2; input.maxLength = 8192; input.required = true;
    input.addEventListener('input', () => { question.instructions = input.value; changed(); });
    const hint = node('p', 'criteria-heading', question.type === 'score' ? 'Ordered stages · adjacent stages are treated as equally spaced' : 'Candidate meanings');
    const criteria = node('div'); criteria.id = `${question.id}-criteria`;
    renderCriteria(question, criteria);
    body.append(label, input, hint, criteria); details.append(summary, body);
    $('question-editors').append(details);
  });
}

function requestPayload() {
  if (!$('state-input').value.trim()) throw new Error('Enter a customer message before running the decisions.');
  const questions = {};
  QUESTIONS.forEach((question) => {
    if (!question.instructions.trim()) throw new Error(`${question.name}: enter instructions.`);
    if (question.criteria.some(([key, description]) => !key.trim() || !description.trim())) throw new Error(`${question.name}: complete every candidate key and description.`);
    if (question.type !== 'score' && new Set(question.criteria.map(([key]) => key)).size !== question.criteria.length) throw new Error(`${question.name}: candidate keys must be unique.`);
    const criteria = question.type === 'score' ? question.criteria.map(([, text]) => text) : Object.fromEntries(question.criteria);
    questions[question.id] = {type: question.type, instructions: question.instructions, criteria};
  });
  return {state: $('state-input').value, questions};
}

function changed() {
  try {
    const payload = requestPayload();
    $('request-json').textContent = JSON.stringify(payload, null, 2);
    $('copy-request').disabled = false;
    if (completedRequest) {
      const stale = JSON.stringify(payload) !== completedRequest;
      $('result-state').textContent = stale ? 'INPUTS CHANGED · RUN AGAIN' : 'LAST COMPLETED RUN';
      $('output-panel').classList.toggle('stale-results', stale);
    }
  } catch (error) {
    $('request-json').textContent = error.message; $('copy-request').disabled = true;
    if (completedRequest) {
      $('result-state').textContent = 'INPUTS CHANGED · RUN AGAIN';
      $('output-panel').classList.add('stale-results');
    }
  }
}

async function api(path, options = {}, timeout = 40000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(path, {...options, headers: {'X-Mini-Jev-Demo': '1', ...(options.headers || {})}, signal: controller.signal, cache: 'no-store'});
    let payload;
    try { payload = await response.json(); } catch { throw new Error('The demo returned an unreadable response. Check its terminal and try again.'); }
    if (!response.ok) throw new Error(payload.error?.message || `Request failed (HTTP ${response.status}).`);
    return payload;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. The model may still be finishing; wait before trying again.');
    if (error instanceof TypeError) throw new Error('Cannot reach the local demo. Check that both terminal processes are running.');
    throw error;
  } finally { clearTimeout(timer); }
}

function updateControls() {
  $('run-button').disabled = busy || !ready;
  $('input-fields').disabled = busy;
  $('run-button-label').textContent = busy ? 'Reading three questions…' : 'Run decisions';
  $('run-help').textContent = busy ? 'Waiting for the live API. Questions run sequentially.' : ready ? 'Runs the resident model now. No saved answers.' : 'Start the model API to run a live request.';
  $('output-panel').setAttribute('aria-busy', String(busy));
}

async function checkConnection() {
  $('connection-button').disabled = true;
  try {
    const health = await api('/api/health', {}, 5000); ready = health.ready;
    if (Number.isFinite(health.request_timeout_ms)) decisionTimeout = health.request_timeout_ms;
    $('connection-state').textContent = ready ? 'Model API ready' : 'Model API loading';
    $('connection-state').className = ready ? 'status ready' : 'status';
    $('model-info').textContent = `Model: ${health.model} · Complete input limit: ${health.max_input_tokens ?? 'API-defined'} tokens per question · API: ${health.api_url}`;
  } catch {
    ready = false; $('connection-state').textContent = 'Model API offline'; $('connection-state').className = 'status';
    $('model-info').textContent = 'Start ./run.sh --without-calibration in another terminal, then check the connection. The UI never starts or downloads a model.';
  } finally { $('connection-button').disabled = false; updateControls(); }
}

function describe(question, key) {
  return question.type === 'score' ? question.criteria[Number(key)] : question.criteria[key];
}

function renderAnswers(response, request, elapsed, browserElapsed) {
  $('answers').replaceChildren();
  for (const id of ['routing', 'urgent', 'priority']) {
    const answer = response.answers[id]; const question = request.questions[id];
    const title = answer.type === 'choice' ? 'Choice' : answer.type === 'noul' ? 'Noul' : 'Score';
    const card = node('article', 'answer-card'); card.id = `answer-${id}`;
    const heading = node('div', 'answer-top');
    heading.append(node('span', 'type-name', title), node('span', 'return-type', answer.type === 'choice' ? 'semantic key' : answer.type === 'noul' ? 'number · 0–1' : 'expected stage'));
    const value = node('p', 'answer-value', answer.type === 'choice' ? answer.choice : answer.type === 'noul' ? boundedDecimal(answer.noul, 4) : answer.score.toFixed(3));
    if (answer.type === 'score') value.append(node('small', '', ` / ${question.criteria.length - 1}`));
    const explanation = answer.type === 'choice' ? describe(question, answer.choice) : answer.type === 'noul' ? `P(true) = ${probabilityPercent(answer.noul)} · most likely: ${answer.label}` : `Most likely stage ${answer.label}: ${describe(question, answer.label)}`;
    card.append(heading, value, node('p', 'answer-description', explanation));
    card.append(node('p', 'presentation-caption', answer.type === 'choice' ? 'Selected support queue' : answer.type === 'noul' ? 'Probability of explicit urgency' : `Most likely: stage ${answer.label}`));
    const list = node('ul', 'probability-list'); list.setAttribute('aria-label', `${title} candidate probabilities`);
    for (const [key, probability] of Object.entries(answer.probabilities)) {
      const item = node('li', 'probability-row');
      const label = node('span', 'probability-label', answer.type === 'score' ? `Stage ${key}` : key); label.title = describe(question, key);
      const meter = node('meter'); meter.min = 0; meter.max = 1; meter.value = probability;
      meter.setAttribute('aria-label', `${key}: ${describe(question, key)}`); meter.setAttribute('aria-valuetext', probabilityPercent(probability));
      item.append(label, meter, node('span', 'probability-number', probabilityPercent(probability))); list.append(item);
    }
    card.append(list);
    const meta = node('div', 'answer-meta');
    const concentration = typeof answer.confidence === 'number' ? answer.confidence : 1 + Object.values(answer.probabilities).reduce((sum, p) => sum + (p > 0 ? p * Math.log(p) : 0), 0) / Math.log(Object.keys(answer.probabilities).length);
    const temperature = answer.temperature_calibration_applied === true ? 'Temperature scaling applied' : answer.temperature_calibration_applied === false ? 'No temperature calibration applied' : 'Temperature status not supplied';
    meta.append(node('span', '', `Concentration ${boundedDecimal(concentration, 3)}`), node('span', '', temperature));
    card.append(meta); $('answers').append(card);
  }
  $('run-metrics').replaceChildren(node('span', '', `Browser round-trip ${browserElapsed.toFixed(0)} ms`), node('span', '', `Bridge → API ${elapsed.toFixed(0)} ms`), node('span', '', `${response.usage.input_tokens} input · ${response.usage.output_tokens} output tokens`));
  $('response-json').textContent = JSON.stringify(response, null, 2);
  $('copy-response').disabled = false;
  $('run-announcement').textContent = `Live run complete. Three decisions returned in ${browserElapsed.toFixed(0)} milliseconds.`;
}

$('decision-form').addEventListener('submit', async (event) => {
  event.preventDefault(); if (busy || !ready) return;
  $('error-message').hidden = true;
  let request;
  try { request = requestPayload(); } catch (error) { $('error-message').textContent = error.message; $('error-message').hidden = false; return; }
  busy = true; updateControls(); $('result-state').textContent = 'LIVE REQUEST RUNNING';
  if (lastResponse) $('output-panel').classList.add('stale-results');
  $('run-announcement').textContent = 'Running three questions on the live model.';
  const started = performance.now();
  try {
    const result = await api('/api/decide', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(request)}, decisionTimeout);
    if (result.source !== 'live_api') throw new Error('Unexpected response source. This workbench accepts live API output only.');
    lastResponse = result.response; completedRequest = JSON.stringify(request);
    renderAnswers(result.response, request, result.elapsed_ms, performance.now() - started);
    $('output-panel').classList.remove('stale-results');
    $('result-state').textContent = 'LIVE RUN COMPLETE';
  } catch (error) {
    $('error-message').textContent = error.message; $('error-message').hidden = false;
    $('result-state').textContent = lastResponse ? 'RUN FAILED · PREVIOUS RESULTS' : 'RUN FAILED';
    $('run-announcement').textContent = 'The request failed. Read the error message above the workbench.';
  } finally { busy = false; updateControls(); }
});

async function copyJson(kind) {
  const text = kind === 'request' ? JSON.stringify(requestPayload(), null, 2) : JSON.stringify(lastResponse, null, 2);
  let message;
  try { await navigator.clipboard.writeText(text); message = `${kind === 'request' ? 'Request' : 'Response'} copied.`; }
  catch { message = 'Clipboard access is unavailable. Select the JSON text and copy it with your keyboard.'; $(`${kind}-json`).focus(); }
  $('copy-status').textContent = message;
  $(`copy-${kind}-status`).textContent = message;
}
$('copy-request').addEventListener('click', () => copyJson('request'));
$('copy-response').addEventListener('click', () => copyJson('response'));
$('connection-button').addEventListener('click', checkConnection);
$('example-button').addEventListener('click', () => { $('state-input').value = EXAMPLES[$('example-select').value]; changed(); $('state-input').focus(); });
$('state-input').addEventListener('input', changed);
$('state-input').value = EXAMPLES['urgent-billing'];
buildEditors(); changed(); checkConnection();
window.addEventListener('hashchange', () => {
  if (!window.location.hash.startsWith('#presentation') && window.location.hash !== '#standard') return;
  presentationMode = window.location.hash.startsWith('#presentation');
  document.documentElement.classList.toggle('presentation', presentationMode);
  QUESTIONS.forEach((question) => renderCriteria(question, $(`${question.id}-criteria`)));
});
setInterval(() => { if (!busy && !document.hidden) checkConnection(); }, 15000);
