import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { validatePacks } from '../scripts/validate-content';

const ROOT = path.resolve(__dirname, '..');
const SCHEMAS_DIR = path.join(ROOT, 'schemas');
const PUBLIC_DIR = path.join(ROOT, 'public');
const SVG_BASE_DIR = path.join(ROOT, 'src', 'assets');
const BAD_DIR = path.join(ROOT, 'fixtures', 'bad');

describe('M0 Content Validator Gate', () => {
  const badFiles = fs
    .readdirSync(BAD_DIR)
    .filter((f) => f.endsWith('.json'))
    .sort();

  it('has at least 10 negative fixtures in fixtures/bad/', () => {
    expect(badFiles.length).toBeGreaterThanOrEqual(10);
  });

  for (const filename of badFiles) {
    it(`rejects invalid fixture: ${filename}`, () => {
      const result = validatePacks([path.join(BAD_DIR, filename)], {
        schemasDir: SCHEMAS_DIR,
        publicDir: PUBLIC_DIR,
        svgBaseDir: SVG_BASE_DIR,
      });
      expect(result.valid).toBe(false);
      expect(result.issues.length).toBeGreaterThan(0);
    });
  }

  it('validates all four real M3 content packs in content/packs/ (~900 verified schedulable items)', () => {
    const packsDir = path.join(ROOT, 'content', 'packs');
    const packFiles = fs
      .readdirSync(packsDir)
      .filter((f) => f.endsWith('.json'))
      .sort()
      .map((f) => path.join(packsDir, f));

    expect(packFiles.length).toBe(4);
    const result = validatePacks(packFiles, {
      schemasDir: SCHEMAS_DIR,
      publicDir: PUBLIC_DIR,
      svgBaseDir: SVG_BASE_DIR,
    });
    expect(result.issues).toEqual([]);
    expect(result.valid).toBe(true);
    expect(result.stats.figures).toBeGreaterThanOrEqual(9);
    expect(result.stats.facts + result.stats.plainCards).toBeGreaterThanOrEqual(700);
  });
});
