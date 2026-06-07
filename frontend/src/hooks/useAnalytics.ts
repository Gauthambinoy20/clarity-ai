import { useMutation } from "@tanstack/react-query";
import {
  analyzeReadability,
  analyzeTone,
  checkGrammar,
  getStatistics,
  getSuggestions,
  extractCitations,
  compareTexts,
  runFullAnalytics,
} from "@/utils/api";

export function useReadability() {
  return useMutation({
    mutationFn: (text: string) => analyzeReadability(text),
  });
}

export function useTone() {
  return useMutation({
    mutationFn: (text: string) => analyzeTone(text),
  });
}

export function useGrammar() {
  return useMutation({
    mutationFn: (text: string) => checkGrammar(text),
  });
}

export function useStatistics() {
  return useMutation({
    mutationFn: (text: string) => getStatistics(text),
  });
}

export function useSuggestions() {
  return useMutation({
    mutationFn: (text: string) => getSuggestions(text),
  });
}

export function useCitations() {
  return useMutation({
    mutationFn: (text: string) => extractCitations(text),
  });
}

export function useComparison() {
  return useMutation({
    mutationFn: ({ textA, textB }: { textA: string; textB: string }) =>
      compareTexts(textA, textB),
  });
}

export function useFullAnalytics() {
  return useMutation({
    mutationFn: (text: string) => runFullAnalytics(text),
  });
}
