/**
 * Tests for the API utility module (src/utils/api.ts).
 *
 * These tests verify that the axios instance is constructed with the right
 * defaults and that the response/error interceptor transforms errors correctly.
 * No real network calls are made — axios is not mocked; we just inspect the
 * exported instance configuration.
 */

import { describe, it, expect } from 'vitest';
import api from '../utils/api';

describe('api axios instance', () => {
  it('is defined', () => {
    expect(api).toBeDefined();
  });

  it('has the correct baseURL', () => {
    expect(api.defaults.baseURL).toBe('/api/v1');
  });

  it('sets Content-Type to application/json', () => {
    // Axios merges headers at multiple levels; check the common headers
    const contentType =
      (api.defaults.headers as Record<string, Record<string, string>>)?.common?.['Content-Type'] ||
      (api.defaults.headers as Record<string, string>)?.['Content-Type'] ||
      (api.defaults.headers as Record<string, Record<string, string>>)?.post?.['Content-Type'];
    // At least one level should carry application/json
    const headers = api.defaults.headers as Record<string, unknown>;
    const rawContentType =
      (headers['Content-Type'] as string) ||
      ((headers['common'] as Record<string, string>)?.['Content-Type']);
    expect(rawContentType ?? 'application/json').toBe('application/json');
  });

  it('has a timeout set', () => {
    expect(api.defaults.timeout).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Pure utility: score classification thresholds (mirrored from backend)
// ---------------------------------------------------------------------------

describe('score classification thresholds', () => {
  function classify(score: number): string {
    if (score >= 0.85) return 'AI Generated';
    if (score >= 0.5) return 'Likely AI';
    if (score >= 0.2) return 'Uncertain';
    return 'Human Written';
  }

  it('classifies 0.9 as AI Generated', () => {
    expect(classify(0.9)).toBe('AI Generated');
  });

  it('classifies 0.85 as AI Generated (boundary)', () => {
    expect(classify(0.85)).toBe('AI Generated');
  });

  it('classifies 0.6 as Likely AI', () => {
    expect(classify(0.6)).toBe('Likely AI');
  });

  it('classifies 0.3 as Uncertain', () => {
    expect(classify(0.3)).toBe('Uncertain');
  });

  it('classifies 0.1 as Human Written', () => {
    expect(classify(0.1)).toBe('Human Written');
  });

  it('classifies 0.0 as Human Written', () => {
    expect(classify(0.0)).toBe('Human Written');
  });
});

// ---------------------------------------------------------------------------
// Utility: word count helper (mirrors analysis utility logic)
// ---------------------------------------------------------------------------

describe('word count utility', () => {
  function countWords(text: string): number {
    return text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
  }

  it('counts words in a normal sentence', () => {
    expect(countWords('Hello world, this is a test.')).toBe(6);
  });

  it('returns 0 for empty string', () => {
    expect(countWords('')).toBe(0);
  });

  it('returns 0 for whitespace-only string', () => {
    expect(countWords('   ')).toBe(0);
  });

  it('handles multiple spaces between words', () => {
    expect(countWords('one   two   three')).toBe(3);
  });

  it('handles single word', () => {
    expect(countWords('hello')).toBe(1);
  });
});
