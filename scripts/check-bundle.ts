import fs from 'node:fs';
import path from 'node:path';

/**
 * CI gate per Design Doc v0.1:
 * "No runtime network calls, ever; a CI check greps the built bundle for `fetch(` outside the service worker."
 */
const distDir = path.resolve(process.cwd(), 'dist');

if (!fs.existsSync(distDir)) {
  console.error('dist/ directory not found; run vite build first.');
  process.exit(1);
}

const FORBIDDEN_PATTERNS: { name: string; regex: RegExp }[] = [
  { name: 'fetch(', regex: /\bfetch\s*\(/g },
  { name: 'XMLHttpRequest', regex: /\bXMLHttpRequest\b/g },
];

const IGNORED_FILES = [
  /^sw\.js$/,
  /^workbox-.*\.js$/,
  /^registerSW\.js$/,
];

function walk(dir: string): string[] {
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(full));
    } else if (/\.(js|mjs|html)$/.test(entry.name)) {
      results.push(full);
    }
  }
  return results;
}

const files = walk(distDir);
const violations: string[] = [];

for (const file of files) {
  const rel = path.relative(distDir, file).replace(/\\/g, '/');
  const base = path.basename(file);
  if (IGNORED_FILES.some((re) => re.test(base))) {
    continue;
  }
  const content = fs.readFileSync(file, 'utf8');
  for (const pat of FORBIDDEN_PATTERNS) {
    const matches = content.match(pat.regex);
    if (matches && matches.length > 0) {
      violations.push(`${rel}: found ${matches.length} occurrence(s) of ${pat.name}`);
    }
  }
}

if (violations.length > 0) {
  console.error('Bundle network-call check FAILED:');
  for (const v of violations) {
    console.error(`  - ${v}`);
  }
  process.exit(1);
}

console.log(`Bundle network-call check PASSED across ${files.length} built files (excluding service worker).`);
