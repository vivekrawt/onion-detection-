'use strict';

const $ = (selector) => document.querySelector(selector);
const el = {
  status: $('#status'), statusText: $('#status-text'), themeToggle: $('#theme-toggle'), themeColor: $('meta[name="theme-color"]'),
  modelList: $('#model-list'), confidence: $('#confidence'), confidenceOut: $('#confidence-out'),
  stage: $('#stage'), dropzone: $('#dropzone'), fileInput: $('#file-input'), viewer: $('#viewer'),
  canvasWrap: $('#canvas-wrap'), frame: $('#frame'), canvas: $('#canvas'), legend: $('#legend'),
  labelsToggle: $('#labels-toggle'), downloadPng: $('#download-png'), downloadJson: $('#download-json'), newImage: $('#new-image'),
  fileMeta: $('#file-meta'), timingMeta: $('#timing-meta'), summary: $('#summary'), detList: $('#det-list'), detNote: $('#det-note'),
  dropOverlay: $('#drop-overlay'), toast: $('#toast'),
};

// Annotation colours are fixed across themes: they sit on photos, not on the page.
const CLASS_STYLE = {
  healthy: { title: 'Healthy', color: '#2FA36B', ink: '#FFFFFF' },
  unhealthy: { title: 'Unhealthy', color: '#E4572E', ink: '#FFFFFF' },
  onion: { title: 'Onion', color: '#F2B233', ink: '#2A1C05' },
};
const MAX_BYTES = 20 * 1024 * 1024;
const IMAGE_NAME = /\.(jpe?g|png|webp|bmp|gif|tiff?|heic|heif)$/i;
const RING = 2 * Math.PI * 52;
const RANGE_MIN = Number(el.confidence.min);
const RANGE_MAX = Number(el.confidence.max);
const STAGGER_MS = 45;
const MAX_DELAY_MS = 650;
const FADE_MS = 320;
const motionOK = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const state = {
  device: 'cpu', models: [], modelId: null, threshold: 0.3,
  file: null, previewUrl: null, image: null, result: null,
  hidden: new Set(), showLabels: true, hoverId: null, busy: false, seq: 0,
  view: { w: 0, h: 0, dpr: 1 }, progress: null, raf: 0, summaryKind: null,
};

const pct = (value) => `${Math.round(value * 100)}%`;
const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const refs = (root) => Object.fromEntries([...root.querySelectorAll('[data-ref]')].map((node) => [node.dataset.ref, node]));
const aboveThreshold = () => (state.result ? state.result.detections.filter((d) => d.confidence >= state.threshold) : []);
const visibleDetections = () => aboveThreshold().filter((d) => !state.hidden.has(d.label));
const readyText = () => `Ready · ${state.device.toUpperCase()}`;

function counts() {
  const tally = { total: 0, healthy: 0, unhealthy: 0, onion: 0, confidence: 0 };
  for (const d of aboveThreshold()) {
    tally.total += 1;
    tally[d.label] += 1;
    tally.confidence += d.confidence;
  }
  tally.mean = tally.total ? tally.confidence / tally.total : null;
  return tally;
}

/* ---------- Theme, status, toast ---------- */

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  el.themeToggle.setAttribute('aria-label', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
  el.themeColor.content = theme === 'dark' ? '#121014' : '#F6F1E9';
}

el.themeToggle.addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem('allium-theme', next); } catch { /* storage unavailable: theme lasts this visit */ }
});

function setStatus(kind, text) {
  el.status.dataset.state = kind;
  el.statusText.textContent = text;
}

let toastTimer = 0;
let toastHideTimer = 0;
function showToast(message, kind = 'info') {
  clearTimeout(toastTimer);
  clearTimeout(toastHideTimer);
  el.toast.textContent = message;
  el.toast.dataset.kind = kind;
  el.toast.hidden = false;
  requestAnimationFrame(() => el.toast.classList.add('is-in'));
  toastTimer = setTimeout(() => {
    el.toast.classList.remove('is-in');
    toastHideTimer = setTimeout(() => { el.toast.hidden = true; }, 320);
  }, 4500);
}

/* ---------- Models and threshold ---------- */

