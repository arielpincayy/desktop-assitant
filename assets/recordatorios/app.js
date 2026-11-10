const $ = (id) => document.getElementById(id);
const q = new URLSearchParams(location.search);
const API = q.get("api"), USER = q.get("user");
const now = new Date();
const at = (dayOff, h, m) => { const d = new Date(now); d.setDate(d.getDate() + dayOff); d.setHours(h, m, 0, 0); return d; };
const iso = (d) => new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 16);

let items = [], editing = null, trashed = null, toastTimer, showDone = false;

async function api(method, path, body) {
  try {
    const res = await fetch(API + path, {
      method, headers: { "Content-Type": "application/json" },
      body: body && JSON.stringify(body),
    });
    if (!res.ok) throw new Error(res.status);
    return res.status === 204 ? null : res.json();
  } catch {
    toast("No se pudo conectar con la API", false);
    throw 0;
  }
}
async function load() {
  const rows = await api("GET", "/reminders?user_id=" + encodeURIComponent(USER) + "&limit=500");
  items = rows.map((r) => ({ id: r.id, title: r.title, desc: r.description || "", schedule: r.schedule, when: new Date(r.next_run), done: r.status === "done" }));
  render();
}
const save = (method, path, body) => api(method, path, body).then(load).catch(() => {});

$("today").textContent = now.toLocaleDateString("es", { weekday: "long", day: "numeric", month: "long" })
  .replace(/^./, (c) => c.toUpperCase());

const fmtTime = (d) => d.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit", hour12: false });
const dayLabel = (d) => {
  const diff = Math.round((new Date(d).setHours(0, 0, 0, 0) - new Date(now).setHours(0, 0, 0, 0)) / 864e5);
  if (diff === 0) return "Hoy";
  if (diff === 1) return "Mañana";
  return d.toLocaleDateString("es", { weekday: "long", day: "numeric", month: "short" });
};
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function row(r) {
  return `<div class="row${r.done ? " done" : ""}" data-id="${r.id}">
    <input type="checkbox" ${r.done ? "checked" : ""} aria-label="Marcar como hecho: ${esc(r.title)}">
    <div class="time">${fmtTime(r.when)}</div>
    <div class="body"><b>${esc(r.title)}</b><span class="rec">${esc(Cron.describe(r.schedule))}</span>${r.desc ? `<span>${esc(r.desc)}</span>` : ""}</div>
    <div class="tools">
      <button class="edit" aria-label="Editar ${esc(r.title)}">✎</button>
      <button class="del" aria-label="Eliminar ${esc(r.title)}">🗑</button>
    </div></div>`;
}

function render() {
  const sorted = [...items].sort((a, b) => a.when - b.when);
  const open = sorted.filter((r) => !r.done), done = sorted.filter((r) => r.done);
  let html = "", last = "";
  for (const r of open) {
    const l = dayLabel(r.when);
    if (l !== last) { html += `<div class="day">${l}</div>`; last = l; }
    html += row(r);
  }
  if (!items.length) html = `<div class="empty"><img src="../fantasmita.svg" alt=""><p>No tienes recordatorios.<br>Escribe el primero arriba.</p></div>`;
  if (done.length) html += `<button class="fold" id="fold">${showDone ? "▾" : "▸"} Hechos (${done.length})</button>` + (showDone ? done.map(row).join("") : "");
  $("list").innerHTML = html;
}

// Crear rápido: Enter abre el formulario con el título ya escrito
$("quick").onsubmit = (e) => { e.preventDefault(); openForm(null, $("quick-input").value.trim()); $("quick-input").value = ""; };

function openForm(r, title = "") {
  editing = r;
  $("dlg-title").textContent = r ? "Editar recordatorio" : "Nuevo recordatorio";
  $("save").textContent = r ? "Guardar cambios" : "Guardar recordatorio";
  $("f-title").value = r ? r.title : title;
  $("f-desc").value = r ? r.desc : "";
  setWhen(r ? Cron.fromCron(r.schedule, r.when) : { kind: "once", ...dt(new Date(now.getTime() + 36e5)) });
  $("dlg").show(); // no modal: así queda dentro de .win y no de la pantalla
  $("f-title").focus();
}
const dt = (d) => ({ date: iso(d).slice(0, 10), time: iso(d).slice(11, 16) });
const KINDS = () => $("dlg").querySelectorAll("[data-k]");
function showKind() {
  const k = $("f-kind").value;
  for (const el of KINDS()) {
    const on = el.dataset.k.split(" ").includes(k);
    el.hidden = !on;
    el.querySelectorAll("input").forEach((i) => { if (i.type !== "checkbox") i.disabled = !on; });
  }
}
$("f-kind").onchange = showKind;
function setWhen(f) {
  $("f-kind").value = f.kind;
  $("f-date").value = f.date || dt(now).date;
  $("f-time").value = f.time || "09:00";
  $("f-n").value = f.n || 1;
  $("f-cron").value = f.cron || "";
  $("dlg").querySelectorAll(".wd input").forEach((c) => (c.checked = (f.days || []).includes(+c.value)));
  showKind();
}
const getSchedule = () => Cron.toCron({
  kind: $("f-kind").value, date: $("f-date").value, time: $("f-time").value, n: +$("f-n").value,
  cron: $("f-cron").value, days: [...document.querySelectorAll(".wd input:checked")].map((c) => +c.value),
});

$("dlg").onkeydown = (e) => { if (e.key === "Escape") $("dlg").close(); };
$("cancel").onclick = () => $("dlg").close();
document.querySelector(".chips").onclick = (e) => {
  const k = e.target.dataset.in; if (!k) return;
  setWhen({ kind: "once", ...dt(k === "tomorrow" ? at(1, 9, 0) : new Date(Date.now() + k * 6e4)) });
};
$("form").onsubmit = (e) => {
  const schedule = getSchedule();
  if (!schedule) { e.preventDefault(); return toast("Completa la repetición (p. ej. elige algún día)", false); }
  const data = { title: $("f-title").value.trim(), description: $("f-desc").value.trim() || null, schedule };
  if (editing) save("PATCH", "/reminders/" + editing.id, data);
  else save("POST", "/reminders", { user_id: USER, ...data });
};

$("list").onclick = (e) => {
  if (e.target.id === "fold") { showDone = !showDone; return render(); }
  const el = e.target.closest(".row"); if (!el) return;
  const r = items.find((x) => x.id == el.dataset.id);
  if (e.target.type === "checkbox") save("PATCH", "/reminders/" + r.id, { status: e.target.checked ? "done" : "pending" });
  else if (e.target.closest(".edit")) openForm(r);
  else if (e.target.closest(".del")) {
    el.classList.add("out");
    // Se borra en la API al instante (cerrar la ventana no lo deja pendiente); Deshacer lo vuelve a crear.
    setTimeout(() => api("DELETE", "/reminders/" + r.id).then(() => { trashed = r; return load(); }).then(() => toast("Recordatorio eliminado")).catch(() => {}), 200);
  }
};

function toast(msg, undo = true) {
  $("toast-msg").textContent = msg; $("toast").hidden = false; $("undo").hidden = !undo;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => ($("toast").hidden = true), 5000);
}
$("close-toast").onclick = () => ($("toast").hidden = true);
$("undo").onclick = () => {
  $("toast").hidden = true;
  const r = trashed; trashed = null;
  if (r) save("POST", "/reminders", { user_id: USER, title: r.title, description: r.desc || null, schedule: r.schedule, status: r.done ? "done" : "pending" });
};

load().catch(() => {});
