import { useMutation } from "@tanstack/react-query";
import { analyzePlagiarism } from "@/utils/api";
import { useAppStore } from "@/stores/appStore";
import type { AnalysisOptions } from "@/types/analysis";

interface PlagiarismParams {
  text: string;
  options?: AnalysisOptions;
}

export function usePlagiarism() {
  const { setPlagiarismResult, setIsAnalyzing } = useAppStore();

  return useMutation({
    mutationFn: ({ text, options }: PlagiarismParams) =>
      analyzePlagiarism(text, options),
    onMutate: () => {
      setIsAnalyzing(true);
      setPlagiarismResult(null);
    },
    onSuccess: (data) => {
      setPlagiarismResult(data);
    },
    onSettled: () => {
      setIsAnalyzing(false);
    },
  });
}
