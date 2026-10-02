// Fails if a tracked file looks like it contains a credential. Never prints the match itself,
// only the file, line and kind, so a real secret cannot leak into CI logs.
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const PATTERNS = [
  ["private key block", /-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----/],
  ["GitHub token", /\bgh[pousr]_[A-Za-z0-9]{30,}\b/],
  ["GitHub fine-grained token", /\bgithub_pat_[A-Za-z0-9_]{40,}\b/],
  ["AWS access key id", /\bAKIA[0-9A-Z]{16}\b/],
  ["Slack token", /\bxox[abprs]-[A-Za-z0-9-]{10,}\b/],
  ["Vercel token assignment", /VERCEL_TOKEN\s*[=:]\s*["']?[A-Za-z0-9]{20,}/],
  [
    "API key assignment",
    /\b(?:api[_-]?key|secret|password)\s*[=:]\s*["'][A-Za-z0-9/+_-]{24,}["']/i,
  ],
  ["bearer token", /\bBearer\s+[A-Za-z0-9._-]{30,}/],
];
const SKIP = /(^|\/)(package-lock\.json|scripts\/secret-scan\.mjs)$|\.(png|jpg|ico|woff2?)$/;

const files = execFileSync("git", ["ls-files", "-z"], { encoding: "utf8" })
  .split("\0")
  .filter((f) => f && !SKIP.test(f));

const hits = [];
for (const file of files) {
  let text;
  try {
    text = readFileSync(file, "utf8");
  } catch {
    continue;
  }
  text.split("\n").forEach((line, i) => {
    for (const [kind, re] of PATTERNS) if (re.test(line)) hits.push(`${file}:${i + 1}: ${kind}`);
  });
}

const tracked = files.filter((f) => /(^|\/)\.env(\.|$)/.test(f) && !f.endsWith(".env.example"));
for (const f of tracked) hits.push(`${f}: environment file is tracked`);

if (hits.length > 0) {
  console.error(hits.join("\n"));
  process.exit(1);
}
console.log(`secret scan ok: ${files.length} tracked files`);
