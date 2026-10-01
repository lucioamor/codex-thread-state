"use strict";
const $ = id => document.getElementById(id);
const token = location.hash.slice(1) || sessionStorage.getItem("thread-state-token") || "";
if(token) sessionStorage.setItem("thread-state-token", token);
history.replaceState(null, "", location.pathname);
let data, draft, saved, effectiveIcons = {}, pickerKey, category = "Símbolos", timer, generation = 0, busy = false;
const core = ["running", "waiting_on_user", "interrupted", "paused", "pending", "completed", "failed", "blocked", "usage_limited", "budget_limited", "unknown"];
const featured = ["running", "waiting_on_user", "interrupted", "completed"];
const clone = value => JSON.parse(JSON.stringify(value));
const norm = value => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const node = (tag, className, text) => { const e = document.createElement(tag); if(className) e.className = className; if(text !== undefined) e.textContent = text; return e; };
async function api(path, body) {
  const options = {headers:{"X-Thread-State-Token":token}};
  if(body !== undefined) { options.method = "POST"; options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); }
  const response = await fetch(path, options);
  const result = await response.json();
  if(!response.ok) throw new Error(result.error || "Não foi possível completar a ação.");
  return result;
}
function feedback(message, error = false) { $("feedback").textContent = message; $("feedback").classList.toggle("error", error); }
function dirty() { return JSON.stringify(draft) !== JSON.stringify(saved); }
function theme() { return data.themes.find(item => item.id === draft.style); }
function updateSave() {
  $("save").disabled = busy || !dirty();
  $("undo").disabled = busy || !data.canUndo || dirty();
  $("dirty-dot").classList.toggle("dirty", dirty());
  $("save-state").textContent = busy ? "Salvando…" : dirty() ? "Prévia · alterações não salvas" : "Preferências salvas";
}
function drawThemes() {
  $("themes").replaceChildren();
  data.themes.forEach(item => {
    const b = node("button", "theme"); b.type = "button"; b.setAttribute("aria-pressed", String(item.id === draft.style)); b.setAttribute("aria-label", item.name);
    b.append(node("span", "theme-icons", [item.icons.running, item.icons.waiting_on_user, item.icons.completed].join(" ")),
      node("span", "theme-name", item.name), node("span", "theme-description", item.description));
    if(item.id === draft.style) b.append(node("span", "theme-check", "✓"));
    b.addEventListener("click", () => { draft.style = item.id; draft.icons = {}; changed(); drawThemes(); });
    $("themes").append(b);
  });
}
function drawMarkers() {
  $("markers").replaceChildren(); $("extra-markers").replaceChildren();
  [...core, ...Object.keys(data.labels).filter(key => !core.includes(key))].forEach(key => {
    const row = node("div", "marker-row"); row.classList.toggle("customized", key in draft.icons);
    const button = node("button", "marker-button", effectiveIcons[key] || theme().icons[key]); button.type = "button";
    button.setAttribute("aria-label", "Personalizar: " + data.labels[key]); button.title = "Personalizar " + data.labels[key];
    button.addEventListener("click", () => openPicker(key));
    row.append(node("span", "marker-label", data.labels[key]), button);
    $(core.includes(key) ? "markers" : "extra-markers").append(row);
  });
}
function changed() {
  generation++; clearTimeout(timer); feedback("");
  $("enabled").checked = draft.enabled; $("power-label").textContent = draft.enabled ? "Marcadores ativos" : "Marcadores desligados";
  $("max-badges").value = draft.max_badges; $("max-badges").disabled = draft.style === "minimal";
  $("minimal-note").hidden = draft.style !== "minimal"; $("disabled-note").hidden = draft.enabled;
  $("preview-theme").textContent = theme().name + (Object.keys(draft.icons).length ? " · seu toque" : "");
  $("palette-note").textContent = theme().note; $("palette-note").hidden = !theme().note;
  effectiveIcons = {...theme().icons, ...draft.icons}; drawMarkers(); updateSave();
  timer = setTimeout(preview, 120);
}
async function preview() {
  const request = ++generation;
  try {
    const result = await api("/api/preview", {settings:clone(draft)});
    if(request !== generation) return;
    effectiveIcons = result.icons; drawMarkers();
    $("preview-list").replaceChildren(); $("all-preview").replaceChildren();
    const add = (row, target) => { const item = node("div", "preview-row"); item.append(node("span", row.error ? "preview-error" : "preview-title", row.error ? "Título longo demais para o limite atual" : row.title), node("span", "preview-label", row.label)); $(target).append(item); };
    featured.forEach(key => add(result.rows.find(row => row.state === key), "preview-list"));
    result.rows.forEach(row => add(row, "all-preview"));
  } catch(error) { if(request === generation) feedback(error.message, true); }
}
function adopt(state) {
  data = state; draft = clone(data.settings); saved = clone(data.settings);
  drawThemes(); changed();
}
async function load() {
  try { adopt(await api("/api/state")); }
  catch(error) { feedback(error.message, true); $("save-state").textContent = "Painel desconectado"; }
}
async function persist(undo = false) {
  if(busy) return; busy = true; $("app").inert = true; updateSave();
  try {
    const result = await api(undo ? "/api/undo" : "/api/settings", {settings:clone(draft), revision:data.revision});
    adopt(result.state); feedback(undo ? "Preferências anteriores restauradas." : "Preferências salvas. Valem nos próximos eventos das conversas.");
  } catch(error) { feedback(error.message, true); }
  finally { busy = false; $("app").inert = false; updateSave(); }
}
function drawPicker() {
  $("picker-tabs").replaceChildren();
  Object.keys(data.picker).forEach(name => {
    const b = node("button", "picker-tab", name); b.type = "button"; b.setAttribute("aria-pressed", String(name === category));
    b.addEventListener("click", () => { category = name; drawPicker(); }); $("picker-tabs").append(b);
  });
  $("picker-grid").replaceChildren();
  const search = norm($("picker-search").value);
  const items = data.picker[category].filter(([symbol, label]) => norm(label + symbol).includes(search));
  items.forEach(([symbol, label]) => {
    const b = node("button", "picker-symbol", symbol); b.type = "button"; b.title = label; b.setAttribute("aria-label", label + " " + symbol);
    b.addEventListener("click", () => choose(symbol)); $("picker-grid").append(b);
  });
  if(!items.length) $("picker-grid").append(node("p", "picker-empty", "Nenhum símbolo nesta categoria. Você também pode colar um abaixo."));
}
function openPicker(key) {
  pickerKey = key; $("picker-title").textContent = data.labels[key]; $("custom-symbol").value = effectiveIcons[key];
  $("picker-search").value = ""; $("picker-error").textContent = ""; drawPicker(); $("picker").showModal(); $("picker-search").focus();
}
async function choose(symbol) {
  const request = JSON.stringify(draft);
  const candidate = clone(draft); candidate.icons[pickerKey] = symbol;
  $("picker").inert = true;
  try { await api("/api/preview", {settings:candidate}); if(request !== JSON.stringify(draft) || !$("picker").open) return; draft = candidate; $("picker").close(); changed(); }
  catch(error) { $("picker-error").textContent = error.message; }
  finally { $("picker").inert = false; }
}
$("enabled").addEventListener("change", event => { draft.enabled = event.target.checked; changed(); });
$("max-badges").addEventListener("change", event => { draft.max_badges = Number(event.target.value); changed(); });
$("reset-icons").addEventListener("click", () => { draft.icons = {}; changed(); });
$("default-symbol").addEventListener("click", () => { delete draft.icons[pickerKey]; $("picker").close(); changed(); });
$("close-picker").addEventListener("click", () => $("picker").close());
$("picker-search").addEventListener("input", drawPicker);
$("apply-symbol").addEventListener("click", () => choose($("custom-symbol").value));
$("custom-symbol").addEventListener("keydown", event => { if(event.key === "Enter") { event.preventDefault(); choose(event.target.value); } });
$("save").addEventListener("click", () => persist()); $("undo").addEventListener("click", () => persist(true));
$("reload").addEventListener("click", load);
document.querySelector(".brand").addEventListener("click", event => event.preventDefault());
window.addEventListener("beforeunload", event => { if(data && dirty()) { event.preventDefault(); event.returnValue = ""; } });
load();
