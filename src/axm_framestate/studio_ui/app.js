"use strict";

const $ = (q) => document.querySelector(q);
const $$ = (q) => Array.from(document.querySelectorAll(q));
const clone = (v) => JSON.parse(JSON.stringify(v));

const S = { project: null, digest: "", frame: 0, selected: null, dirty: false, playing: false, timer: null, previewToken: 0, assetLimit: 64 * 1024 * 1024 };

async function api(path, payload = null) {
  const opts = payload === null ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) };
  const r = await fetch(path, opts);
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || `${r.status} ${r.statusText}`);
  return data;
}

function toast(msg, error = false) {
  const el = $("#toast"); el.textContent = msg; el.className = error ? "show error" : "show";
  clearTimeout(el._timer); el._timer = setTimeout(() => { el.className = ""; }, 2800);
}

function markDirty(v = true) {
  S.dirty = v; const el = $("#dirtyFlag"); el.textContent = v ? "unsaved" : "clean"; el.className = v ? "pill dirty" : "pill";
}

function uid(prefix) {
  const ids = new Set([...(S.project.media || []).map(x => x.id), ...(S.project.layers || []).map(x => x.id), ...(S.project.captions || []).map(x => x.id), ...(S.project.audio || []).map(x => x.id)]);
  let n = 1; while (ids.has(`${prefix}-${n}`)) n++; return `${prefix}-${n}`;
}

function currentObject() {
  if (!S.selected) return null;
  const rows = S.selected.type === "layer" ? S.project.layers : S.selected.type === "caption" ? S.project.captions : S.project.audio;
  return rows.find(x => x.id === S.selected.id) || null;
}

function setSelection(type, id) { S.selected = { type, id }; renderLists(); renderInspector(); }

function layerDefaults(kind) {
  const x = Math.floor(S.project.canvas.width / 2), y = Math.floor(S.project.canvas.height / 2), end = S.project.duration_frames;
  const base = { id: uid(kind), kind, z: S.project.layers.length, start_frame: 0, end_frame: end, x, y };
  if (kind === "rect") return { ...base, w: 160, h: 90, color: [80, 150, 235] };
  if (kind === "circle") return { ...base, radius: 52, color: [235, 120, 170] };
  if (kind === "text") return { ...base, text: "TEXT", scale: 3, color: [245, 245, 250] };
  if (kind === "particles") return { ...base, count: 80, seed: 1, spread_x: 140, spread_y: 70, speed: 1, size: 2, color: [90, 180, 240] };
  if (kind === "cube3d") return { ...base, depth: 220, size: 90, rot_x_mdeg: 12000, rot_y_mdeg: 30000, rot_z_mdeg: 0, shadow: true, color: [220, 170, 85] };
  return base;
}

function addLayer(kind) { const row = layerDefaults(kind); S.project.layers.push(row); markDirty(); setSelection("layer", row.id); renderAll(); schedulePreview(); }
function addCaption() { const row = { id: uid("caption"), start_frame: 0, end_frame: S.project.duration_frames, text: "Caption", position: "bottom", scale: 1, font_size: 14 }; S.project.captions.push(row); markDirty(); setSelection("caption", row.id); renderAll(); schedulePreview(); }
function addTone() { const row = { id: uid("tone"), kind: "tone", start_frame: 0, end_frame: S.project.duration_frames, frequency_hz: 440, gain_milli: 120, pan_milli: 0 }; S.project.audio.push(row); markDirty(); setSelection("audio", row.id); renderAll(); }
function addSpeech() { const row = { id: uid("speech"), kind: "speech", start_frame: 0, end_frame: S.project.duration_frames, text: "FrameState speaks.", engine: "native", voice: "native-neutral-1", rate_wpm: 165, gain_milli: 850, pan_milli: 0 }; S.project.audio.push(row); markDirty(); setSelection("audio", row.id); renderAll(); }

function duplicateSelected() {
  const obj = currentObject(); if (!obj || !S.selected) return;
  const copy = clone(obj); copy.id = uid(obj.kind || S.selected.type);
  if (S.selected.type === "layer") { copy.z = Math.max(...S.project.layers.map(x => x.z || 0), 0) + 1; S.project.layers.push(copy); }
  else if (S.selected.type === "caption") S.project.captions.push(copy); else S.project.audio.push(copy);
  markDirty(); setSelection(S.selected.type, copy.id); renderAll(); schedulePreview();
}

