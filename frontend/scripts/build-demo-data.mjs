import fs from "node:fs";

const input = process.argv[2] || "raw_export.json";
const rows = JSON.parse(fs.readFileSync(input, "utf8"));
const raw = rows[0].export;
const data = typeof raw === "string" ? JSON.parse(raw) : raw;

const OWNER = data.user.email;
const EMAIL = /[\w.+-]+@[\w-]+(\.[\w-]+)+/g;
const scrub = (s) =>
  typeof s === "string" ? s.replace(EMAIL, (m) => (m === OWNER ? m : "a teammate")) : s;

// drop empty board, test tasks, and the absurd-revenue estimate
data.boards = data.boards.filter((b) => b.id !== 33);
data.tasks = data.tasks.filter((t) => t.created_by === data.user.id);
data.cost_estimates = data.cost_estimates.filter((c) => c.id !== 1);

// strip heavy PNGs, keep draw.io XML
for (const d of data.diagrams) if (d.model?.edited) delete d.model.edited.png;

// only your own activity, with other people's emails removed
data.board_activity = data.board_activity
  .filter((a) => a.user_id === data.user.id)
  .map((a) => ({ ...a, summary: scrub(a.summary) }));

fs.mkdirSync("src/demo", { recursive: true });
fs.writeFileSync("src/demo/demoAccount.json", JSON.stringify(data));

for (const [k, v] of Object.entries(data)) {
  console.log(k.padEnd(20), Array.isArray(v) ? v.length + " rows" : "1 object");
}
console.log("size:", (fs.statSync("src/demo/demoAccount.json").size / 1024).toFixed(0), "KB");