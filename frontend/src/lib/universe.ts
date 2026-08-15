/**
 * frontend/src/lib/universe.ts — Client-side universe selection helpers.
 *
 * Parses raw custom-symbol input into a clean, deduplicated, uppercase list.
 * Pure logic — no DOM or network — so it is trivially testable.
 */

/** Hard cap on the size of a resolved universe (mirrors the backend setting). */
export const MAX_UNIVERSE_SYMBOLS = 200;

/**
 * Parse a raw comma-separated symbol input string into an ordered, deduplicated,
 * uppercase symbol list. Empty tokens and excess symbols beyond the cap are dropped.
 */
export function parseSymbols(input: string): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const raw of input.split(/[,\s]+/)) {
    const token = raw.trim().toUpperCase();
    if (!token || seen.has(token)) continue;
    seen.add(token);
    result.push(token);
    if (result.length >= MAX_UNIVERSE_SYMBOLS) break;
  }
  return result;
}

/** Market-cap bucket labels used by the universe filter UI + API. */
export const MARKET_CAP_BUCKETS = [
  { value: '', label: 'All market caps' },
  { value: 'low', label: 'Low cap (< $2B)' },
  { value: 'mid', label: 'Mid cap ($2B–$10B)' },
  { value: 'high', label: 'High cap (> $10B)' },
] as const;

export type MarketCapValue = (typeof MARKET_CAP_BUCKETS)[number]['value'];
