import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  useTheme,
  Divider,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { motion } from "framer-motion";
import type { ParaphraseResult } from "@/types/analytics";

interface ParaphraseDetectorProps {
  data: ParaphraseResult;
}

function getSimilarityColor(similarity: number): { color: string; label: string } {
  if (similarity >= 0.9) return { color: "#ef4444", label: "Self-Plagiarism" };
  if (similarity >= 0.8) return { color: "#f59e0b", label: "Repetition" };
  return { color: "#22c55e", label: "Acceptable" };
}

function UniqueContentGauge({ ratio, size = 180 }: { ratio: number; size?: number }) {
  const theme = useTheme();
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - ratio * circumference;
  const color = ratio >= 0.8 ? "#22c55e" : ratio >= 0.6 ? "#f59e0b" : "#ef4444";
  const center = size / 2;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1 }}>
      <Box sx={{ position: "relative", width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={theme.palette.divider}
            strokeWidth={8}
          />
          <motion.circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={8}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            transform={`rotate(-90 ${center} ${center})`}
            style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
          />
        </svg>
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            textAlign: "center",
          }}
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.4, type: "spring", stiffness: 200 }}
          >
            <Typography variant="h3" fontWeight={800} sx={{ color, lineHeight: 1 }}>
              {Math.round(ratio * 100)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Unique
            </Typography>
          </motion.div>
        </Box>
      </Box>
      <Chip
        label={ratio >= 0.8 ? "Original" : ratio >= 0.6 ? "Some Repetition" : "High Repetition"}
        sx={{ backgroundColor: `${color}20`, color, fontWeight: 600 }}
      />
    </Box>
  );
}

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.35, ease: "easeOut" },
  }),
};

export default function ParaphraseDetector({ data }: ParaphraseDetectorProps) {
  const theme = useTheme();

  return (
    <Box>
      {/* Header Stats */}
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: 4,
          alignItems: "center",
          mb: 4,
        }}
      >
        <UniqueContentGauge ratio={data.uniqueContentRatio} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Content Uniqueness Analysis
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {data.totalSentences} total sentences analyzed, {data.uniqueSentences} unique.
            {data.flaggedPairs.length > 0
              ? ` Found ${data.flaggedPairs.length} similar sentence pair${
                  data.flaggedPairs.length !== 1 ? "s" : ""
                }.`
              : " No repetitive sentences detected."}
          </Typography>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            <Chip
              size="small"
              label={`${data.totalSentences} sentences`}
              variant="outlined"
            />
            <Chip
              size="small"
              label={`${data.flaggedPairs.filter((p) => p.similarity >= 0.9).length} self-plagiarism`}
              sx={{ borderColor: "#ef4444", color: "#ef4444" }}
              variant="outlined"
            />
            <Chip
              size="small"
              label={`${data.flaggedPairs.filter((p) => p.similarity >= 0.8 && p.similarity < 0.9).length} repetitions`}
              sx={{ borderColor: "#f59e0b", color: "#f59e0b" }}
              variant="outlined"
            />
          </Box>
        </Box>
      </Box>

      <Divider sx={{ mb: 3 }} />

      {/* Flagged Sentence Pairs */}
      {data.flaggedPairs.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Flagged Sentence Pairs
          </Typography>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {data.flaggedPairs.map((pair, i) => {
              const { color, label } = getSimilarityColor(pair.similarity);
              return (
                <motion.div
                  key={`${pair.indexA}-${pair.indexB}`}
                  custom={i}
                  initial="hidden"
                  animate="visible"
                  variants={cardVariants}
                >
                  <Card
                    sx={{
                      borderLeft: `4px solid ${color}`,
                      backgroundColor:
                        theme.palette.mode === "dark"
                          ? "rgba(255,255,255,0.02)"
                          : "rgba(0,0,0,0.01)",
                    }}
                  >
                    <CardContent>
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          mb: 2,
                        }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          Sentences #{pair.indexA + 1} vs #{pair.indexB + 1}
                        </Typography>
                        <Chip
                          label={`${Math.round(pair.similarity * 100)}% - ${label}`}
                          size="small"
                          sx={{
                            backgroundColor: `${color}20`,
                            color,
                            fontWeight: 600,
                          }}
                        />
                      </Box>
                      <Box
                        sx={{
                          display: "grid",
                          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                          gap: 2,
                        }}
                      >
                        <Box
                          sx={{
                            p: 1.5,
                            borderRadius: 1.5,
                            backgroundColor:
                              theme.palette.mode === "dark"
                                ? "rgba(255,255,255,0.04)"
                                : "rgba(0,0,0,0.03)",
                          }}
                        >
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            fontWeight={600}
                            sx={{ mb: 0.5, display: "block" }}
                          >
                            Sentence A
                          </Typography>
                          <Typography variant="body2">{pair.sentenceA}</Typography>
                        </Box>
                        <Box
                          sx={{
                            p: 1.5,
                            borderRadius: 1.5,
                            backgroundColor:
                              theme.palette.mode === "dark"
                                ? "rgba(255,255,255,0.04)"
                                : "rgba(0,0,0,0.03)",
                          }}
                        >
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            fontWeight={600}
                            sx={{ mb: 0.5, display: "block" }}
                          >
                            Sentence B
                          </Typography>
                          <Typography variant="body2">{pair.sentenceB}</Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </Box>
        </Box>
      )}

      {/* Clusters */}
      {data.clusters.length > 0 && (
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Similarity Clusters
          </Typography>
          {data.clusters.map((cluster, i) => {
            const clusterColor =
              cluster.avgSimilarity >= 0.9
                ? "#ef4444"
                : cluster.avgSimilarity >= 0.8
                ? "#f59e0b"
                : "#22c55e";
            return (
              <motion.div
                key={cluster.label}
                custom={i}
                initial="hidden"
                animate="visible"
                variants={cardVariants}
              >
                <Accordion
                  sx={{
                    mb: 1,
                    borderRadius: "8px !important",
                    "&:before": { display: "none" },
                    border: `1px solid ${theme.palette.divider}`,
                  }}
                >
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                        width: "100%",
                      }}
                    >
                      <Typography variant="subtitle2" fontWeight={600}>
                        {cluster.label}
                      </Typography>
                      <Chip
                        label={`${cluster.sentences.length} sentences`}
                        size="small"
                        variant="outlined"
                      />
                      <Chip
                        label={`Avg: ${Math.round(cluster.avgSimilarity * 100)}%`}
                        size="small"
                        sx={{
                          backgroundColor: `${clusterColor}20`,
                          color: clusterColor,
                          fontWeight: 600,
                        }}
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                      {cluster.sentences.map((sentence, si) => (
                        <Box
                          key={si}
                          sx={{
                            p: 1.5,
                            borderRadius: 1.5,
                            backgroundColor:
                              theme.palette.mode === "dark"
                                ? "rgba(255,255,255,0.03)"
                                : "rgba(0,0,0,0.02)",
                          }}
                        >
                          <Typography variant="body2">{sentence}</Typography>
                        </Box>
                      ))}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              </motion.div>
            );
          })}
        </Box>
      )}

      {data.flaggedPairs.length === 0 && data.clusters.length === 0 && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography variant="h6" color="text.secondary">
            No repetitions or self-plagiarism detected.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Your content appears to be fully original.
          </Typography>
        </Box>
      )}
    </Box>
  );
}
