// node tests/md_test.js
const assert = require("assert");
const { render } = require("../assets/recordatorios/md.js");

assert.strictEqual(render("Hola **mundo** y *tú* con `x`"), "<p>Hola <strong>mundo</strong> y <em>tú</em> con <code>x</code></p>");
assert.strictEqual(render("<img src=x onerror=alert(1)>"), "<p>&lt;img src=x onerror=alert(1)&gt;</p>");
assert.strictEqual(render("- a\n- b"), "<ul><li>a</li><li>b</li></ul>");
assert.strictEqual(render("1. a\n2. b"), "<ol><li>a</li><li>b</li></ol>");
assert.strictEqual(render("## Título"), "<h4>Título</h4>");
assert.strictEqual(render("```\n<b>\n```"), "<pre><code>&lt;b&gt;</code></pre>");
assert.strictEqual(
  render("| ID | Título |\n|----|--------|\n| 2 | **Tomar** |\n\nNota"),
  "<table><thead><tr><th>ID</th><th>Título</th></tr></thead><tbody><tr><td>2</td><td><strong>Tomar</strong></td></tr></tbody></table><p>Nota</p>",
);
assert.strictEqual(render("a\nb"), "<p>a<br>b</p>");
console.log("md ok");
