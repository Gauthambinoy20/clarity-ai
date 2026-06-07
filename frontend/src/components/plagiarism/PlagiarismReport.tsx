import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Link,
  Chip,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { motion } from "framer-motion";
import ScoreGauge from "@/components/common/ScoreGauge";
import type { PlagiarismResult } from "@/types/analysis";

interface PlagiarismReportProps {
  result: PlagiarismResult;
}

function getOriginalityColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

export default function PlagiarismReport({ result }: PlagiarismReportProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Originality Score */}
        <Card>
          <CardContent sx={{ textAlign: "center" }}>
            <ScoreGauge
              score={100 - result.originalityScore}
              label={
                result.originalityScore >= 80
                  ? "Highly Original"
                  : result.originalityScore >= 60
                  ? "Mostly Original"
                  : "Significant Matches Found"
              }
            />
            <Typography
              variant="h6"
              sx={{
                mt: 2,
                color: getOriginalityColor(result.originalityScore),
              }}
            >
              {result.originalityScore}% Original Content
            </Typography>
          </CardContent>
        </Card>

        {/* Paragraph Scores */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Paragraph Analysis
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {result.paragraphs.map((para, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.08 }}
                >
                  <Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        mb: 0.5,
                      }}
                    >
                      <Typography variant="body2" fontWeight={500}>
                        Paragraph {index + 1}
                      </Typography>
                      <Chip
                        label={`${Math.round(para.score)}% match`}
                        size="small"
                        sx={{
                          backgroundColor:
                            para.score > 40
                              ? "#ef444420"
                              : para.score > 20
                              ? "#f59e0b20"
                              : "#22c55e20",
                          color:
                            para.score > 40
                              ? "#ef4444"
                              : para.score > 20
                              ? "#f59e0b"
                              : "#22c55e",
                          fontWeight: 600,
                        }}
                      />
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={para.score}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        backgroundColor: "divider",
                        mb: 1,
                        "& .MuiLinearProgress-bar": {
                          borderRadius: 3,
                          backgroundColor:
                            para.score > 40
                              ? "#ef4444"
                              : para.score > 20
                              ? "#f59e0b"
                              : "#22c55e",
                        },
                      }}
                    />
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}
                    >
                      {para.text}
                    </Typography>
                  </Box>
                  {index < result.paragraphs.length - 1 && (
                    <Divider sx={{ mt: 2 }} />
                  )}
                </motion.div>
              ))}
            </Box>
          </CardContent>
        </Card>

        {/* Sources */}
        {result.sources.length > 0 && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Matched Sources ({result.sources.length})
              </Typography>
              {result.sources.map((source, index) => (
                <Accordion
                  key={index}
                  sx={{
                    backgroundColor: "transparent",
                    border: "1px solid",
                    borderColor: "divider",
                    "&:before": { display: "none" },
                    mb: 1,
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
                      <Chip
                        label={`${Math.round(source.similarity * 100)}%`}
                        size="small"
                        color={
                          source.similarity > 0.7
                            ? "error"
                            : source.similarity > 0.4
                            ? "warning"
                            : "success"
                        }
                      />
                      <Typography variant="body2" fontWeight={500} noWrap>
                        {source.title}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box
                      sx={{
                        p: 2,
                        backgroundColor: "background.default",
                        borderRadius: 1,
                        mb: 1.5,
                      }}
                    >
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        gutterBottom
                      >
                        Matched text:
                      </Typography>
                      <Typography variant="body2">
                        {source.matchedText}
                      </Typography>
                    </Box>
                    <Link
                      href={source.url}
                      target="_blank"
                      rel="noopener"
                      sx={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 0.5,
                        fontSize: "0.85rem",
                      }}
                    >
                      View Source <OpenInNewIcon sx={{ fontSize: 14 }} />
                    </Link>
                  </AccordionDetails>
                </Accordion>
              ))}
            </CardContent>
          </Card>
        )}
      </Box>
    </motion.div>
  );
}
