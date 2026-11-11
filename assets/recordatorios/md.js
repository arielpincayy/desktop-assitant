// Markdown mínimo para el chat: código, títulos, listas, tablas, **negrita**, *cursiva*, `código`.
// Escapa todo el HTML antes de formatear, así que el resultado es seguro para innerHTML.
// Sin enlaces a propósito: un clic navegaría la ventana fuera de la app.
const Md = (() => {
  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, "$1<em>$2</em>");
  const cells = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
  const isSep = (l) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(l || "");
  const LI = /^\s*([-*]|\d+\.)\s+(.*)/;

  function render(text) {
    const lines = text.replace(/\r/g, "").split("\n");
    let out = "", i = 0;
    while (i < lines.length) {
      const l = lines[i];
      let m;
      if (/^\s*```/.test(l)) {
        const code = [];
        for (i++; i < lines.length && !/^\s*```/.test(lines[i]); i++) code.push(lines[i]);
        i++;
        out += `<pre><code>${esc(code.join("\n"))}</code></pre>`;
      } else if (l.includes("|") && isSep(lines[i + 1])) {
        const head = cells(l);
        i += 2;
        let body = "";
        for (; i < lines.length && lines[i].includes("|"); i++)
          body += "<tr>" + cells(lines[i]).map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>";
        out += `<table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table>`;
      } else if ((m = l.match(/^#{1,6}\s+(.*)/))) {
        out += `<h4>${inline(m[1])}</h4>`;
        i++;
      } else if (LI.test(l)) {
        const tag = /^\s*\d/.test(l) ? "ol" : "ul";
        let items = "";
        for (; i < lines.length && LI.test(lines[i]); i++) items += `<li>${inline(lines[i].match(LI)[2])}</li>`;
        out += `<${tag}>${items}</${tag}>`;
      } else if (!l.trim()) {
        i++;
      } else {
        const para = [];
        for (; i < lines.length && lines[i].trim() && !/^\s*(```|#{1,6}\s)/.test(lines[i]) && !LI.test(lines[i]) && !(lines[i].includes("|") && isSep(lines[i + 1])); i++)
          para.push(inline(lines[i]));
        out += `<p>${para.join("<br>")}</p>`;
      }
    }
    return out;
  }
  return { render };
})();
if (typeof module !== "undefined") module.exports = Md;