async function loadModels() {
  setStatus('loading', 'Connecting');
  try {
    const response = await fetch('/api/models');
    if (!response.ok) throw new Error(response.statusText);
    const data = await response.json();
    state.device = data.device;
    state.models = data.models;
    renderModels();
    const preferred = data.models.find((m) => m.id === data.default_model && m.available) || data.models.find((m) => m.available);
    if (preferred) {
      selectModel(preferred.id);
      setStatus('ready', readyText());
    } else {
      setStatus('error', 'No model files');
    }
  } catch {
    setStatus('error', 'Server offline');
    showToast('Could not reach the Allium server. Start it with: python run.py', 'error');
  }
}

function renderModels() {
  el.modelList.replaceChildren(...state.models.map((model) => {
    const option = document.createElement('label');
    option.className = 'model-option';
    option.innerHTML = `
      <input type="radio" name="model" value="${escapeHtml(model.id)}" ${model.available ? '' : 'disabled'}>
      <span class="model-radio" aria-hidden="true"></span>
      <span>
        <span class="model-name">${escapeHtml(model.name)}<span class="tag tag-${model.mode}">${model.mode === 'health' ? 'Health' : 'Detect'}</span></span>
        <span class="model-desc">${escapeHtml(model.available ? model.description : `Missing file: models/${model.file}`)}</span>
      </span>`;
    option.querySelector('input').addEventListener('change', () => selectModel(model.id));
    return option;
  }));
}

function selectModel(id) {
  const model = state.models.find((m) => m.id === id);
  if (!model || !model.available) return;
  state.modelId = id;
  const input = el.modelList.querySelector(`input[value="${CSS.escape(id)}"]`);
  if (input) input.checked = true;
  // Score scales differ between models, so each starts from its own default.
  setThreshold(model.default_confidence, { redraw: false });
  if (state.file) analyze();
}

function setThreshold(value, { redraw = true } = {}) {
  state.threshold = Math.round(value * 100) / 100;
  el.confidence.value = String(state.threshold);
  el.confidenceOut.textContent = pct(state.threshold);
  el.confidence.style.setProperty('--fill', `${((state.threshold - RANGE_MIN) / (RANGE_MAX - RANGE_MIN)) * 100}%`);
  if (redraw && state.result) {
    if (!visibleDetections().some((d) => d.id === state.hoverId)) state.hoverId = null;
    renderResults();
    draw();
  }
}

el.confidence.addEventListener('input', () => setThreshold(Number(el.confidence.value)));

/* ---------- Upload and analysis ---------- */

function setView(view) {
  el.dropzone.hidden = view !== 'empty';
  el.viewer.hidden = view !== 'viewer';
}

function handleFile(file) {
  if (!file) return;
  if (!file.type.startsWith('image/') && !IMAGE_NAME.test(file.name)) {
    showToast('Please choose an image file: JPG, PNG, WEBP, BMP or HEIC.', 'error');
    return;
  }
  if (file.size > MAX_BYTES) {
    showToast('That image is larger than 20 MB.', 'error');
    return;
  }
  if (!state.modelId) {
    showToast('No model is available. Check that the server is running.', 'error');
    return;
  }
  state.file = file;
  state.image = null;
  if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
  state.previewUrl = URL.createObjectURL(file);
  const preview = new Image();
  preview.onload = () => {
    if (state.file === file && !state.result) {
      state.image = preview;
      layout();
    }
  };
  preview.src = state.previewUrl;
  setView('viewer');
  layout();
  analyze();
  const top = el.stage.getBoundingClientRect().top;
  if (top < 64 || top > window.innerHeight * 0.55) el.stage.scrollIntoView({ behavior: motionOK ? 'smooth' : 'auto', block: 'start' });
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('The analyzed image could not be displayed.'));
    image.src = src;
  });
}

async function analyze() {
  const seq = ++state.seq;
  const { file, modelId } = state;
  cancelAnimationFrame(state.raf);
  Object.assign(state, { busy: true, result: null, hoverId: null, progress: null });
  el.frame.classList.add('is-scanning');
  setStatus('busy', 'Analyzing');
  renderResults();
  draw();

  const body = new FormData();
  body.append('file', file, file.name || 'image.png');
  body.append('model_id', modelId);
  try {
    const response = await fetch('/api/analyze', { method: 'POST', body });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error((data && typeof data.detail === 'string' && data.detail) || `Analysis failed (HTTP ${response.status}).`);
    }
    const image = await loadImage(data.image.data_url);
    if (seq !== state.seq) return;
    state.result = data;
    state.image = image;
    state.hidden.clear();
    finishBusy();
    layout();
    animateIn();
    renderResults();
  } catch (error) {
    if (seq !== state.seq) return;
    const offline = error instanceof TypeError;
    reset();
    showToast(offline ? 'Lost connection to the Allium server.' : error.message, 'error');
    if (offline) setStatus('error', 'Server offline');
  }
}

