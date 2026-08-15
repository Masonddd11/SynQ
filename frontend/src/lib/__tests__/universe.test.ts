import { describe, expect, it } from 'vitest';
import { parseSymbols } from '../universe';

describe('parseSymbols', () => {
  it('parses a comma-separated string into uppercase symbols', () => {
    expect(parseSymbols('aapl, MSFT, NVDA')).toEqual(['AAPL', 'MSFT', 'NVDA']);
  });

  it('deduplicates repeated symbols', () => {
    expect(parseSymbols('AAPL, aapl, AAPL')).toEqual(['AAPL']);
  });

  it('drops empty tokens and whitespace-only entries', () => {
    expect(parseSymbols('AAPL, , MSFT,   ')).toEqual(['AAPL', 'MSFT']);
  });

  it('handles whitespace-separated symbols without commas', () => {
    expect(parseSymbols('AAPL MSFT NVDA')).toEqual(['AAPL', 'MSFT', 'NVDA']);
  });

  it('returns empty array for empty input', () => {
    expect(parseSymbols('')).toEqual([]);
  });
});
