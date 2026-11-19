import fs from 'node:fs';
import path from 'node:path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import type { ContentPack, Dimension, Entity, Fact } from '../src/types/content.ts';

export interface ValidationIssue {
  file: string;
  code: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
  stats: {
    packs: number;
    entities: number;
    dimensions: number;
    facts: number;
    figures: number;
    plainCards: number;
  };
}

const ANTI_COLLISION_FACTOR = 1.2;
const MIN_ANCHOR_BRACKET_RATIO = 0.8;

function normalizeName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function levenshtein(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost);
    }
  }
  return dp[m][n];
}

function extractSvgIds(svgContent: string): Set<string> {
  const ids = new Set<string>();
  const regex = /\bid\s*=\s*["']([^"']+)["']/g;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(svgContent)) !== null) {
    ids.add(match[1]);
  }
  return ids;
}

export function buildPackValidator(schemasDir: string) {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);

  const schemaFiles = [
    'entity.schema.json',
    'dimension.schema.json',
    'fact.schema.json',
    'anchor_set.schema.json',
    'figure.schema.json',
    'plain_card.schema.json',
    'pack.schema.json',
  ];

  for (const filename of schemaFiles) {
    const raw = fs.readFileSync(path.join(schemasDir, filename), 'utf8');
    ajv.addSchema(JSON.parse(raw), filename);
  }

  const validate = ajv.getSchema('pack.schema.json');
  if (!validate) {
    throw new Error('Failed to load pack.schema.json');
  }
  return validate;
}

