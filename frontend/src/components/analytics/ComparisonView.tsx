import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  useTheme,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import { motion } from "framer-motion";
import type { ComparisonResult } from "@/types/analytics";

interface ComparisonViewProps {
  data: ComparisonResult;
  textA: string;
  textB: string;
}

function SimilarityGauge({ score }: { score: number }) {
  const theme = useTheme();
  const size = 150;
  const strokeWidth = 14;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - score / 100);

  const getColor = () => {
    if (score >= 80) return theme.palette.error.main;
    if (score >= 50) return theme.palette.warning.main;
    return theme.palette.success.main;
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ textAlign: "center" }}>
        <Box sx={{ position: "relative", display: "inline-block" }}>
          <svg width={size} height={size}>
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={theme.palette.divider}
              strokeWidth={strokeWidth}
            />
            <motion.circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke={getColor()}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ delay: 0.3, duration: 1, ease: "easeOut" }}
              transform={`rotate(-90 ${size / 2} ${size / 2})`}
            />
          </svg>
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Typography variant="h3" fontWeight={800}>
              {score.toFixed(1)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Similarity
            </Typography>
          </Box>
        </Box>
      </Box>
    </motion.div>
  );
}

export default function ComparisonView({
  data,
  textA,
  textB,
}: ComparisonViewProps) {
  const theme = useTheme();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Similarity gauge */}
        <Card>
          <CardContent sx={{ py: 4 }}>
            <SimilarityGauge score={data.similarity_score} />
          </CardContent>
        </Card>

        {/* Side-by-side diff */}
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Text Comparison
            </Typography>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    border: "1px solid",
                    borderColor: "divider",
                    maxHeight: 400,
                    overflow: "auto",
                    backgroundColor: "action.hover",
                  }}
                >
                  <Typography
                    variant="caption"
                    fontWeight={600}
                    color="primary.main"
                    sx={{ display: "block", mb: 1 }}
                  >
                    Text A
                  </Typography>
                  <Box sx={{ fontFamily: "monospace", fontSize: "0.85rem", lineHeight: 1.8 }}>
                    {data.diff_data.map((segment, i) => {
                      if (segment.type === "equal") {
                        return <span key={i}>{segment.text}</span>;
                      }
                      if (segment.type === "delete" || segment.type === "replace") {
                        return (
                          <Box
                            key={i}
                            component="span"
                            sx={{
                              backgroundColor: "rgba(239,68,68,0.2)",
                              textDecoration: "line-through",
                              borderRadius: 0.5,
                              px: 0.3,
                            }}
                          >
                            {segment.text}
                          </Box>
                        );
                      }
                      return null;
                    })}
                  </Box>
                </Box>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    border: "1px solid",
                    borderColor: "divider",
                    maxHeight: 400,
                    overflow: "auto",
                    backgroundColor: "action.hover",
                  }}
                >
                  <Typography
                    variant="caption"
                    fontWeight={600}
                    color="secondary.main"
                    sx={{ display: "block", mb: 1 }}
                  >
                    Text B
                  </Typography>
                  <Box sx={{ fontFamily: "monospace", fontSize: "0.85rem", lineHeight: 1.8 }}>
                    {data.diff_data.map((segment, i) => {
                      if (segment.type === "equal") {
                        return <span key={i}>{segment.text}</span>;
                      }
                      if (segment.type === "insert") {
                        return (
                          <Box
                            key={i}
                            component="span"
                            sx={{
                              backgroundColor: "rgba(34,197,94,0.2)",
                              borderRadius: 0.5,
                              px: 0.3,
                            }}
                          >
                            {segment.text}
                          </Box>
                        );
                      }
                      if (segment.type === "replace") {
                        return (
                          <Box
                            key={i}
                            component="span"
                            sx={{
                              backgroundColor: "rgba(34,197,94,0.2)",
                              borderRadius: 0.5,
                              px: 0.3,
                            }}
                          >
                            {segment.text_b || ""}
                          </Box>
                        );
                      }
                      return null;
                    })}
                  </Box>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Structural comparison table */}
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Structural Comparison
            </Typography>
            <TableContainer sx={{ mt: 1 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Metric</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600, color: "primary.main" }}>
                      Text A
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600, color: "secondary.main" }}>
                      Text B
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600 }}>
                      Difference
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {[
                    {
                      label: "Word Count",
                      a: data.text_a_stats.word_count,
                      b: data.text_b_stats.word_count,
                    },
                    {
                      label: "Sentences",
                      a: data.text_a_stats.sentence_count,
                      b: data.text_b_stats.sentence_count,
                    },
                    {
                      label: "Avg Sentence Length",
                      a: data.text_a_stats.avg_sentence_length.toFixed(1),
                      b: data.text_b_stats.avg_sentence_length.toFixed(1),
                    },
                    {
                      label: "Vocabulary Size",
                      a: data.text_a_stats.vocabulary_size,
                      b: data.text_b_stats.vocabulary_size,
                    },
                    {
                      label: "Vocabulary Overlap",
                      a: `${(data.vocabulary_overlap * 100).toFixed(1)}%`,
                      b: `${(data.vocabulary_overlap * 100).toFixed(1)}%`,
                      noDiff: true,
                    },
                  ].map((row) => (
                    <TableRow key={row.label}>
                      <TableCell>{row.label}</TableCell>
                      <TableCell align="center">{row.a}</TableCell>
                      <TableCell align="center">{row.b}</TableCell>
                      <TableCell align="center">
                        {row.noDiff ? (
                          "--"
                        ) : (
                          <Chip
                            label={
                              typeof row.a === "number" && typeof row.b === "number"
                                ? row.a - row.b > 0
                                  ? `+${row.a - row.b}`
                                  : `${row.a - row.b}`
                                : "--"
                            }
                            size="small"
                            variant="outlined"
                            sx={{ fontWeight: 600, fontSize: "0.75rem", height: 22 }}
                          />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>

        {/* Common Phrases */}
        {data.common_phrases.length > 0 && (
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Common Phrases
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1 }}>
                {data.common_phrases.map((phrase, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.03, duration: 0.3 }}
                  >
                    <Chip
                      label={phrase}
                      variant="outlined"
                      sx={{
                        fontFamily: "monospace",
                        fontSize: "0.8rem",
                      }}
                    />
                  </motion.div>
                ))}
              </Box>
            </CardContent>
          </Card>
        )}
      </Box>
    </motion.div>
  );
}