function finishBusy() {
  state.busy = false;
  el.frame.classList.remove('is-scanning');
  setStatus('ready', readyText());
}

function reset() {
  state.seq += 1;
  cancelAnimationFrame(state.raf);
  if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
  Object.assign(state, { file: null, previewUrl: null, image: null, result: null, hoverId: null, progress: null });
  finishBusy();
  if (!state.modelId) setStatus('error', 'No model files');
  setView('empty');
  renderResults();
}

/* ---------- Canvas ---------- */

function layout() {
  if (el.viewer.hidden) return;
  const style = getComputedStyle(el.canvasWrap);
  const maxW = Math.max(160, el.canvasWrap.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight));
  const maxH = Math.max(280, Math.min(window.innerHeight * 0.7, 900));
  const iw = state.image ? state.image.naturalWidth : 4;
  const ih = state.image ? state.image.naturalHeight : 3;
  const scale = Math.min(maxW / iw, maxH / ih);
  const w = Math.max(1, Math.floor(iw * scale));
  const h = Math.max(1, Math.floor(ih * scale));
  const dpr = Math.min(window.devicePixelRatio || 1, 3);
  el.canvas.width = Math.round(w * dpr);
  el.canvas.height = Math.round(h * dpr);
  el.canvas.style.width = `${w}px`;
  el.canvas.style.height = `${h}px`;
  state.view = { w, h, dpr };
  draw();
}

function draw() {
  const { w, h, dpr } = state.view;
  const ctx = el.canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  // Slightly smaller tags on narrow canvases keep dense piles legible on phones.
  if (state.image) paintScene(ctx, w, h, { hoverId: state.hoverId, progress: state.progress, unit: Math.min(1, Math.max(0.8, w / 600)) });
}

function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, Math.max(0, Math.min(r, w / 2, h / 2)));
  else ctx.rect(x, y, w, h);
}

function rgba(hex, alpha) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

function boxRect(d, w, h) {
  const [x1, y1, x2, y2] = d.box;
  return { x: x1 * w, y: y1 * h, w: (x2 - x1) * w, h: (y2 - y1) * h };
}

function appearAlpha(elapsed, index) {
  const t = Math.min(1, Math.max(0, (elapsed - Math.min(index * STAGGER_MS, MAX_DELAY_MS)) / FADE_MS));
  return 1 - (1 - t) ** 3;
}

/** Draws the photo and its boxes. Shared by the live view and the PNG export. */
function paintScene(ctx, w, h, { hoverId = null, progress = null, unit = 1 }) {
  ctx.drawImage(state.image, 0, 0, w, h);
  const detections = visibleDetections();
  const hovered = hoverId == null ? null : detections.find((d) => d.id === hoverId);
  if (hovered) {
    // Spotlight: dim the photo everywhere except the hovered onion.
    const r = boxRect(hovered, w, h);
    ctx.fillStyle = 'rgba(16, 10, 18, 0.5)';
    ctx.fillRect(0, 0, w, h);
    ctx.save();
    roundRectPath(ctx, r.x, r.y, r.w, r.h, 6 * unit);
    ctx.clip();
    ctx.drawImage(state.image, 0, 0, w, h);
    ctx.restore();
  }
  const items = detections.map((d, index) => {
    const alpha = progress == null ? 1 : appearAlpha(progress, index);
    const grow = (1 - alpha) * 8 * unit;
    const r = boxRect(d, w, h);
    return { d, alpha, active: d === hovered, rect: { x: r.x - grow, y: r.y - grow, w: r.w + grow * 2, h: r.h + grow * 2 } };
  });
  // Tags are placed in confidence order, even while fading in, so they never jump around.
  const occupied = [];
  for (const item of items) {
    if (state.showLabels || item.active) item.tag = placeTag(ctx, item, w, h, unit, occupied);
  }
  // Boxes first, then tags, so no outline cuts through a label; the hovered onion paints last.
  const order = hovered ? [...items.filter((i) => !i.active), ...items.filter((i) => i.active)] : items;
  const dimOthers = Boolean(hovered);
  for (const item of order) if (item.alpha > 0) drawBox(ctx, item, unit, dimOthers);
  for (const item of order) if (item.alpha > 0 && item.tag) drawTag(ctx, item, unit, dimOthers);
}