function deleteSelected() {
  if (!S.selected) return;
  const key = S.selected.type === "layer" ? "layers" : S.selected.type === "caption" ? "captions" : "audio";
  S.project[key] = S.project[key].filter(x => x.id !== S.selected.id); S.selected = null; markDirty(); renderAll(); schedulePreview();
}

function renderProjectFields() {
  $("#projectTitle").value = S.project.title; $("#canvasW").value = S.project.canvas.width; $("#canvasH").value = S.project.canvas.height; $("#fps").value = S.project.canvas.fps; $("#duration").value = S.project.duration_frames; $("#background").value = S.project.background.join(",");
  $("#digest").textContent = S.digest || "canonical state"; $("#scrubber").max = Math.max(0, S.project.duration_frames - 1); $("#scrubber").value = Math.min(S.frame, S.project.duration_frames - 1); $("#frameLabel").textContent = `Frame ${S.frame} / ${S.project.duration_frames - 1}`;
  $("#assetLimit").textContent = `≤ ${Math.floor(S.assetLimit / 1024 / 1024)} MB`;
  $$('[data-effect]').forEach(ch => ch.checked = S.project.effects.includes(ch.dataset.effect));
}

function objectRow(type, row, meta) {
  const div = document.createElement("div"); div.className = "object-row" + (S.selected && S.selected.type === type && S.selected.id === row.id ? " selected" : "");
  const name = document.createElement("span"); name.textContent = row.id; const m = document.createElement("span"); m.className = "meta"; m.textContent = meta; div.append(name, m); if (type !== "media") div.onclick = () => setSelection(type, row.id); return div;
}

function renderLists() {
  const media = $("#mediaList"); media.innerHTML = ""; (S.project.media || []).forEach(x => media.appendChild(objectRow("media", x, `${x.kind} · ${x.path}`)));
  const layers = $("#layerList"); layers.innerHTML = ""; [...S.project.layers].sort((a,b) => (b.z||0)-(a.z||0)).forEach(x => layers.appendChild(objectRow("layer", x, `${x.kind} · z${x.z}`)));
  const caps = $("#captionList"); caps.innerHTML = ""; S.project.captions.forEach(x => caps.appendChild(objectRow("caption", x, `${x.start_frame}–${x.end_frame}`)));
  const audio = $("#audioList"); audio.innerHTML = ""; S.project.audio.forEach(x => audio.appendChild(objectRow("audio", x, x.kind)));
}

function field(label, key, value, opts = {}) {
  const wrap = document.createElement("label"); wrap.textContent = label;
  let input;
  if (opts.track && typeof value === "object") { input = document.createElement("textarea"); input.className = "track-editor"; input.value = JSON.stringify(value, null, 2); input.onchange = () => { try { opts.target[key] = JSON.parse(input.value); changed(); } catch(e) { toast(e.message, true); } }; }
  else if (opts.boolean) { input = document.createElement("input"); input.type = "checkbox"; input.checked = !!value; input.onchange = () => { opts.target[key] = input.checked; changed(); }; }
  else { input = document.createElement("input"); input.type = opts.type || (typeof value === "number" ? "number" : "text"); input.value = Array.isArray(value) ? value.join(",") : (value ?? ""); input.onchange = () => { let v = input.value; if (Array.isArray(value)) v = input.value.split(",").map(s => Number(s.trim())); else if (typeof value === "number") v = Number(v); opts.target[key] = v; changed(); }; }
  wrap.appendChild(input); return wrap;
}

function group(title, nodes) { const g = document.createElement("div"); g.className = "inspector-group"; const h = document.createElement("h4"); h.textContent = title; g.appendChild(h); nodes.filter(Boolean).forEach(n => g.appendChild(n)); return g; }
function pair(a,b) { const d = document.createElement("div"); d.className = "inline2"; d.append(a,b); return d; }
function changed() { markDirty(); renderProjectFields(); renderLists(); renderTimeline(); schedulePreview(); }

