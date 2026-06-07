import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  LinearProgress,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  useTheme,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import { motion } from "framer-motion";
import type { FactCheckResult } from "@/types/analytics";

interface FactCheckerProps {
  data: FactCheckResult;
}

function getCredibilityColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

function getCredibilityLabel(score: number): string {
  if (score >= 80) return "Highly Credible";
  if (score >= 60) return "Moderately Credible";
  if (score >= 40) return "Low Credibility";
  return "Not Credible";
}

const categoryColors: Record<string, string> = {
  statistical: "#7c3aed",
  temporal: "#06b6d4",
  entity: "#f59e0b",
  quantitative: "#ec4899",
};

function CredibilityGauge({ score, size = 180 }: { score: number; size?: number }) {
  const theme = useTheme();
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius * 0.75;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const color = getCredibilityColor(score);
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
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * 0.25}
            transform={`rotate(135 ${center} ${center})`}
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
            transform={`rotate(135 ${center} ${center})`}
            style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
          />
        </svg>
        <Box
          sx={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -45%)",
            textAlign: "center",
          }}
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.4, type: "spring", stiffness: 200 }}
          >
            <Typography variant="h3" fontWeight={800} sx={{ color, lineHeight: 1 }}>
              {Math.round(score)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              / 100
            </Typography>
          </motion.div>
        </Box>
      </Box>
      <Chip
        label={getCredibilityLabel(score)}
        sx={{ backgroundColor: `${color}20`, color, fontWeight: 600 }}
      />
    </Box>
  );
}

const itemVariants = {
  hidden: { opacity: 0, x: -15 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.06, duration: 0.3 },
  }),
};

export default function FactChecker({ data }: FactCheckerProps) {
  const theme = useTheme();

  return (
    <Box>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: 4,
          alignItems: "center",
          mb: 4,
        }}
      >
        <CredibilityGauge score={data.credibilityScore} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Fact Verification Report
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {data.claims.length} claims identified.{" "}
            {data.claims.filter((c) => c.verified).length} verified,{" "}
            {data.claims.filter((c) => !c.verified).length} unverified.
          </Typography>

          {/* Factual Density */}
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
              <Typography variant="caption" fontWeight={600}>
                Factual Density
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {Math.round(data.factualDensity * 100)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={data.factualDensity * 100}
              sx={{
                height: 8,
                borderRadius: 4,
                backgroundColor: theme.palette.divider,
                "& .MuiLinearProgress-bar": {
                  borderRadius: 4,
                  background: "linear-gradient(90deg, #7c3aed, #06b6d4)",
                },
              }}
            />
          </Box>
        </Box>
      </Box>

      {/* Vague Attribution Warning */}
      {data.vagueAttributions > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Alert severity="warning" sx={{ mb: 3, borderRadius: 2 }}>
            Found {data.vagueAttributions} unverifiable claim
            {data.vagueAttributions !== 1 ? "s" : ""} with vague attributions such as
            "studies show" or "experts say". Consider adding specific citations.
          </Alert>
        </motion.div>
      )}

      <Divider sx={{ mb: 3 }} />

      {/* Claims List */}
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        Claims Analysis
      </Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, mb: 4 }}>
        {data.claims.map((claim, i) => (
          <motion.div
            key={claim.id}
            custom={i}
            initial="hidden"
            animate="visible"
            variants={itemVariants}
          >
            <Card
              sx={{
                borderLeft: `4px solid ${claim.verified ? "#22c55e" : "#ef4444"}`,
                backgroundColor:
                  theme.palette.mode === "dark"
                    ? "rgba(255,255,255,0.02)"
                    : "rgba(0,0,0,0.01)",
              }}
            >
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 1.5,
                  }}
                >
                  {claim.verified ? (
                    <CheckCircleOutlineIcon
                      sx={{ color: "#22c55e", fontSize: 20, mt: 0.25 }}
                    />
                  ) : (
                    <CancelOutlinedIcon
                      sx={{ color: "#ef4444", fontSize: 20, mt: 0.25 }}
                    />
                  )}
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {claim.text}
                    </Typography>
                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                      <Chip
                        label={claim.category}
                        size="small"
                        sx={{
                          backgroundColor: `${categoryColors[claim.category] || "#666"}20`,
                          color: categoryColors[claim.category] || "#666",
                          fontWeight: 600,
                          textTransform: "capitalize",
                        }}
                      />
                      <Chip
                        label={`${Math.round(claim.confidence * 100)}% confidence`}
                        size="small"
                        variant="outlined"
                      />
                      {claim.source && (
                        <Chip
                          label={claim.source}
                          size="small"
                          variant="outlined"
                          color="primary"
                        />
                      )}
                    </Box>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </Box>

      {/* Tips */}
      {data.tips.length > 0 && (
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Recommendations
          </Typography>
          <Card
            sx={{
              backgroundColor:
                theme.palette.mode === "dark"
                  ? "rgba(124,58,237,0.08)"
                  : "rgba(124,58,237,0.04)",
              border: `1px solid ${theme.palette.divider}`,
            }}
          >
            <List dense>
              {data.tips.map((tip, i) => (
                <ListItem key={i}>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <LightbulbOutlinedIcon sx={{ color: "#f59e0b", fontSize: 20 }} />
                  </ListItemIcon>
                  <ListItemText
                    primary={tip}
                    primaryTypographyProps={{ variant: "body2" }}
                  />
                </ListItem>
              ))}
            </List>
          </Card>
        </Box>
      )}
    </Box>
  );
}
