import { useState, useCallback } from "react";
import {
  Box,
  TextField,
  Button,
  Typography,
  Chip,
  ToggleButtonGroup,
  ToggleButton,
} from "@mui/material";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import { motion } from "framer-motion";

interface TextInputProps {
  onSubmit: (text: string, mode: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  submitLabel?: string;
  showModeSelector?: boolean;
}

function countWords(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

export default function TextInput({
  onSubmit,
  isLoading = false,
  placeholder = "Paste or type text to analyze...",
  submitLabel = "Analyze",
  showModeSelector = true,
}: TextInputProps) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState("deep");
  const wordCount = countWords(text);
  const charCount = text.length;
  const isMinWords = wordCount >= 50;

  const handleSubmit = useCallback(() => {
    if (isMinWords && !isLoading) {
      onSubmit(text, mode);
    }
  }, [text, mode, isMinWords, isLoading, onSubmit]);

  return (
    <Box>
      <TextField
        multiline
        minRows={6}
        maxRows={16}
        fullWidth
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        disabled={isLoading}
        sx={{
          "& .MuiOutlinedInput-root": {
            fontSize: "1rem",
            lineHeight: 1.7,
          },
        }}
      />

      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mt: 1.5,
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Typography variant="caption" color="text.secondary">
            {wordCount} words
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {charCount} chars
          </Typography>
          {wordCount > 0 && !isMinWords && (
            <motion.div
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <Chip
                label={`${50 - wordCount} more words needed`}
                size="small"
                color="warning"
                variant="outlined"
              />
            </motion.div>
          )}
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          {showModeSelector && (
            <ToggleButtonGroup
              value={mode}
              exclusive
              onChange={(_, v) => v && setMode(v)}
              size="small"
            >
              <ToggleButton value="quick">Quick</ToggleButton>
              <ToggleButton value="deep">Deep</ToggleButton>
              <ToggleButton value="forensic">Forensic</ToggleButton>
            </ToggleButtonGroup>
          )}

          <Button
            variant="contained"
            disabled={!isMinWords || isLoading}
            onClick={handleSubmit}
            startIcon={<PlayArrowRoundedIcon />}
            sx={{
              background: "linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%)",
              color: "#fff",
              "&:hover": {
                background: "linear-gradient(135deg, #6d28d9 0%, #0891b2 100%)",
              },
              "&.Mui-disabled": {
                background: "action.disabledBackground",
              },
            }}
          >
            {isLoading ? "Analyzing..." : submitLabel}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
