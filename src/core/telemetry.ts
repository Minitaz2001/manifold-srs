import type { ModuleId, ReviewTaskType } from '../types/content';
import type { ReviewLogEntry } from '../types/memory';

export const WIDGET_LATENCY_BUDGET_MS = 6000;

export interface ModuleCalibrationPoint {
  bucketLabel: string;
  medianAbsError: number;
  medianBias: number;
  count: number;
}

export interface ModuleCalibrationSummary {
  module: ModuleId;
  count: number;
  medianAbsError: number | null;
  medianBias: number | null;
  series: ModuleCalibrationPoint[];
}

export interface WidgetLatencySummary {
  task_type: ReviewTaskType;
  count: number;
  medianMs: number | null;
  flaggedForRedesign: boolean;
}

export function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Computes calibration telemetry per module (Design Doc §4):
 * median absolute error over time + signed bias (consistent over/under-estimation).
 */
export function computeModuleCalibration(
  logs: ReviewLogEntry[],
  module: ModuleId
): ModuleCalibrationSummary {
  const relevant = logs
    .filter((l) => l.module === module && Number.isFinite(l.error) && (l.task_type === 'place' || l.task_type === 'place_timeline'))
    .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());

  if (relevant.length === 0) {
    return {
      module,
      count: 0,
      medianAbsError: null,
      medianBias: null,
      series: [],
    };
  }

  // Group into daily buckets (up to last 14 active days)
  const buckets = new Map<string, ReviewLogEntry[]>();
  for (const log of relevant) {
    const day = log.ts.slice(0, 10);
    const arr = buckets.get(day) ?? [];
    arr.push(log);
    buckets.set(day, arr);
  }

  const series: ModuleCalibrationPoint[] = Array.from(buckets.entries())
    .slice(-14)
    .map(([day, entries]) => ({
      bucketLabel: day.slice(5),
      medianAbsError: median(entries.map((e) => e.error)) ?? 0,
      medianBias: median(entries.map((e) => e.signed_error)) ?? 0,
      count: entries.length,
    }));

  return {
    module,
    count: relevant.length,
    medianAbsError: median(relevant.map((r) => r.error)),
    medianBias: median(relevant.map((r) => r.signed_error)),
    series,
  };
}

/**
 * Computes 7-day median review latency per widget and overall (Design Doc §5):
 * "Any widget whose median exceeds 6 s for a week is flagged for redesign."
 */
export function computeLatencyStats(logs: ReviewLogEntry[], now = new Date()): {
  overallMedianMs: number | null;
  byWidget: WidgetLatencySummary[];
} {
  const weekAgo = now.getTime() - 7 * 86400000;
  const recent = logs.filter((l) => new Date(l.ts).getTime() >= weekAgo && l.latency_ms > 0);

  const taskTypes: ReviewTaskType[] = ['place', 'place_timeline', 'occlude', 'recall'];
  const byWidget: WidgetLatencySummary[] = taskTypes.map((task_type) => {
    const subset = recent.filter((l) => l.task_type === task_type);
    const med = median(subset.map((s) => s.latency_ms));
    const uniqueDays = new Set(subset.map((s) => s.ts.slice(0, 10))).size;
    return {
      task_type,
      count: subset.length,
      medianMs: med,
      flaggedForRedesign: med !== null && med > WIDGET_LATENCY_BUDGET_MS && (uniqueDays >= 3 || subset.length >= 10),
    };
  });

  return {
    overallMedianMs: median(recent.map((r) => r.latency_ms)),
    byWidget,
  };
}
