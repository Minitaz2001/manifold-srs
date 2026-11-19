import type {
  AnchorSet,
  CompiledContent,
  ContentPack,
  Dimension,
  Entity,
  Fact,
  Figure,
  PlainCard,
} from '../types/content';
import geographyPack from '../../content/packs/geography.json';
import physicsPack from '../../content/packs/physics.json';
import naturalWorldPack from '../../content/packs/natural_world.json';
import areBuiltPack from '../../content/packs/are_built.json';

import eastSeAsiaSvg from '../assets/figures/east-se-asia.svg?raw';
import europeSvg from '../assets/figures/europe.svg?raw';
import americasSvg from '../assets/figures/americas.svg?raw';
import africaMenaSvg from '../assets/figures/africa-mena.svg?raw';
import usEnergySankeySvg from '../assets/figures/us-energy-sankey.svg?raw';
import emSpectrumSvg from '../assets/figures/em-spectrum.svg?raw';
import wallSectionSvg from '../assets/figures/wall-section.svg?raw';
import aiaDeliverySvg from '../assets/figures/aia-delivery-map.svg?raw';
import siteZoningSvg from '../assets/figures/site-zoning-section.svg?raw';

/**
 * All SVG figures are statically bundled at build time via Vite `?raw` imports.
 * Zero runtime network calls (`fetch(`) ever occur.
 */
export const BUNDLED_SVGS: Record<string, string> = {
  'figures/east-se-asia.svg': eastSeAsiaSvg,
  'figures/europe.svg': europeSvg,
  'figures/americas.svg': americasSvg,
  'figures/africa-mena.svg': africaMenaSvg,
  'figures/us-energy-sankey.svg': usEnergySankeySvg,
  'figures/em-spectrum.svg': emSpectrumSvg,
  'figures/wall-section.svg': wallSectionSvg,
  'figures/aia-delivery-map.svg': aiaDeliverySvg,
  'figures/site-zoning-section.svg': siteZoningSvg,
};

export function compileContentPacks(packs: ContentPack[]): CompiledContent {
  const entities = new Map<string, Entity>();
  const dimensions = new Map<string, Dimension>();
  const facts: Fact[] = [];
  const factsByKey = new Map<string, Fact>();
  const factsByDimension = new Map<string, Fact[]>();
  const anchorSets = new Map<string, AnchorSet>();
  const figures = new Map<string, Figure>();
  const plainCards = new Map<string, PlainCard>();
  let releaseDate = '2026-01-01';

  for (const pack of packs) {
    if (pack.release_date > releaseDate) {
      releaseDate = pack.release_date;
    }
    for (const e of pack.entities) entities.set(e.id, e);
    for (const d of pack.dimensions) dimensions.set(d.id, d);
    for (const f of pack.facts) {
      facts.push(f);
      factsByKey.set(`${f.entity_id}::${f.dimension_id}`, f);
      const bucket = factsByDimension.get(f.dimension_id) ?? [];
      bucket.push(f);
      factsByDimension.set(f.dimension_id, bucket);
    }
    for (const a of pack.anchor_sets) anchorSets.set(a.dimension_id, a);
    for (const fig of pack.figures) figures.set(fig.id, fig);
    for (const card of pack.plain_cards) plainCards.set(card.id, card);
  }

  return {
    packs,
    entities,
    dimensions,
    facts,
    factsByKey,
    factsByDimension,
    anchorSets,
    figures,
    plainCards,
    releaseDate,
  };
}

let cachedContent: CompiledContent | null = null;

export function getBundledContent(): CompiledContent {
  if (!cachedContent) {
    cachedContent = compileContentPacks([
      geographyPack as ContentPack,
      physicsPack as ContentPack,
      naturalWorldPack as ContentPack,
      areBuiltPack as ContentPack,
    ]);
  }
  return cachedContent;
}