function drawBox(ctx, { d, alpha, active, rect }, unit, dimOthers) {
  const color = (CLASS_STYLE[d.label] || CLASS_STYLE.onion).color;
  ctx.save();
  ctx.globalAlpha = alpha * (dimOthers && !active ? 0.3 : 1);
  roundRectPath(ctx, rect.x, rect.y, rect.w, rect.h, 6 * unit);
  ctx.fillStyle = rgba(color, active ? 0.14 : 0.07);
  ctx.fill();
  ctx.lineJoin = 'round';
  ctx.lineWidth = (active ? 4.5 : 3.5) * unit;
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.32)';
  ctx.stroke();
  ctx.lineWidth = (active ? 3 : 2) * unit;
  ctx.strokeStyle = color;
  ctx.stroke();
  ctx.restore();
}

const tagFont = (unit) => `600 ${12 * unit}px Inter, system-ui, sans-serif`;

/** Picks the first free spot around the box: above-left, inside top-left, above-right, inside bottom-left. */
function placeTag(ctx, { d, active, rect: r }, w, h, unit, occupied) {
  const style = CLASS_STYLE[d.label] || CLASS_STYLE.onion;
  const padX = 7 * unit;
  const height = 20 * unit;
  const gap = 3 * unit;
  ctx.font = tagFont(unit);
  let text = `${d.id} · ${style.title} ${pct(d.confidence)}`;
  // Small boxes get a compact tag so dense piles stay readable.
  if (!active && ctx.measureText(text).width + padX * 2 > Math.max(r.w, 96 * unit)) text = `${d.id} · ${pct(d.confidence)}`;
  const width = ctx.measureText(text).width + padX * 2;
  const spots = [
    [r.x, r.y - height - gap], [r.x + gap, r.y + gap], [r.x + r.w - width, r.y - height - gap], [r.x + gap, r.y + r.h - height - gap],
  ].map(([x, y]) => ({
    x: Math.min(Math.max(x, 0), Math.max(0, w - width)),
    y: Math.min(Math.max(y, 0), Math.max(0, h - height)),
    w: width,
    h: height,
    fits: y >= 0 && y <= h - height,
  }));
  const overlaps = (s) => occupied.some((o) => s.x < o.x + o.w + gap && o.x < s.x + s.w + gap && s.y < o.y + o.h + gap && o.y < s.y + s.h + gap);
  const spot = spots.find((s) => s.fits && !overlaps(s)) || spots.find((s) => s.fits) || spots[0];
  occupied.push(spot);
  return { ...spot, text, padX, style };
}

function drawTag(ctx, { tag, alpha, active }, unit, dimOthers) {
  ctx.save();
  ctx.globalAlpha = alpha * (dimOthers && !active ? 0.3 : 1);
  ctx.font = tagFont(unit);
  roundRectPath(ctx, tag.x, tag.y, tag.w, tag.h, 6 * unit);
  ctx.fillStyle = tag.style.color;
  ctx.fill();
  ctx.fillStyle = tag.style.ink;
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  ctx.fillText(tag.text, tag.x + tag.padX, tag.y + tag.h / 2 + 0.5 * unit);
  ctx.restore();
}

function animateIn() {
  cancelAnimationFrame(state.raf);
  if (!motionOK) {
    state.progress = null;
    draw();
    return;
  }
  const start = performance.now();
  const tick = (now) => {
    const elapsed = now - start;
    state.progress = elapsed >= MAX_DELAY_MS + FADE_MS ? null : elapsed;
    draw();
    if (state.progress != null) state.raf = requestAnimationFrame(tick);
  };
  state.raf = requestAnimationFrame(tick);
}

/* ---------- Hover linking between canvas and list ---------- */

function hitTest(event) {
  const rect = el.canvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width;
  const y = (event.clientY - rect.top) / rect.height;
  let best = null;
  let bestArea = Infinity;
  for (const d of visibleDetections()) {
    const [x1, y1, x2, y2] = d.box;
    const area = (x2 - x1) * (y2 - y1);
    // Smallest containing box wins, so nested boxes stay reachable.
    if (x >= x1 && x <= x2 && y >= y1 && y <= y2 && area < bestArea) {
      best = d;
      bestArea = area;
    }
  }
  return best;
}

