import { Box, Typography, useTheme } from "@mui/material";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { SignalScore } from "@/types/analysis";

interface SignalRadarProps {
  signals: SignalScore[];
}

export default function SignalRadar({ signals }: SignalRadarProps) {
  const theme = useTheme();

  const data = signals.map((s) => ({
    name: s.name.replace(/_/g, " "),
    score: Math.round(s.score * 100),
    fullMark: 100,
  }));

  return (
    <Box sx={{ width: "100%", height: 400 }}>
      <Typography variant="h6" gutterBottom>
        Signal Radar
      </Typography>
      <ResponsiveContainer width="100%" height="90%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke={theme.palette.divider} />
          <PolarAngleAxis
            dataKey="name"
            tick={{
              fill: theme.palette.text.secondary,
              fontSize: 11,
            }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: theme.palette.text.secondary, fontSize: 10 }}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke={theme.palette.primary.main}
            fill={theme.palette.primary.main}
            fillOpacity={0.25}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: theme.palette.background.paper,
              border: `1px solid ${theme.palette.divider}`,
              borderRadius: 8,
              color: theme.palette.text.primary,
            }}
            formatter={(value: number) => [`${value}%`, "Score"]}
          />
        </RadarChart>
      </ResponsiveContainer>
    </Box>
  );
}
