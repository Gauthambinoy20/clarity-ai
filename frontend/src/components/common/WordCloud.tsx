import { useMemo } from "react";
import { Box, Typography, useTheme } from "@mui/material";
import { motion } from "framer-motion";
import type { WordCloudItem } from "@/types/analytics";

interface WordCloudProps {
  words: WordCloudItem[];
  width?: number;
  height?: number;
}

export default function WordCloud({ words, width = 600, height = 320 }: WordCloudProps) {
  const theme = useTheme();

  const palette = useMemo(
    () => [
      theme.palette.primary.main,
      theme.palette.primary.light,
      theme.palette.secondary.main,
      theme.palette.secondary.light,
      theme.palette.success.main,
      theme.palette.warning.main,
      theme.palette.error.light,
      "#a78bfa",
      "#34d399",
      "#fbbf24",
      "#f472b6",
      "#60a5fa",
    ],
    [theme]
  );

  const positioned = useMemo(() => {
    if (!words.length) return [];
    const maxVal = Math.max(...words.map((w) => w.value));
    const minVal = Math.min(...words.map((w) => w.value));
    const range = maxVal - minVal || 1;

    return words.slice(0, 50).map((word, i) => {
      const normalized = (word.value - minVal) / range;
      const fontSize = 14 + normalized * 34;
      const angle = (Math.random() - 0.5) * 30;
      const color = palette[i % palette.length];
      const x = 10 + Math.random() * (width - 120);
      const y = 10 + Math.random() * (height - 60);
      return { ...word, fontSize, angle, color, x, y };
    });
  }, [words, width, height, palette]);

  if (!words.length) {
    return (
      <Box
        sx={{
          width,
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Typography color="text.secondary">No word data available</Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        position: "relative",
        width: "100%",
        maxWidth: width,
        height,
        mx: "auto",
        overflow: "hidden",
        borderRadius: 2,
      }}
    >
      {positioned.map((word, i) => (
        <motion.div
          key={word.text}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.02, duration: 0.4, ease: "easeOut" }}
          style={{
            position: "absolute",
            left: word.x,
            top: word.y,
            transform: `rotate(${word.angle}deg)`,
            whiteSpace: "nowrap",
            userSelect: "none",
          }}
        >
          <Typography
            sx={{
              fontSize: word.fontSize,
              fontWeight: 600 + Math.round((word.fontSize / 48) * 300),
              color: word.color,
              lineHeight: 1.2,
              cursor: "default",
              transition: "transform 0.2s",
              "&:hover": {
                transform: "scale(1.15)",
              },
            }}
          >
            {word.text}
          </Typography>
        </motion.div>
      ))}
    </Box>
  );
}