function setHover(id, fromCanvas = false) {
  if (state.hoverId === id) return;
  state.hoverId = id;
  el.canvas.style.cursor = id == null ? 'crosshair' : 'pointer';
  for (const row of el.detList.querySelectorAll('.det')) row.classList.toggle('is-active', Number(row.dataset.id) === id);
  if (fromCanvas && id != null) {
    const row = el.detList.querySelector(`.det[data-id="${id}"]`);
    if (row) keepInView(row, el.detList);
  }
  if (state.progress == null) draw();
}

function keepInView(row, container) {
  const top = row.offsetTop;
  const bottom = top + row.offsetHeight;
  if (top < container.scrollTop) container.scrollTo({ top: top - 6, behavior: motionOK ? 'smooth' : 'auto' });
  else if (bottom > container.scrollTop + container.clientHeight) {
    container.scrollTo({ top: bottom - container.clientHeight + 6, behavior: motionOK ? 'smooth' : 'auto' });
  }
}

el.canvas.addEventListener('pointermove', (event) => { if (state.result) setHover(hitTest(event)?.id ?? null, true); });
el.canvas.addEventListener('pointerdown', (event) => { if (state.result && event.pointerType !== 'mouse') setHover(hitTest(event)?.id ?? null, true); });
el.canvas.addEventListener('pointerleave', (event) => { if (event.pointerType === 'mouse') setHover(null); });
el.detList.addEventListener('pointerover', (event) => {
  const row = event.target.closest('.det');
  if (row) setHover(Number(row.dataset.id));
});
el.detList.addEventListener('pointerleave', () => setHover(null));
el.detList.addEventListener('focusin', (event) => {
  const row = event.target.closest('.det');
  if (row) setHover(Number(row.dataset.id));
});
el.detList.addEventListener('focusout', () => setHover(null));

/* ---------- Results panels ---------- */

function renderResults() {
  renderSummary();
  renderLegend();
  renderList();
  renderMeta();
  el.downloadPng.disabled = !state.result;
  el.downloadJson.disabled = !state.result;
}

const SUMMARY_TEMPLATES = {
  empty: () => `
    <h2 class="panel-title">Summary</h2>
    <p class="summary-lead">Awaiting an image</p>
    <ol class="steps">
      <li><span class="step-num">1</span><span><b>Upload</b> a clear, top-down photo of your onions.</span></li>
      <li><span class="step-num">2</span><span><b>Detect</b>: the model boxes each bulb and judges its health.</span></li>
      <li><span class="step-num">3</span><span><b>Review</b> the counts, tune the threshold, and export.</span></li>
    </ol>`,
  busy: () => `
    <h2 class="panel-title">Summary</h2>
    <div class="busy"><div class="busy-ring"></div><p>Reading every onion…</p></div>
    <div class="skeleton" aria-hidden="true"><span></span><span></span><span></span></div>`,
  health: () => `
    <div class="panel-head"><h2 class="panel-title">Summary</h2><span class="model-pill" data-ref="model"></span></div>
    <div class="gauge">
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle class="gauge-track" cx="60" cy="60" r="52"/>
        <circle class="gauge-arc gauge-unhealthy" cx="60" cy="60" r="52" data-ref="arcBad"/>
        <circle class="gauge-arc gauge-healthy" cx="60" cy="60" r="52" data-ref="arcGood"/>
      </svg>
      <div class="gauge-center">
        <span class="gauge-value"><span data-ref="share">0</span><small data-ref="shareUnit">%</small></span>
        <span class="gauge-caption">healthy</span>
      </div>
    </div>
    <p class="verdict" data-ref="verdict"></p>
    <div class="stats">
      <div class="stat" style="--c: var(--healthy)"><span class="stat-label">Healthy</span><span class="stat-value" data-ref="healthy">0</span></div>
      <div class="stat" style="--c: var(--unhealthy)"><span class="stat-label">Unhealthy</span><span class="stat-value" data-ref="unhealthy">0</span></div>
      <div class="stat" style="--c: var(--ink-2)"><span class="stat-label">Total</span><span class="stat-value" data-ref="total">0</span></div>
    </div>
    <dl class="facts">
      <div><dt>Mean confidence</dt><dd data-ref="mean">—</dd></div>
      <div><dt>Inference time</dt><dd data-ref="speed">—</dd></div>
    </dl>`,
  onion: () => `
    <div class="panel-head"><h2 class="panel-title">Summary</h2><span class="model-pill" data-ref="model"></span></div>
    <div class="bigcount"><span class="bigcount-value" data-ref="total">0</span><span class="bigcount-label" data-ref="noun">onions located</span></div>
    <p class="note">This model finds onions but doesn't judge their health.
      <button class="text-btn" type="button" data-ref="useHealth">Classify them with Onion Health</button></p>
    <p class="empty-note" data-ref="empty" hidden></p>
    <dl class="facts">
      <div><dt>Mean confidence</dt><dd data-ref="mean">—</dd></div>
      <div><dt>Inference time</dt><dd data-ref="speed">—</dd></div>
    </dl>`,
};