function renderInspector() {
  const host = $("#inspector"), title = $("#selectionTitle"); host.innerHTML = ""; const obj = currentObject(); $("#deleteBtn").disabled = !obj; $("#duplicateBtn").disabled = !obj;
  if (!obj || !S.selected) { title.textContent = "Nothing selected"; host.textContent = "Select a layer, caption or audio event."; return; }
  title.textContent = `${S.selected.type.toUpperCase()} · ${obj.id}`;
  host.appendChild(group("Identity", [field("ID", "id", obj.id, {target: obj}), obj.kind ? field("Kind", "kind", obj.kind, {target: obj}) : null]));
  if (S.selected.type === "layer") {
    host.appendChild(group("Timing", [pair(field("Start", "start_frame", obj.start_frame, {target: obj}), field("End", "end_frame", obj.end_frame, {target: obj})), field("Z", "z", obj.z, {target: obj})]));
    host.appendChild(group("Transform", [pair(field("X", "x", obj.x, {target: obj, track:true}), field("Y", "y", obj.y, {target: obj, track:true})), field("Opacity", "opacity_milli", obj.opacity_milli ?? 1000, {target: obj, track:true}), field("Rotation mdeg", "rotation_mdeg", obj.rotation_mdeg ?? 0, {target: obj, track:true})]));
    const spec = [];
    if (obj.color) spec.push(field("Color RGB", "color", obj.color, {target: obj}));
    if (obj.kind === "rect") spec.push(pair(field("Width", "w", obj.w, {target:obj,track:true}), field("Height", "h", obj.h, {target:obj,track:true})));
    if (obj.kind === "circle") spec.push(field("Radius", "radius", obj.radius, {target:obj,track:true}));
    if (obj.kind === "text") spec.push(field("Text", "text", obj.text, {target:obj}), pair(field("Scale", "scale", obj.scale ?? 1, {target:obj}), field("Font size", "font_size", obj.font_size ?? 16, {target:obj})));
    if (obj.kind === "particles") spec.push(pair(field("Count", "count", obj.count, {target:obj}), field("Seed", "seed", obj.seed, {target:obj})), pair(field("Spread X", "spread_x", obj.spread_x, {target:obj}), field("Spread Y", "spread_y", obj.spread_y, {target:obj})), pair(field("Speed", "speed", obj.speed, {target:obj}), field("Size", "size", obj.size, {target:obj})));
    if (obj.kind === "cube3d") spec.push(pair(field("Depth", "depth", obj.depth, {target:obj,track:true}), field("Size", "size", obj.size, {target:obj,track:true})), field("Rot X mdeg", "rot_x_mdeg", obj.rot_x_mdeg ?? 0, {target:obj,track:true}), field("Rot Y mdeg", "rot_y_mdeg", obj.rot_y_mdeg ?? 0, {target:obj,track:true}), field("Rot Z mdeg", "rot_z_mdeg", obj.rot_z_mdeg ?? 0, {target:obj,track:true}), field("Shadow", "shadow", obj.shadow ?? false, {target:obj,boolean:true}));
    if (["image","video","child"].includes(obj.kind)) spec.push(field("Media ID", "media_id", obj.media_id, {target:obj}), pair(field("Width", "w", obj.w, {target:obj,track:true}), field("Height", "h", obj.h, {target:obj,track:true})));
    if (["mesh3d","skinned_mesh3d"].includes(obj.kind)) spec.push(field("Media ID", "media_id", obj.media_id, {target:obj}), pair(field("Depth", "depth", obj.depth, {target:obj,track:true}), field("Size", "size", obj.size, {target:obj,track:true})));
    host.appendChild(group("Layer", spec));
  } else if (S.selected.type === "caption") {
    host.appendChild(group("Caption", [pair(field("Start", "start_frame", obj.start_frame, {target:obj}), field("End", "end_frame", obj.end_frame, {target:obj})), field("Text", "text", obj.text, {target:obj}), pair(field("Position", "position", obj.position, {target:obj}), field("Scale", "scale", obj.scale, {target:obj})), field("Font size", "font_size", obj.font_size ?? 14, {target:obj})]));
  } else {
    const rows = [pair(field("Start", "start_frame", obj.start_frame, {target:obj}), field("End", "end_frame", obj.end_frame, {target:obj})), field("Gain milli", "gain_milli", obj.gain_milli ?? 1000, {target:obj,track:true}), field("Pan milli", "pan_milli", obj.pan_milli ?? 0, {target:obj,track:true})];
    if (obj.kind === "tone") rows.push(field("Frequency Hz", "frequency_hz", obj.frequency_hz ?? 440, {target:obj}));
    if (obj.kind === "speech") rows.push(field("Text", "text", obj.text, {target:obj}), field("Engine", "engine", obj.engine ?? "native", {target:obj}), field("Voice", "voice", obj.voice ?? "native-neutral-1", {target:obj}), field("Rate WPM", "rate_wpm", obj.rate_wpm ?? 165, {target:obj}));
    if (obj.kind === "file") rows.push(field("Project-relative path", "path", obj.path, {target:obj}));
    host.appendChild(group("Audio", rows));
  }
}

