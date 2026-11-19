export type ModuleId = 'geography' | 'physics' | 'natural_world' | 'are_built';

export type DimensionScale = 'log' | 'linear' | 'date' | 'geo' | 'categorical';

export type ToleranceMode = 'factor' | 'absolute' | 'date_pct';

/** `flash` = plain number flashcard (primary); `place`/`place_timeline` = supplemental scale drills. */
export type CanonicalTaskType = 'flash' | 'place' | 'place_timeline' | 'occlude' | 'recall';

export type ReviewTaskType = CanonicalTaskType | 'ratio_probe';

export interface Entity {
  id: string;
  name: string;
  kind: string;
  module: ModuleId;
  tags: string[];
}

export interface Dimension {
  id: string;
  name: string;
  unit: string;
  scale: DimensionScale;
  tolerance: number;
  tolerance_mode?: ToleranceMode;
  min_domain?: number;
  max_domain?: number;
}

export interface Fact {
  entity_id: string;
  dimension_id: string;
  value: number;
  low: number;
  high: number;
  as_of: string;
  source_url: string;
  source_note: string;
  volatile: boolean;
  secondary_source_url?: string;
  secondary_value?: number;
}

export interface AnchorSet {
  dimension_id: string;
  entity_ids: string[];
}

export interface FigureRegion {
  region_id: string;
  label: string;
  entity_id?: string;
  adjacent_ids?: string[];
}

export interface Figure {
  id: string;
  title: string;
  module: ModuleId;
  dimension_id: string;
  svg_path: string;
  source_url?: string;
  source_note?: string;
  regions: FigureRegion[];
}

export interface PlainCard {
  id: string;
  module: ModuleId;
  entity_id?: string;
  tags?: string[];
  front: string;
  back: string;
  media?: string;
  attribution?: string;
  source_url?: string;
  source_note?: string;
  as_of?: string;
  volatile?: boolean;
}

export interface OrderingAssertion {
  dimension_id: string;
  ordered_entity_ids: string[];
}

export interface ContentPack {
  pack_id: string;
  version: string;
  release_date: string;
  module: ModuleId;
  entities: Entity[];
  dimensions: Dimension[];
  facts: Fact[];
  anchor_sets: AnchorSet[];
  figures: Figure[];
  plain_cards: PlainCard[];
  ordering_assertions?: OrderingAssertion[];
}

export interface CompiledContent {
  packs: ContentPack[];
  entities: Map<string, Entity>;
  dimensions: Map<string, Dimension>;
  facts: Fact[];
  factsByKey: Map<string, Fact>;
  factsByDimension: Map<string, Fact[]>;
  anchorSets: Map<string, AnchorSet>;
  figures: Map<string, Figure>;
  plainCards: Map<string, PlainCard>;
  releaseDate: string;
}

export const MODULE_LABELS: Record<ModuleId, string> = {
  geography: 'Geography & Human Scale',
  physics: 'Physical & Quantitative Ladders',
  natural_world: 'Natural World',
  are_built: 'Built Environment (ARE)',
};