function renderSummary() {
  const kind = state.busy ? 'busy' : state.result ? state.result.model.mode : 'empty';
  if (kind !== state.summaryKind) {
    state.summaryKind = kind;
    el.summary.innerHTML = SUMMARY_TEMPLATES[kind]();
    const useHealth = el.summary.querySelector('[data-ref="useHealth"]');
    if (useHealth) {
      const healthModel = state.models.find((m) => m.mode === 'health' && m.available);
      if (healthModel) useHealth.addEventListener('click', () => selectModel(healthModel.id));
      else useHealth.remove();
    }
  }
  if (kind !== 'health' && kind !== 'onion') return;
  const ref = refs(el.summary);
  const tally = counts();
  ref.model.textContent = state.result.model.name;
  ref.mean.textContent = tally.mean == null ? '—' : pct(tally.mean);
  ref.speed.textContent = `${Math.round(state.result.timing_ms.inference)} ms`;
  tweenNumber(ref.total, tally.total);
  if (kind === 'onion') {
    ref.noun.textContent = tally.total === 1 ? 'onion located' : 'onions located';
    ref.empty.hidden = tally.total > 0;
    ref.empty.textContent = `Nothing above ${pct(state.threshold)} confidence. Try lowering the threshold.`;
    return;
  }
  const share = tally.total ? tally.healthy / tally.total : 0;
  ref.arcGood.style.strokeDasharray = `${RING * share} ${RING}`;
  ref.arcBad.style.strokeDasharray = `${tally.total ? RING : 0} ${RING}`;
  if (tally.total) {
    ref.shareUnit.hidden = false;
    tweenNumber(ref.share, Math.round(share * 100));
  } else {
    ref.share.dataset.value = '0';
    ref.share.textContent = '—';
    ref.shareUnit.hidden = true;
  }
  tweenNumber(ref.healthy, tally.healthy);
  tweenNumber(ref.unhealthy, tally.unhealthy);
  ref.verdict.innerHTML = tally.total
    ? `<b>${tally.healthy} of ${tally.total}</b> ${tally.total === 1 ? 'onion looks' : 'onions look'} healthy.`
    : `No onions above ${pct(state.threshold)} confidence. Try lowering the threshold.`;
}

const tweens = new WeakMap();
function tweenNumber(node, to) {
  const from = Number(node.dataset.value || 0);
  node.dataset.value = String(to);
  cancelAnimationFrame(tweens.get(node));
  if (!motionOK || from === to) {
    node.textContent = String(to);
    return;
  }
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / 450);
    node.textContent = String(Math.round(from + (to - from) * (1 - (1 - t) ** 3)));
    if (t < 1) tweens.set(node, requestAnimationFrame(step));
  };
  tweens.set(node, requestAnimationFrame(step));
}

function renderLegend() {
  const labels = state.result ? (state.result.model.mode === 'health' ? ['healthy', 'unhealthy'] : ['onion']) : [];
  if (el.legend.dataset.labels !== labels.join()) {
    el.legend.dataset.labels = labels.join();
    el.legend.replaceChildren(...labels.map((label) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.dataset.label = label;
      chip.style.setProperty('--c', CLASS_STYLE[label].color);
      chip.innerHTML = `<span class="dot"></span>${CLASS_STYLE[label].title}<b></b>`;
      chip.addEventListener('click', () => toggleLabel(label));
      return chip;
    }));
  }
  const tally = counts();
  for (const chip of el.legend.children) {
    const shown = !state.hidden.has(chip.dataset.label);
    chip.querySelector('b').textContent = tally[chip.dataset.label];
    chip.setAttribute('aria-pressed', String(shown));
    chip.title = `${shown ? 'Hide' : 'Show'} ${CLASS_STYLE[chip.dataset.label].title.toLowerCase()} boxes`;
  }
}

