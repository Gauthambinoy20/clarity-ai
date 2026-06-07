import { useMutation } from "@tanstack/react-query";
import { humanizeText } from "@/utils/api";
import { useAppStore } from "@/stores/appStore";
import type { AnalysisOptions } from "@/types/analysis";

interface HumanizationParams {
  text: string;
  style?: string;
  options?: AnalysisOptions;
}

export function useHumanization() {
  const { setHumanizationResult, setIsAnalyzing } = useAppStore();

  return useMutation({
    mutationFn: ({ text, style = "academic", options }: HumanizationParams) =>
      humanizeText(text, style, options),
    onMutate: () => {
      setIsAnalyzing(true);
      setHumanizationResult(null);
    },
    onSuccess: (data) => {
      setHumanizationResult(data);
    },
    onSettled: () => {
      setIsAnalyzing(false);
    },
  });
}
