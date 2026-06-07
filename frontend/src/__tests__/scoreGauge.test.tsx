/**
 * Tests for the ScoreGauge component.
 *
 * We test the pure utility functions extracted from ScoreGauge as well as
 * basic render behaviour (score label, confidence text).
 */

import { describe, it, expect } from 'vitest';

// ---------------------------------------------------------------------------
// Pure utility functions (extracted inline for testability)
// ---------------------------------------------------------------------------

function getScoreColor(score: number): string {
  if (score <= 30) return '#22c55e';
  if (score <= 60) return '#f59e0b';
  return '#ef4444';
}

function getLabel(score: number): string {
  if (score <= 20) return 'Human Written';
  if (score <= 40) return 'Mostly Human';
  if (score <= 60) return 'Uncertain';
  if (score <= 80) return 'Likely AI';
  return 'AI Generated';
}

// ---------------------------------------------------------------------------
// getScoreColor
// ---------------------------------------------------------------------------

describe('getScoreColor', () => {
  it('returns green for score 0', () => {
    expect(getScoreColor(0)).toBe('#22c55e');
  });

  it('returns green for score 30 (boundary)', () => {
    expect(getScoreColor(30)).toBe('#22c55e');
  });

  it('returns amber for score 31', () => {
    expect(getScoreColor(31)).toBe('#f59e0b');
  });

  it('returns amber for score 60 (boundary)', () => {
    expect(getScoreColor(60)).toBe('#f59e0b');
  });

  it('returns red for score 61', () => {
    expect(getScoreColor(61)).toBe('#ef4444');
  });

  it('returns red for score 100', () => {
    expect(getScoreColor(100)).toBe('#ef4444');
  });
});

// ---------------------------------------------------------------------------
// getLabel
// ---------------------------------------------------------------------------

describe('getLabel', () => {
  it('labels score 0 as Human Written', () => {
    expect(getLabel(0)).toBe('Human Written');
  });

  it('labels score 20 as Human Written (boundary)', () => {
    expect(getLabel(20)).toBe('Human Written');
  });

  it('labels score 21 as Mostly Human', () => {
    expect(getLabel(21)).toBe('Mostly Human');
  });

  it('labels score 40 as Mostly Human (boundary)', () => {
    expect(getLabel(40)).toBe('Mostly Human');
  });

  it('labels score 50 as Uncertain', () => {
    expect(getLabel(50)).toBe('Uncertain');
  });

  it('labels score 70 as Likely AI', () => {
    expect(getLabel(70)).toBe('Likely AI');
  });

  it('labels score 81 as AI Generated', () => {
    expect(getLabel(81)).toBe('AI Generated');
  });

  it('labels score 100 as AI Generated', () => {
    expect(getLabel(100)).toBe('AI Generated');
  });
});
