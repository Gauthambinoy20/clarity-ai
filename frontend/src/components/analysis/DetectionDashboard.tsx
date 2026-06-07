import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Tabs,
  Tab,
  Divider,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import PersonOutlinedIcon from "@mui/icons-material/PersonOutlined";
import { motion } from "framer-motion";
import ScoreGauge from "@/components/common/ScoreGauge";
import SignalRadar from "@/components/analysis/SignalRadar";
import SignalBreakdown from "@/components/analysis/SignalBreakdown";
import SentenceHeatmap from "@/components/analysis/SentenceHeatmap";
import GLTRVisualization from "@/components/analysis/GLTRVisualization";
import type { DetectionResult } from "@/types/analysis";

interface DetectionDashboardProps {
  result: DetectionResult;
}

function getLabelIcon(label: string) {
  switch (label) {
    case "ai":
      return <SmartToyOutlinedIcon fontSize="small" />;
    case "human":
      return <PersonOutlinedIcon fontSize="small" />;
    default:
      return null;
  }
}

function getLabelColor(label: string): string {
  switch (label) {
    case "ai":
      return "#ef4444";
    case "human":
      return "#22c55e";
    case "mixed":
      return "#f59e0b";
    default:
      return "#a1a1aa";
  }
}

export default function DetectionDashboard({
  result,
}: DetectionDashboardProps) {
  const [bottomTab, setBottomTab] = useState(0);
  const labelColor = getLabelColor(result.label);

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Top row: Score + Attribution */}
        <Card>
          <CardContent>
            <Grid container spacing={3} alignItems="center">
              <Grid size={{ xs: 12, md: 4 }}>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "center",
                  }}
                >
                  <ScoreGauge
                    score={result.overallScore}
                    confidence={result.confidence}
                    label={
                      result.label === "ai"
                        ? "AI Generated"
                        : result.label === "human"
                        ? "Human Written"
                        : result.label === "mixed"
                        ? "Mixed Content"
                        : "Uncertain"
                    }
                  />
                </Box>
              </Grid>
              <Grid size={{ xs: 12, md: 8 }}>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Chip
                      icon={getLabelIcon(result.label) || undefined}
                      label={result.label.toUpperCase()}
                      sx={{
                        backgroundColor: `${labelColor}20`,
                        color: labelColor,
                        fontWeight: 700,
                        fontSize: "0.85rem",
                      }}
                    />
                    <Chip
                      label={`Confidence: ${Math.round(result.confidence * 100)}%`}
                      variant="outlined"
                      size="small"
                    />
                  </Box>

                  {result.attribution && (
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        gutterBottom
                      >
                        Possible Attribution
                      </Typography>
                      <Typography variant="body2" fontWeight={500}>
                        {result.attribution}
                      </Typography>
                    </Box>
                  )}

                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Analysis ID: {result.id}
                    </Typography>
                  </Box>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Middle row: Radar + Breakdown */}
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent>
                <SignalRadar signals={result.signals} />
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card
              sx={{
                height: "100%",
                maxHeight: 480,
                overflow: "auto",
              }}
            >
              <CardContent>
                <SignalBreakdown signals={result.signals} />
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Bottom: Heatmap / GLTR tabs */}
        <Card>
          <CardContent>
            <Tabs
              value={bottomTab}
              onChange={(_, v) => setBottomTab(v)}
              sx={{ mb: 2 }}
            >
              <Tab label="Sentence Heatmap" />
              <Tab label="GLTR Token Analysis" />
            </Tabs>
            <Divider sx={{ mb: 2 }} />

            {bottomTab === 0 && result.sentences.length > 0 && (
              <SentenceHeatmap sentences={result.sentences} />
            )}
            {bottomTab === 0 && result.sentences.length === 0 && (
              <Typography color="text.secondary" variant="body2">
                Sentence-level analysis not available for this mode.
              </Typography>
            )}
            {bottomTab === 1 && result.gltrTokens.length > 0 && (
              <GLTRVisualization tokens={result.gltrTokens} />
            )}
            {bottomTab === 1 && result.gltrTokens.length === 0 && (
              <Typography color="text.secondary" variant="body2">
                GLTR analysis not available for this mode.
              </Typography>
            )}
          </CardContent>
        </Card>
      </Box>
    </motion.div>
  );
}
