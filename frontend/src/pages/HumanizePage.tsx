import { useState, useCallback } from "react";
import { Box, Card, CardContent, Typography } from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";
import TextInput from "@/components/input/TextInput";
import LoadingProgress from "@/components/common/LoadingProgress";
import HumanizerPanel from "@/components/humanizer/HumanizerPanel";
import { useHumanization } from "@/hooks/useHumanization";
import { useAppStore } from "@/stores/appStore";

export default function HumanizePage() {
  const [style, setStyle] = useState("academic");
  const humanization = useHumanization();
  const { humanizationResult, isAnalyzing } = useAppStore();

  const handleSubmit = useCallback(
    (text: string) => {
      humanization.mutate({ text, style });
    },
    [humanization, style]
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
            AI Text Humanizer
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Transform AI-generated text to bypass detection while preserving
            original meaning.
          </Typography>
        </Box>

        <Card sx={{ mb: 3 }}>
          <CardContent>
            <TextInput
              onSubmit={handleSubmit}
              isLoading={isAnalyzing}
              placeholder="Paste AI-generated text to humanize..."
              submitLabel="Humanize"
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

        {humanization.isError && (
          <Card sx={{ mb: 3, borderColor: "error.main" }}>
            <CardContent>
              <Typography color="error" variant="body2">
                {humanization.error?.message || "Humanization failed."}
              </Typography>
            </CardContent>
          </Card>
        )}

        {humanizationResult && !isAnalyzing && (
          <HumanizerPanel
            result={humanizationResult}
            style={style}
            onStyleChange={setStyle}
          />
        )}
      </Box>
    </motion.div>
  );
}
