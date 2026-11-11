// Cron de 5 campos: "min hora díaMes mes díaSemana" (0 = domingo).
// kinds: once, daily, weekdays, days, hours, min, custom
const Cron = (() => {
  const LETTER = "DLMXJVS";
  const hm = (time) => time.split(":").map(Number);

  // f = {kind, date "YYYY-MM-DD", time "HH:MM", days [0-6], n, cron}; null si falta algún dato
  function toCron(f) {
    const [h, m] = f.time ? hm(f.time) : [0, 0];
    switch (f.kind) {
      case "once": {
        if (!f.date || !f.time) return null;
        const [, mo, d] = f.date.split("-").map(Number);
        return `${m} ${h} ${d} ${mo} *`;
      }
      case "daily": return f.time ? `${m} ${h} * * *` : null;
      case "weekdays": return f.time && f.days.length ? `${m} ${h} * * ${[...f.days].sort().join(",")}` : null;
      case "days": return f.time && f.n > 0 ? `${m} ${h} */${f.n} * *` : null;
      case "hours": return f.n > 0 ? `0 */${f.n} * * *` : null;
      case "min": return f.n > 0 ? `*/${f.n} * * * *` : null;
      case "custom": return f.cron && f.cron.trim().split(/\s+/).length === 5 ? f.cron.trim() : null;
    }
    return null;
  }

  // Inverso de toCron. `ref` aporta el año para "once" (cron no lo guarda).
  function fromCron(expr, ref = new Date()) {
    const x = expr.trim().split(/\s+/), custom = { kind: "custom", cron: expr };
    if (x.length !== 5) return custom;
    const [mi, h, d, mo, w] = x, num = /^\d+$/, step = /^\*\/(\d+)$/;
    const pad = (v) => String(v).padStart(2, "0");
    const time = num.test(mi) && num.test(h) ? `${pad(h)}:${pad(mi)}` : null;
    if (time) {
      if (num.test(d) && num.test(mo) && w === "*") return { kind: "once", time, date: `${ref.getFullYear()}-${pad(mo)}-${pad(d)}` };
      if (d === "*" && mo === "*" && w === "*") return { kind: "daily", time };
      if (d === "*" && mo === "*" && /^[0-6](,[0-6])*$/.test(w)) return { kind: "weekdays", time, days: w.split(",").map(Number) };
      if (step.test(d) && mo === "*" && w === "*") return { kind: "days", time, n: +d.match(step)[1] };
    }
    const rest = (...v) => v.every((c) => c === "*");
    if (mi === "0" && step.test(h) && rest(d, mo, w)) return { kind: "hours", n: +h.match(step)[1] };
    if (step.test(mi) && rest(h, d, mo, w)) return { kind: "min", n: +mi.match(step)[1] };
    return custom;
  }

  function describe(expr) {
    const f = fromCron(expr);
    switch (f.kind) {
      case "once": return "Una vez";
      case "daily": return "Cada día";
      case "weekdays": return f.days.map((i) => LETTER[i]).join(" ");
      case "days": return `Cada ${f.n} días`;
      case "hours": return `Cada ${f.n} h`;
      case "min": return `Cada ${f.n} min`;
    }
    return expr;
  }

  return { toCron, fromCron, describe };
})();
if (typeof module !== "undefined") module.exports = Cron;