function renderTimeline() {
  const host = $("#timelineRows"); host.innerHTML = ""; const dur = Math.max(1, S.project.duration_frames);
  const add = (label, start, end, cls="") => { const row = document.createElement("div"); row.className = "timeline-row"; const l = document.createElement("div"); l.className="timeline-label"; l.textContent=label; const tr=document.createElement("div"); tr.className="timeline-track"; const bar=document.createElement("div"); bar.className="timeline-bar "+cls; bar.style.left=`${100*start/dur}%`; bar.style.width=`${100*Math.max(1,end-start)/dur}%`; const cur=document.createElement("div"); cur.className="timeline-cursor"; cur.style.left=`${100*S.frame/dur}%`; tr.append(bar,cur); row.append(l,tr); host.appendChild(row); };
  [...S.project.layers].sort((a,b)=>(b.z||0)-(a.z||0)).forEach(x=>add(x.id,x.start_frame,x.end_frame)); S.project.captions.forEach(x=>add(`CC ${x.id}`,x.start_frame,x.end_frame,"caption")); S.project.audio.forEach(x=>add(`♪ ${x.id}`,x.start_frame,x.end_frame,"audio"));
}

function renderAll() { renderProjectFields(); renderLists(); renderInspector(); renderTimeline(); }

let previewDebounce = null;
function schedulePreview() { clearTimeout(previewDebounce); previewDebounce = setTimeout(preview, 120); }
async function preview() {
  const token = ++S.previewToken; $("#previewStatus").textContent = "rendering actual frame…";
  try { const r = await api("/api/preview", {project:S.project, frame:S.frame, mode:$("#realizationMode").value}); if (token !== S.previewToken) return; $("#preview").src = r.image; $("#previewStatus").textContent = `${r.mode} · ${r.frame_state.pixel_digest.slice(0,22)}…`; }
  catch(e){ if(token!==S.previewToken)return; $("#previewStatus").textContent = e.message; toast(e.message,true); }
}

function bytesToBase64(buffer) {
  const bytes = new Uint8Array(buffer); const chunk = 0x8000; let binary = "";
  for (let i=0; i<bytes.length; i+=chunk) binary += String.fromCharCode(...bytes.subarray(i, Math.min(bytes.length, i+chunk)));
  return btoa(binary);
}

async function importAsset() {
  const file = $("#assetFile").files[0]; if (!file) { toast("Choose a file first", true); return; }
  if (file.size > S.assetLimit) { toast(`Asset is ${Math.ceil(file.size/1024/1024)} MB; Studio intake limit is ${Math.floor(S.assetLimit/1024/1024)} MB`, true); return; }
  const btn = $("#importAssetBtn"); btn.disabled = true; btn.textContent = "Importing…";
  try {
    const data = bytesToBase64(await file.arrayBuffer());
    const r = await api("/api/import", {project:S.project, name:file.name, kind:$("#assetKind").value, data});
    S.project = r.project; S.digest = r.project_digest; markDirty(); renderAll(); $("#jsonEditor").value = JSON.stringify(S.project,null,2); $("#evidence").textContent = JSON.stringify(r.import_receipt,null,2); $("#assetFile").value = ""; schedulePreview(); toast(`Imported ${file.name}`);
  } catch(e) { toast(e.message,true); }
  finally { btn.disabled = false; btn.textContent = "Import asset"; }
}

async function normalizeProject(showToast=true) {
  try { const r = await api("/api/normalize", {project:S.project}); S.project=r.project; S.digest=r.project_digest; if (S.frame>=S.project.duration_frames) S.frame=S.project.duration_frames-1; renderAll(); if(showToast)toast("Canonical state valid"); return true; } catch(e){ toast(e.message,true); return false; }
}