export function validatePacks(
  packFiles: string[],
  options: { schemasDir: string; publicDir: string; svgBaseDir?: string }
): ValidationResult {
  const issues: ValidationIssue[] = [];
  const validate = buildPackValidator(options.schemasDir);

  const allEntities = new Map<string, { entity: Entity; file: string }>();
  const allDimensions = new Map<string, { dimension: Dimension; file: string }>();
  const allFactsByDim = new Map<string, { fact: Fact; file: string }[]>();
  const allFactKeys = new Set<string>();
  const loadedPacks: { pack: ContentPack; file: string }[] = [];

  let totalFigures = 0;
  let totalPlainCards = 0;
  let totalFacts = 0;

  for (const file of packFiles) {
    let parsed: unknown;
    try {
      parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch (err) {
      issues.push({
        file,
        code: 'JSON_PARSE_ERROR',
        message: `Failed to parse JSON: ${(err as Error).message}`,
      });
      continue;
    }

    if (!validate(parsed)) {
      for (const err of validate.errors ?? []) {
        issues.push({
          file,
          code: 'SCHEMA_ERROR',
          message: `${err.instancePath || '/'} ${err.message ?? 'schema violation'}`,
        });
      }
      continue;
    }

    const pack = parsed as ContentPack;
    loadedPacks.push({ pack, file });

    // Entities: duplicate ID and module consistency
    for (const entity of pack.entities) {
      if (entity.module !== pack.module) {
        issues.push({
          file,
          code: 'MODULE_MISMATCH',
          message: `Entity "${entity.id}" has module "${entity.module}" inside "${pack.module}" pack`,
        });
      }
      if (allEntities.has(entity.id)) {
        issues.push({
          file,
          code: 'DUPLICATE_ENTITY_ID',
          message: `Duplicate entity id "${entity.id}" (already defined in ${allEntities.get(entity.id)!.file})`,
        });
      } else {
        allEntities.set(entity.id, { entity, file });
      }
    }

    // Dimensions
    for (const dim of pack.dimensions) {
      if (dim.scale === 'log' && dim.tolerance <= 1) {
        issues.push({
          file,
          code: 'INVALID_LOG_TOLERANCE',
          message: `Log dimension "${dim.id}" must have factor tolerance > 1 (got ${dim.tolerance})`,
        });
      }
      if (allDimensions.has(dim.id)) {
        const existing = allDimensions.get(dim.id)!;
        if (existing.dimension.scale !== dim.scale || existing.dimension.unit !== dim.unit) {
          issues.push({
            file,
            code: 'CONFLICTING_DIMENSION',
            message: `Dimension "${dim.id}" conflicts with definition in ${existing.file}`,
          });
        }
      } else {
        allDimensions.set(dim.id, { dimension: dim, file });
      }
    }
  }

  // Near-duplicate entity name check within same kind/module
  const entityList = Array.from(allEntities.values());
  for (let i = 0; i < entityList.length; i++) {
    const a = entityList[i];
    const normA = normalizeName(a.entity.name);
    for (let j = i + 1; j < entityList.length; j++) {
      const b = entityList[j];
      if (a.entity.module !== b.entity.module || a.entity.kind !== b.entity.kind) continue;
      const normB = normalizeName(b.entity.name);
      if (normA === normB) {
        issues.push({
          file: b.file,
          code: 'DUPLICATE_ENTITY_NAME',
          message: `Entities "${a.entity.id}" and "${b.entity.id}" share normalized name "${normA}"`,
        });
      } else if (normA.length >= 8 && normB.length >= 8 && levenshtein(normA, normB) <= 1) {
        issues.push({
          file: b.file,
          code: 'NEAR_DUPLICATE_ENTITY',
          message: `Entities "${a.entity.id}" ("${a.entity.name}") and "${b.entity.id}" ("${b.entity.name}") are near-duplicates`,
        });
      }
    }
  }

  // Facts, Anchor sets, Figures, Plain cards, Ordering assertions
  for (const { pack, file } of loadedPacks) {
    for (const fact of pack.facts) {
      totalFacts++;
      if (!allEntities.has(fact.entity_id)) {
        issues.push({
          file,
          code: 'UNKNOWN_ENTITY',
          message: `Fact references unknown entity_id "${fact.entity_id}"`,
        });
      }
      const dimEntry = allDimensions.get(fact.dimension_id);
      if (!dimEntry) {
        issues.push({
          file,
          code: 'UNKNOWN_DIMENSION',
          message: `Fact references unknown dimension_id "${fact.dimension_id}"`,
        });
      } else {
        if (dimEntry.dimension.scale === 'log' && (fact.value <= 0 || fact.low <= 0 || fact.high <= 0)) {
          issues.push({
            file,
            code: 'NON_POSITIVE_LOG_VALUE',
            message: `Log fact ${fact.entity_id}.${fact.dimension_id} must have strictly positive value/low/high`,
          });
        }
      }

      if (fact.low > fact.value || fact.value > fact.high) {
        issues.push({
          file,
          code: 'INVALID_BOUNDS',
          message: `Fact ${fact.entity_id}.${fact.dimension_id} violates low <= value <= high (${fact.low}, ${fact.value}, ${fact.high})`,
        });
      }

      const key = `${fact.entity_id}::${fact.dimension_id}`;
      if (allFactKeys.has(key)) {
        issues.push({
          file,
          code: 'DUPLICATE_FACT',
          message: `Duplicate fact for ${key}`,
        });
      } else {
        allFactKeys.add(key);
      }

      if (!fact.source_url || !fact.source_url.startsWith('http')) {
        issues.push({
          file,
          code: 'MISSING_SOURCE_URL',
          message: `Fact ${key} is missing a valid source_url`,
        });
      }

      const bucket = allFactsByDim.get(fact.dimension_id) ?? [];
      bucket.push({ fact, file });
      allFactsByDim.set(fact.dimension_id, bucket);
    }

    // Ordering monotonicity checks
    for (const assertion of pack.ordering_assertions ?? []) {
      const dimFacts = new Map(
        (allFactsByDim.get(assertion.dimension_id) ?? []).map((x) => [x.fact.entity_id, x.fact])
      );
      for (let i = 0; i < assertion.ordered_entity_ids.length - 1; i++) {
        const leftId = assertion.ordered_entity_ids[i];
        const rightId = assertion.ordered_entity_ids[i + 1];
        const left = dimFacts.get(leftId);
        const right = dimFacts.get(rightId);
        if (!left || !right) {
          issues.push({
            file,
            code: 'ORDERING_MISSING_FACT',
            message: `Ordering assertion on ${assertion.dimension_id} references missing fact (${leftId} or ${rightId})`,
          });
          continue;
        }
        if (left.value > right.value) {
          issues.push({
            file,
            code: 'MONOTONICITY_VIOLATION',
            message: `Ordering assertion failed on ${assertion.dimension_id}: ${leftId} (${left.value}) > ${rightId} (${right.value})`,
          });
        }
      }
    }

    // Figures & SVG regions
    for (const fig of pack.figures) {
      totalFigures++;
      if (!allDimensions.has(fig.dimension_id)) {
        issues.push({
          file,
          code: 'UNKNOWN_DIMENSION',
          message: `Figure "${fig.id}" references unknown dimension_id "${fig.dimension_id}"`,
        });
      }
      const svgBase = options.svgBaseDir ?? options.publicDir;
      const svgFullPath = path.join(svgBase, fig.svg_path);
      if (!fs.existsSync(svgFullPath)) {
        issues.push({
          file,
          code: 'MISSING_SVG_FILE',
          message: `Figure "${fig.id}" svg_path not found: ${fig.svg_path}`,
        });
      } else {
        const svgIds = extractSvgIds(fs.readFileSync(svgFullPath, 'utf8'));
        const regionIds = new Set(fig.regions.map((r) => r.region_id));
        for (const region of fig.regions) {
          if (!svgIds.has(region.region_id)) {
            issues.push({
              file,
              code: 'MISSING_SVG_REGION',
              message: `Figure "${fig.id}" region "${region.region_id}" not found as id in ${fig.svg_path}`,
            });
          }
          if (region.entity_id && !allEntities.has(region.entity_id)) {
            issues.push({
              file,
              code: 'UNKNOWN_REGION_ENTITY',
              message: `Figure "${fig.id}" region "${region.region_id}" references unknown entity_id "${region.entity_id}"`,
            });
          }
          for (const adj of region.adjacent_ids ?? []) {
            if (!regionIds.has(adj)) {
              issues.push({
                file,
                code: 'UNKNOWN_ADJACENT_REGION',
                message: `Figure "${fig.id}" region "${region.region_id}" lists unknown adjacent_id "${adj}"`,
              });
            }
          }
        }
      }
    }

    // Plain cards
    for (const card of pack.plain_cards) {
      totalPlainCards++;
      if (card.entity_id && !allEntities.has(card.entity_id)) {
        issues.push({
          file,
          code: 'UNKNOWN_CARD_ENTITY',
          message: `Plain card "${card.id}" references unknown entity_id "${card.entity_id}"`,
        });
      }
      if (card.media) {
        const mediaFullPath = path.join(options.publicDir, card.media);
        if (!fs.existsSync(mediaFullPath)) {
          issues.push({
            file,
            code: 'MISSING_MEDIA_FILE',
            message: `Plain card "${card.id}" media file not found: ${card.media}`,
          });
        }
        if (!card.attribution) {
          issues.push({
            file,
            code: 'MISSING_ATTRIBUTION',
            message: `Plain card "${card.id}" includes media "${card.media}" without attribution`,
          });
        }
      }
    }
  }

  // Anchor set checks (bracketing >= 80% + log anti-collision >= 1.2x)
  for (const { pack, file } of loadedPacks) {
    for (const anchorSet of pack.anchor_sets) {
      const dimEntry = allDimensions.get(anchorSet.dimension_id);
      if (!dimEntry) {
        issues.push({
          file,
          code: 'UNKNOWN_ANCHOR_DIMENSION',
          message: `AnchorSet references unknown dimension_id "${anchorSet.dimension_id}"`,
        });
        continue;
      }

      const dimFacts = allFactsByDim.get(anchorSet.dimension_id) ?? [];
      const factMap = new Map(dimFacts.map((x) => [x.fact.entity_id, x.fact]));
      const anchorValues: { id: string; value: number }[] = [];

      for (const eid of anchorSet.entity_ids) {
        const f = factMap.get(eid);
        if (!f) {
          issues.push({
            file,
            code: 'ANCHOR_MISSING_FACT',
            message: `Anchor "${eid}" in dimension "${anchorSet.dimension_id}" has no corresponding fact`,
          });
        } else {
          anchorValues.push({ id: eid, value: f.value });
        }
      }

      if (anchorValues.length < 2) continue;

      const sorted = [...anchorValues].sort((a, b) => a.value - b.value);
      const minAnchor = sorted[0].value;
      const maxAnchor = sorted[sorted.length - 1].value;

      // Bracketing check: >= 80% of all dimension facts must lie inside [minAnchor, maxAnchor]
      if (dimFacts.length > 0) {
        const bracketed = dimFacts.filter(
          ({ fact }) => fact.value >= minAnchor && fact.value <= maxAnchor
        ).length;
        const ratio = bracketed / dimFacts.length;
        if (ratio < MIN_ANCHOR_BRACKET_RATIO) {
          issues.push({
            file,
            code: 'INSUFFICIENT_ANCHOR_BRACKETING',
            message: `AnchorSet for "${anchorSet.dimension_id}" brackets only ${(ratio * 100).toFixed(1)}% (${bracketed}/${dimFacts.length}) of facts; minimum is 80%`,
          });
        }
      }

      // Anti-collision check on log dimensions: no two anchors within 1.2x
      if (dimEntry.dimension.scale === 'log') {
        for (let i = 0; i < sorted.length - 1; i++) {
          const ratio = sorted[i + 1].value / sorted[i].value;
          if (ratio <= ANTI_COLLISION_FACTOR) {
            issues.push({
              file,
              code: 'ANCHOR_COLLISION',
              message: `Anchors "${sorted[i].id}" (${sorted[i].value}) and "${sorted[i + 1].id}" (${sorted[i + 1].value}) on log dimension "${anchorSet.dimension_id}" are within ${ANTI_COLLISION_FACTOR}x (${ratio.toFixed(3)}x)`,
            });
          }
        }
      }
    }
  }

  return {
    valid: issues.length === 0,
    issues,
    stats: {
      packs: loadedPacks.length,
      entities: allEntities.size,
      dimensions: allDimensions.size,
      facts: totalFacts,
      figures: totalFigures,
      plainCards: totalPlainCards,
    },
  };
}

// CLI entry
import { fileURLToPath } from 'node:url';
const isMain =
  Boolean(process.argv[1]) &&
  path.resolve(process.argv[1]).toLowerCase() === path.resolve(fileURLToPath(import.meta.url)).toLowerCase();
if (isMain) {
  const root = process.cwd();
  const targetDir = process.argv[2] ? path.resolve(process.argv[2]) : path.join(root, 'content', 'packs');
  const schemasDir = path.join(root, 'schemas');
  const publicDir = path.join(root, 'public');
  const svgBaseDir = path.join(root, 'src', 'assets');

  if (!fs.existsSync(targetDir)) {
    console.error(`Pack directory not found: ${targetDir}`);
    process.exit(1);
  }

  const files = fs
    .readdirSync(targetDir)
    .filter((f) => f.endsWith('.json'))
    .sort()
    .map((f) => path.join(targetDir, f));

  if (files.length === 0) {
    console.error(`No .json content packs found in ${targetDir}`);
    process.exit(1);
  }

  const result = validatePacks(files, { schemasDir, publicDir, svgBaseDir });
  console.log(
    `Validated ${result.stats.packs} packs: ${result.stats.entities} entities, ${result.stats.dimensions} dimensions, ${result.stats.facts} facts, ${result.stats.figures} figures, ${result.stats.plainCards} plain cards.`
  );
  if (!result.valid) {
    for (const issue of result.issues) {
      console.error(`[${issue.code}] ${path.basename(issue.file)}: ${issue.message}`);
    }
    process.exit(1);
  }
  console.log('Content validation PASSED.');
}
