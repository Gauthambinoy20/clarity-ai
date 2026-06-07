import { useCallback } from "react";
import { Box, Card, CardContent, Typography } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import TextInput from "@/components/input/TextInput";
import LoadingProgress from "@/components/common/LoadingProgress";
import PlagiarismReport from "@/components/plagiarism/PlagiarismReport";
import { usePlagiarism } from "@/hooks/usePlagiarism";
import { useAppStore } from "@/stores/appStore";

export default function PlagiarismPage() {
  const plagiarism = usePlagiarism();
  const { plagiarismResult, isAnalyzing } = useAppStore();

  const handleSubmit = useCallback(
    (text: string) => {
      plagiarism.mutate({ text });
    },
    [plagiarism]
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Box sx={{ maxWidth: 1100, mx: "auto" }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Plagiarism Detection
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Check text originality against billions of online sources and academic
            databases.
          </Typography>
        </Box>

        <Card sx={{ mb: 3 }}>
          <CardContent>
            <TextInput
              onSubmit={handleSubmit}
              isLoading={isAnalyzing}
              placeholder="Paste text to check for plagiarism..."
              submitLabel="Check Plagiarism"
              showModeSelector={false}
            />
          </CardContent>
        </Card>

        <AnimatePresence>
          {isAnalyzing && (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <LoadingProgress isLoading={isAnalyzing} />
              </CardContent>
            </Card>
          )}
        </AnimatePresence>

        {plagiarism.isError && (
          <Card sx={{ mb: 3, borderColor: "error.main" }}>
            <CardContent>
              <Typography color="error" variant="body2">
                {plagiarism.error?.message || "Plagiarism check failed."}
              </Typography>
            </CardContent>
          </Card>
        )}

        {plagiarismResult && !isAnalyzing && (
          <PlagiarismReport result={plagiarismResult} />
        )}
      </Box>
    </motion.div>
  );
}