async function save() { if(!await normalizeProject(false))return; try{const r=await api("/api/save",{project:S.project});S.digest=r.project_digest;markDirty(false);renderProjectFields();$("#evidence").textContent=JSON.stringify(r,null,2);toast(`Saved ${r.path}`);}catch(e){toast(e.message,true);} }
async function review() { try{const r=await api("/api/review",{project:S.project});$("#evidence").textContent=JSON.stringify(r,null,2);toast("Mechanical review complete");}catch(e){toast(e.message,true);} }
async function applyPrompt() { const text=$("#promptText").value.trim(); if(!text)return; try{const r=await api("/api/prompt",{project:S.project,text});S.project=r.project;S.digest=r.project_digest;markDirty();renderAll();$("#promptResult").textContent=JSON.stringify({status:r.plan.status,recognized:r.plan.recognized,ambiguous:r.plan.ambiguous,unresolved:r.plan.unresolved_fragments,operations:r.applied_operations},null,2);schedulePreview();toast(r.plan.status);}catch(e){toast(e.message,true);} }
async function finalRender() { if(!await normalizeProject(false))return; const btn=$("#renderBtn");btn.disabled=true;btn.textContent="Rendering…";try{const short=(S.digest||"").replace("sha256:","").slice(0,12);const name=`${S.project.id}-${short||"render"}`;const r=await api("/api/render",{project:S.project,name,profile:"h264",mode:$("#realizationMode").value});$("#evidence").textContent=JSON.stringify(r,null,2);toast(`Render complete: ${r.output}`);}catch(e){toast(e.message,true);}finally{btn.disabled=false;btn.textContent="Render Final";} }

function togglePlay() {
  S.playing=!S.playing; $("#playBtn").textContent=S.playing?"❚❚":"▶"; clearInterval(S.timer);
  if(S.playing){const ms=Math.max(40,1000/S.project.canvas.fps);S.timer=setInterval(()=>{S.frame=(S.frame+1)%S.project.duration_frames;$("#scrubber").value=S.frame;renderProjectFields();renderTimeline();preview();},ms);}
}

function bindProjectInput(sel, fn) { $(sel).onchange=()=>{fn();markDirty();renderAll();schedulePreview();}; }
function bind() {
  $$('[data-add-layer]').forEach(b=>b.onclick=()=>addLayer(b.dataset.addLayer)); $("#addCaptionBtn").onclick=addCaption; $("#addToneBtn").onclick=addTone; $("#addSpeechBtn").onclick=addSpeech; $("#duplicateBtn").onclick=duplicateSelected; $("#deleteBtn").onclick=deleteSelected; $("#importAssetBtn").onclick=importAsset;
  bindProjectInput("#projectTitle",()=>S.project.title=$("#projectTitle").value); bindProjectInput("#canvasW",()=>S.project.canvas.width=Number($("#canvasW").value)); bindProjectInput("#canvasH",()=>S.project.canvas.height=Number($("#canvasH").value)); bindProjectInput("#fps",()=>S.project.canvas.fps=Number($("#fps").value)); bindProjectInput("#duration",()=>S.project.duration_frames=Number($("#duration").value)); bindProjectInput("#background",()=>S.project.background=$("#background").value.split(",").map(x=>Number(x.trim())));
  $$('[data-effect]').forEach(ch=>ch.onchange=()=>{const e=ch.dataset.effect;S.project.effects=S.project.effects.filter(x=>x!==e);if(ch.checked)S.project.effects.push(e);markDirty();schedulePreview();});
  $("#scrubber").oninput=()=>{S.frame=Number($("#scrubber").value);renderProjectFields();renderTimeline();schedulePreview();}; $("#realizationMode").onchange=schedulePreview; $("#playBtn").onclick=togglePlay;
  $("#saveBtn").onclick=save; $("#reviewBtn").onclick=review; $("#promptBtn").onclick=applyPrompt; $("#renderBtn").onclick=finalRender;
  $("#refreshJsonBtn").onclick=()=>{$("#jsonEditor").value=JSON.stringify(S.project,null,2);toast("JSON refreshed from canonical state");};
  $("#applyJsonBtn").onclick=async()=>{try{S.project=JSON.parse($("#jsonEditor").value);if(await normalizeProject(false)){markDirty();$("#jsonEditor").value=JSON.stringify(S.project,null,2);schedulePreview();toast("JSON applied to canonical state");}}catch(e){toast(e.message,true);}};
  document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="s"){e.preventDefault();save();}if(e.code==="Space"&&!["INPUT","TEXTAREA","SELECT"].includes(document.activeElement.tagName)){e.preventDefault();togglePlay();}});
}

async function boot() {
  bind(); try { const st=await api("/api/state");S.project=st.project;S.digest=st.project_digest;S.assetLimit=st.asset_limit_bytes||S.assetLimit;S.frame=0;markDirty(false);renderAll();$("#jsonEditor").value=JSON.stringify(S.project,null,2);$("#evidence").textContent=JSON.stringify({machine:st.machine,project_path:st.project_path,asset_limit_bytes:st.asset_limit_bytes,truth_boundary:st.truth_boundary},null,2);preview(); } catch(e){toast(e.message,true);$("#evidence").textContent=e.stack||e.message;}
}
boot();
