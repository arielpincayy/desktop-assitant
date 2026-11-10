// node tests/cron_test.js
const assert = require("assert");
const { toCron, fromCron, describe } = require("../assets/recordatorios/cron.js");

const cases = [
  [{ kind: "once", date: "2026-11-10", time: "17:30" }, "0 30 17 10 11 *"],
  [{ kind: "daily", time: "09:00" }, "0 0 9 * * *"],
  [{ kind: "weekdays", time: "08:05", days: [5, 1, 3] }, "0 5 8 * * 1,3,5"],
  [{ kind: "days", time: "07:00", n: 3 }, "0 0 7 */3 * *"],
  [{ kind: "hours", n: 2 }, "0 0 */2 * * *"],
  [{ kind: "min", n: 15 }, "0 */15 * * * *"],
  [{ kind: "sec", n: 30 }, "*/30 * * * * *"],
  [{ kind: "custom", cron: "0 0 12 1 1 *" }, "0 0 12 1 1 *"],
];
for (const [form, cron] of cases) {
  assert.strictEqual(toCron(form), cron);
  const back = fromCron(cron, new Date(2026, 0, 1));
  // ida y vuelta: el cron resultante debe ser idéntico
  assert.strictEqual(toCron(back), cron, cron);
}
assert.strictEqual(fromCron("0 0 12 1 1 *").kind, "once");
assert.strictEqual(fromCron("0 0 9 * * 1-5").kind, "custom");
assert.strictEqual(fromCron("* * *").kind, "custom");
assert.strictEqual(toCron({ kind: "weekdays", time: "08:00", days: [] }), null);
assert.strictEqual(toCron({ kind: "min", n: 0 }), null);
assert.strictEqual(describe("0 5 8 * * 1,3,5"), "L X V");
console.log("ok");