function toggleLabel(label) {
  if (state.hidden.has(label)) state.hidden.delete(label);
  else state.hidden.add(label);
  if (!visibleDetections().some((d) => d.id === state.hoverId)) state.hoverId = null;
  renderResults();
  draw();
}

function renderList() {
  if (!state.result) {
    el.detNote.textContent = '';
    el.detList.innerHTML = `<li class="det-empty">${state.busy ? 'Detecting onions…' : 'Detected onions will be listed here.'}</li>`;
    return;
  }
  const detections = aboveThreshold();
  const below = state.result.detections.length - detections.length;
  el.detNote.textContent = below ? `${detections.length} shown · ${below} below threshold` : `${detections.length} shown`;
  if (!detections.length) {
    el.detList.innerHTML = `<li class="det-empty">Nothing above ${pct(state.threshold)} confidence.</li>`;
    return;
  }
  el.detList.replaceChildren(...detections.map((d) => {
    const style = CLASS_STYLE[d.label];
    const row = document.createElement('li');
    row.className = 'det';
    row.dataset.id = d.id;
    row.tabIndex = 0;
    row.style.setProperty('--c', style.color);
    row.classList.toggle('is-muted', state.hidden.has(d.label));
    row.classList.toggle('is-active', d.id === state.hoverId);
    row.setAttribute('aria-label', `Onion ${d.id}: ${style.title}, ${pct(d.confidence)} confidence`);
    row.innerHTML = `
      <span class="det-num">${d.id}</span>
      <span class="det-label"><span class="dot"></span>${style.title}</span>
      <span class="det-meter"><span style="width: ${(d.confidence * 100).toFixed(1)}%"></span></span>
      <span class="det-conf">${pct(d.confidence)}</span>`;
    return row;
  }));
}

function renderMeta() {
  const result = state.result;
  const name = state.file ? state.file.name || 'Pasted image' : '';
  el.fileMeta.textContent = result ? `${name} · ${result.image.original_width} × ${result.image.original_height}px` : name;
  el.timingMeta.textContent = result
    ? `${result.model.name} · ${Math.round(result.timing_ms.inference)} ms inference`
    : state.busy ? 'Analyzing…' : '';
}

/* ---------- Exports ---------- */

function baseName() {
  const name = (state.result && state.result.image.name) || 'onions';
  return name.replace(/\.[^.]+$/, '').replace(/[^\w-]+/g, '-').replace(/^-+|-+$/g, '') || 'onions';
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function captionText() {
  const tally = counts();
  const model = state.result.model;
  const parts = model.mode === 'health'
    ? [`Healthy ${tally.healthy}`, `Unhealthy ${tally.unhealthy}`, `Total ${tally.total}`]
    : [`Onions ${tally.total}`];
  return [...parts, `≥ ${pct(state.threshold)} confidence`, model.name].join('  ·  ');
}

async function downloadImage() {
  if (!state.result || !state.image) return;
  const w = state.image.naturalWidth;
  const h = state.image.naturalHeight;
  const unit = Math.max(1, Math.max(w, h) / 1000);
  const band = Math.round(52 * unit);
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h + band;
  const ctx = canvas.getContext('2d');
  try { await document.fonts.load(`${Math.round(24 * unit)}px "Instrument Serif"`); } catch { /* fall back to Georgia */ }
  paintScene(ctx, w, h, { unit });

  // Caption band beneath the photo, so the export reads as a small report.
  const pad = 16 * unit;
  ctx.fillStyle = '#FFFCF7';
  ctx.fillRect(0, h, w, band);
  ctx.fillStyle = '#E8DFD2';
  ctx.fillRect(0, h, w, Math.max(1, unit));
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  ctx.fillStyle = '#6E2A57';
  ctx.font = `${24 * unit}px "Instrument Serif", Georgia, serif`;
  ctx.fillText('Allium', pad, h + band / 2);
  const brandWidth = ctx.measureText('Allium').width;
  const caption = captionText();
  let size = 13 * unit;
  ctx.font = `500 ${size}px Inter, system-ui, sans-serif`;
  const room = w - brandWidth - pad * 3;
  const needed = ctx.measureText(caption).width;
  if (needed > room) {
    size = Math.max(8, size * (room / needed));
    ctx.font = `500 ${size}px Inter, system-ui, sans-serif`;
  }
  ctx.fillStyle = '#5B5260';
  ctx.textAlign = 'right';
  ctx.fillText(caption, w - pad, h + band / 2);
  canvas.toBlob((blob) => {
    if (blob) saveBlob(blob, `${baseName()}-allium.png`);
    else showToast('The image could not be exported.', 'error');
  }, 'image/png');
}

function downloadReport() {
  if (!state.result) return;
  const result = state.result;
  const tally = counts();
  const { original_width: width, original_height: height } = result.image;
  const report = {
    app: 'Allium',
    generated_at: new Date().toISOString(),
    image: { name: result.image.name, width, height },
    model: { id: result.model.id, name: result.model.name, mode: result.model.mode },
    confidence_threshold: state.threshold,
    counts: result.model.mode === 'health'
      ? { healthy: tally.healthy, unhealthy: tally.unhealthy, total: tally.total }
      : { onions: tally.total },
    healthy_share: result.model.mode === 'health' && tally.total ? Number((tally.healthy / tally.total).toFixed(4)) : null,
    mean_confidence: tally.mean == null ? null : Number(tally.mean.toFixed(4)),
    detections: aboveThreshold().map((d) => ({
      id: d.id,
      label: d.label,
      confidence: d.confidence,
      box_normalized: d.box,
      box_pixels: d.box.map((v, i) => Math.round(v * (i % 2 ? height : width))),
    })),
    timing_ms: result.timing_ms,
    note: 'Visual estimate from a single photo; not a physical grading certificate.',
  };
  saveBlob(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }), `${baseName()}-allium.json`);
}

