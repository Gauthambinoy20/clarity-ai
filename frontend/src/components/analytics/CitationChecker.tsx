import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  LinearProgress,
  Divider,
  useTheme,
} from "@mui/material";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import FormatQuoteOutlinedIcon from "@mui/icons-material/FormatQuoteOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import { motion } from "framer-motion";
import type { CitationResult } from "@/types/analytics";

interface CitationCheckerProps {
  data: CitationResult;
}

export default function CitationChecker({ data }: CitationCheckerProps) {
  const theme = useTheme();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {/* Summary row */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr 1fr" },
            gap: 2,
          }}
        >
          <Card>
            <CardContent sx={{ textAlign: "center", py: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Detected Style
              </Typography>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
              >
                <Chip
                  icon={<FormatQuoteOutlinedIcon />}
                  label={data.detected_style || "Unknown"}
                  color="primary"
                  sx={{
                    mt: 1,
                    fontWeight: 600,
                    fontSize: "0.9rem",
                    height: 36,
                  }}
                />
              </motion.div>
            </CardContent>
          </Card>

          <Card>
            <CardContent sx={{ textAlign: "center", py: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Total Citations
              </Typography>
              <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
                {data.total_citations}
              </Typography>
            </CardContent>
          </Card>

          <Card>
            <CardContent sx={{ textAlign: "center", py: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Valid / Invalid
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "center",
                  gap: 1,
                  mt: 0.5,
                }}
              >
                <Chip
                  label={data.valid_count}
                  size="small"
                  sx={{
                    fontWeight: 700,
                    backgroundColor: "success.main",
                    color: "#fff",
                  }}
                />
                <Typography variant="h5" fontWeight={300} color="text.secondary">
                  /
                </Typography>
                <Chip
                  label={data.invalid_count}
                  size="small"
                  sx={{
                    fontWeight: 700,
                    backgroundColor:
                      data.invalid_count > 0 ? "error.main" : "success.main",
                    color: "#fff",
                  }}
                />
              </Box>
            </CardContent>
          </Card>

          <Card>
            <CardContent sx={{ textAlign: "center", py: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Format Consistency
              </Typography>
              <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
                {data.format_consistency_score}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={data.format_consistency_score}
                sx={{
                  height: 6,
                  borderRadius: 3,
                  mt: 1,
                  backgroundColor: "action.hover",
                  "& .MuiLinearProgress-bar": {
                    borderRadius: 3,
                    backgroundColor:
                      data.format_consistency_score >= 80
                        ? "success.main"
                        : data.format_consistency_score >= 50
                        ? "warning.main"
                        : "error.main",
                  },
                }}
              />
            </CardContent>
          </Card>
        </Box>

        {/* Citation list */}
        <Card>
          <CardContent>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Found Citations
            </Typography>
            {data.citations.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 4 }}>
                <FormatQuoteOutlinedIcon
                  sx={{ fontSize: 48, color: "text.disabled", mb: 1 }}
                />
                <Typography color="text.secondary">
                  No citations detected in the text.
                </Typography>
              </Box>
            ) : (
              <List>
                {data.citations.map((citation, i) => (
                  <motion.div
                    key={citation.id}
                    initial={{ opacity: 0, x: -15 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05, duration: 0.3 }}
                  >
                    <ListItem
                      sx={{
                        mb: 1,
                        borderRadius: 2,
                        border: "1px solid",
                        borderColor: citation.is_valid
                          ? "success.main"
                          : "error.main",
                        backgroundColor: citation.is_valid
                          ? "rgba(34,197,94,0.05)"
                          : "rgba(239,68,68,0.05)",
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 40 }}>
                        {citation.is_valid ? (
                          <CheckCircleOutlinedIcon
                            sx={{ color: "success.main" }}
                          />
                        ) : (
                          <CancelOutlinedIcon sx={{ color: "error.main" }} />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Typography
                            variant="body2"
                            fontWeight={500}
                            sx={{ fontFamily: "monospace", fontSize: "0.85rem" }}
                          >
                            {citation.text}
                          </Typography>
                        }
                        secondary={
                          <Box sx={{ mt: 0.5 }}>
                            {citation.authors.length > 0 && (
                              <Typography variant="caption" color="text.secondary">
                                Authors: {citation.authors.join(", ")}
                                {citation.year && ` (${citation.year})`}
                              </Typography>
                            )}
                            {citation.issues.length > 0 && (
                              <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                                {citation.issues.map((issue, j) => (
                                  <Chip
                                    key={j}
                                    label={issue}
                                    size="small"
                                    variant="outlined"
                                    color="error"
                                    sx={{ fontSize: "0.65rem", height: 20 }}
                                  />
                                ))}
                              </Box>
                            )}
                          </Box>
                        }
                      />
                      <Chip
                        label={citation.style_detected}
                        size="small"
                        variant="outlined"
                        sx={{ fontWeight: 500, fontSize: "0.7rem" }}
                      />
                    </ListItem>
                  </motion.div>
                ))}
              </List>
            )}
          </CardContent>
        </Card>

        {/* Missing references */}
        {data.missing_references.length > 0 && (
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Missing References
              </Typography>
              {data.missing_references.map((ref, i) => (
                <Alert
                  key={i}
                  severity="warning"
                  icon={<WarningAmberOutlinedIcon />}
                  sx={{ mb: 1, borderRadius: 2 }}
                >
                  {ref}
                </Alert>
              ))}
            </CardContent>
          </Card>
        )}

        {/* General issues */}
        {data.issues.length > 0 && (
          <Card>
            <CardContent>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Citation Issues
              </Typography>
              {data.issues.map((issue, i) => (
                <Alert
                  key={i}
                  severity="info"
                  sx={{ mb: 1, borderRadius: 2 }}
                >
                  {issue}
                </Alert>
              ))}
            </CardContent>
          </Card>
        )}
      </Box>
    </motion.div>
  );
}
