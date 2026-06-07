import { useMutation } from "@tanstack/react-query";
import { analyzeText } from "@/utils/api";
import { useAppStore } from "@/stores/appStore";
import type { AnalysisOptions } from "@/types/analysis";

interface DetectionParams {
  text: string;
  mode?: string;
  options?: AnalysisOptions;
}

export function useDetection() {
  const { setDetectionResult, setIsAnalyzing } = useAppStore();

  return useMutation({
    mutationFn: ({ text, mode = "deep", options }: DetectionParams) =>
      analyzeText(text, mode, options),
    onMutate: () => {
      setIsAnalyzing(true);
      setDetectionResult(null);
    },
    onSuccess: (data) => {
      setDetectionResult(data);
    },
    onSettled: () => {
      setIsAnalyzing(false);
    },
  });
}