/* ---------- Inputs: picker, drag and drop, paste, samples ---------- */

el.dropzone.addEventListener('click', () => el.fileInput.click());
el.dropzone.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    el.fileInput.click();
  }
});
el.fileInput.addEventListener('change', () => {
  handleFile(el.fileInput.files[0]);
  el.fileInput.value = '';
});

const hasFiles = (event) => Boolean(event.dataTransfer) && [...event.dataTransfer.types].includes('Files');
let dragDepth = 0;
function endDrag() {
  dragDepth = 0;
  el.dropOverlay.hidden = true;
  document.body.classList.remove('is-dragging');
}
window.addEventListener('dragenter', (event) => {
  if (!hasFiles(event)) return;
  dragDepth += 1;
  el.dropOverlay.hidden = false;
  document.body.classList.add('is-dragging');
});
window.addEventListener('dragleave', (event) => {
  if (hasFiles(event) && --dragDepth <= 0) endDrag();
});
window.addEventListener('dragover', (event) => { if (hasFiles(event)) event.preventDefault(); });
window.addEventListener('drop', (event) => {
  if (!hasFiles(event)) return;
  event.preventDefault();
  endDrag();
  handleFile(event.dataTransfer.files[0]);
});

window.addEventListener('paste', (event) => {
  const item = [...(event.clipboardData?.items || [])].find((i) => i.kind === 'file' && i.type.startsWith('image/'));
  if (!item) return;
  const blob = item.getAsFile();
  const extension = blob.type.split('/')[1] || 'png';
  handleFile(new File([blob], blob.name && blob.name !== 'image.png' ? blob.name : `pasted-image.${extension}`, { type: blob.type }));
});

for (const button of document.querySelectorAll('[data-sample]')) {
  button.addEventListener('click', async () => {
    try {
      const response = await fetch(button.dataset.sample);
      if (!response.ok) throw new Error(response.statusText);
      const blob = await response.blob();
      handleFile(new File([blob], button.dataset.name, { type: blob.type || 'image/jpeg' }));
    } catch {
      showToast('Could not load that sample image.', 'error');
    }
  });
}

el.labelsToggle.addEventListener('click', () => {
  state.showLabels = !state.showLabels;
  el.labelsToggle.setAttribute('aria-pressed', String(state.showLabels));
  draw();
});
el.downloadPng.addEventListener('click', downloadImage);
el.downloadJson.addEventListener('click', downloadReport);
el.newImage.addEventListener('click', () => {
  reset();
  el.dropzone.focus({ preventScroll: true });
});

let lastWrapWidth = 0;
new ResizeObserver(([entry]) => {
  if (Math.abs(entry.contentRect.width - lastWrapWidth) > 0.5) {
    lastWrapWidth = entry.contentRect.width;
    layout();
  }
}).observe(el.canvasWrap);
let resizeFrame = 0;
window.addEventListener('resize', () => {
  cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(layout);
});

/* ---------- Start ---------- */

applyTheme(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
setThreshold(state.threshold, { redraw: false });
setView('empty');
renderResults();
loadModels();
