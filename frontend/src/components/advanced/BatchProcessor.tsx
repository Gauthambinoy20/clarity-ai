import { useState, useCallback, useRef } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  TextField,
  Tooltip,
  alpha,
  useTheme,
} from "@mui/material";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import DownloadIcon from "@mui/icons-material/Download";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import { motion, AnimatePresence } from "framer-motion";

/* ─── Types ──────────────────────────────────────────────────────── */

export interface BatchItem {
  id: string;
  filename: string;
  text: string;
  wordCount: number;
  aiScore: number | null;
  classification: string | null;
  status: "pending" | "processing" | "done" | "error";
  error?: string;
}

export interface BatchSummary {
  totalFiles: number;
  processed: number;
  flagged: number;
  avgScore: number;
}

interface BatchProcessorProps {
  onProcessBatch?: (items: BatchItem[]) => Promise<BatchItem[]>;
}

/* ─── Helpers ────────────────────────────────────────────────────── */

let batchIdCounter = 0;
const nextId = () => `batch-${++batchIdCounter}-${Date.now()}`;

const scoreColor = (score: number | null) => {
  if (score === null) return "text.secondary";
  if (score > 70) return "#ef4444";
  if (score > 40) return "#f59e0b";
  return "#22c55e";
};

const rowBg = (score: number | null, theme: ReturnType<typeof useTheme>) => {
  if (score === null) return "transparent";
  const c = score > 70 ? "#ef4444" : score > 40 ? "#f59e0b" : "#22c55e";
  return alpha(c, 0.06);
};

const classificationChip = (label: string | null) => {
  if (!label) return null;
  const config: Record<string, { color: string; bg: string }> = {
    ai: { color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
    mixed: { color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
    human: { color: "#22c55e", bg: "rgba(34,197,94,0.12)" },
  };
  const c = config[label] || config.mixed;
  return (
    <Chip
      label={label.charAt(0).toUpperCase() + label.slice(1)}
      size="small"
      sx={{
        backgroundColor: c.bg,
        color: c.color,
        fontWeight: 600,
        fontSize: "0.7rem",
      }}
    />
  );
};

const statusIcon = (status: string) => {
  switch (status) {
    case "done":
      return <CheckCircleOutlineIcon sx={{ color: "#22c55e", fontSize: 18 }} />;
    case "error":
      return <ErrorOutlineIcon sx={{ color: "#ef4444", fontSize: 18 }} />;
    case "processing":
      return (
        <HourglassEmptyIcon
          sx={{
            color: "#f59e0b",
            fontSize: 18,
            animation: "spin 1.5s linear infinite",
            "@keyframes spin": {
              "0%": { transform: "rotate(0deg)" },
              "100%": { transform: "rotate(360deg)" },
            },
          }}
        />
      );
    default:
      return <HourglassEmptyIcon sx={{ color: "text.disabled", fontSize: 18 }} />;
  }
};

/* ─── Main Component ─────────────────────────────────────────────── */

export default function BatchProcessor({ onProcessBatch }: BatchProcessorProps) {
  const theme = useTheme();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<BatchItem[]>([]);
  const [pasteText, setPasteText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);

  const summary: BatchSummary = {
    totalFiles: items.length,
    processed: items.filter((i) => i.status === "done").length,
    flagged: items.filter((i) => i.aiScore !== null && i.aiScore > 70).length,
    avgScore:
      items.filter((i) => i.aiScore !== null).length > 0
        ? Math.round(
            items
              .filter((i) => i.aiScore !== null)
              .reduce((sum, i) => sum + (i.aiScore || 0), 0) /
              items.filter((i) => i.aiScore !== null).length
          )
        : 0,
  };

  /* File handling */
  const handleFiles = useCallback((files: FileList | File[]) => {
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const words = text.trim().split(/\s+/).length;
        setItems((prev) => [
          ...prev,
          {
            id: nextId(),
            filename: file.name,
            text,
            wordCount: words,
            aiScore: null,
            classification: null,
            status: "pending",
          },
        ]);
      };
      reader.readAsText(file);
    });
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles]
  );

  /* Paste handling */
  const handlePasteSubmit = useCallback(() => {
    if (!pasteText.trim()) return;
    const segments = pasteText.split("---").filter((s) => s.trim());
    segments.forEach((seg, idx) => {
      const text = seg.trim();
      const words = text.split(/\s+/).length;
      setItems((prev) => [
        ...prev,
        {
          id: nextId(),
          filename: `Text ${prev.length + 1}`,
          text,
          wordCount: words,
          aiScore: null,
          classification: null,
          status: "pending",
        },
      ]);
    });
    setPasteText("");
  }, [pasteText]);

  /* Process all */
  const handleProcessAll = useCallback(async () => {
    setIsProcessing(true);
    setProgress(0);

    const pending = items.filter((i) => i.status === "pending" || i.status === "error");
    for (let idx = 0; idx < pending.length; idx++) {
      const item = pending[idx];
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, status: "processing" } : i))
      );

      try {
        if (onProcessBatch) {
          const results = await onProcessBatch([item]);
          if (results[0]) {
            setItems((prev) =>
              prev.map((i) => (i.id === item.id ? results[0] : i))
            );
          }
        } else {
          // Demo mode: simulate processing
          await new Promise((r) => setTimeout(r, 600 + Math.random() * 800));
          const fakeScore = Math.round(Math.random() * 100);
          const label = fakeScore > 70 ? "ai" : fakeScore > 40 ? "mixed" : "human";
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? { ...i, aiScore: fakeScore, classification: label, status: "done" }
                : i
            )
          );
        }
      } catch {
        setItems((prev) =>
          prev.map((i) =>
            i.id === item.id ? { ...i, status: "error", error: "Processing failed" } : i
          )
        );
      }

      setProgress(Math.round(((idx + 1) / pending.length) * 100));
    }

    setIsProcessing(false);
  }, [items, onProcessBatch]);

  /* Export */
  const handleExport = useCallback(() => {
    const csv = [
      ["Filename", "Words", "AI Score", "Classification", "Status"].join(","),
      ...items.map((i) =>
        [i.filename, i.wordCount, i.aiScore ?? "", i.classification ?? "", i.status].join(",")
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "batch-results.csv";
    a.click();
    URL.revokeObjectURL(url);
  }, [items]);

  const handleRemoveItem = useCallback((id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  }, []);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {/* Summary Header */}
      {items.length > 0 && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <Card
            sx={{
              background: `linear-gradient(135deg, ${alpha(
                theme.palette.primary.main,
                0.06
              )} 0%, ${alpha(theme.palette.secondary.main, 0.06)} 100%)`,
              border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}`,
            }}
          >
            <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
                <Typography variant="body1" fontWeight={700}>
                  {summary.processed} of {summary.totalFiles} files processed
                </Typography>
                <Chip
                  label={`${summary.flagged} flagged`}
                  size="small"
                  sx={{
                    backgroundColor: alpha("#ef4444", 0.12),
                    color: "#ef4444",
                    fontWeight: 600,
                  }}
                />
                <Chip
                  label={`Avg score: ${summary.avgScore}%`}
                  size="small"
                  variant="outlined"
                  sx={{ fontWeight: 600 }}
                />
                <Box sx={{ flex: 1 }} />
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<DownloadIcon />}
                  onClick={handleExport}
                  disabled={summary.processed === 0}
                >
                  Export Results
                </Button>
              </Box>
              {isProcessing && (
                <LinearProgress
                  variant="determinate"
                  value={progress}
                  sx={{
                    mt: 1.5,
                    height: 6,
                    borderRadius: 3,
                    "& .MuiLinearProgress-bar": {
                      borderRadius: 3,
                      background: `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
                    },
                  }}
                />
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Drag & Drop + Paste Zone */}
      <Card>
        <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
          <Box
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            sx={{
              border: `2px dashed ${
                dragOver ? theme.palette.primary.main : alpha(theme.palette.divider, 0.4)
              }`,
              borderRadius: 3,
              p: 4,
              textAlign: "center",
              cursor: "pointer",
              transition: "all 0.2s",
              backgroundColor: dragOver ? alpha(theme.palette.primary.main, 0.04) : "transparent",
              "&:hover": {
                borderColor: theme.palette.primary.main,
                backgroundColor: alpha(theme.palette.primary.main, 0.02),
              },
            }}
          >
            <CloudUploadOutlinedIcon
              sx={{ fontSize: 48, color: "text.secondary", mb: 1 }}
            />
            <Typography variant="body1" fontWeight={600}>
              Drop files here or click to upload
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Supports .txt, .doc, .pdf files. Multiple files allowed.
            </Typography>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".txt,.doc,.docx,.pdf"
              style={{ display: "none" }}
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
            />
          </Box>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ textAlign: "center", my: 2 }}
          >
            or paste multiple texts separated by ---
          </Typography>

          <TextField
            multiline
            rows={4}
            fullWidth
            placeholder={"First text content here...\n---\nSecond text content here...\n---\nThird text..."}
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            sx={{
              "& .MuiOutlinedInput-root": {
                fontFamily: "monospace",
                fontSize: "0.85rem",
              },
            }}
          />
          <Box sx={{ display: "flex", gap: 1.5, mt: 2 }}>
            <Button
              variant="outlined"
              size="small"
              onClick={handlePasteSubmit}
              disabled={!pasteText.trim()}
            >
              Add Texts
            </Button>
            <Box sx={{ flex: 1 }} />
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon />}
              onClick={handleProcessAll}
              disabled={isProcessing || items.filter((i) => i.status === "pending" || i.status === "error").length === 0}
              sx={{
                background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
              }}
            >
              {isProcessing ? "Processing..." : "Process All"}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Results Table */}
      <AnimatePresence>
        {items.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <TableContainer
              component={Paper}
              sx={{
                borderRadius: 3,
                border: `1px solid ${alpha(theme.palette.divider, 0.3)}`,
              }}
            >
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>File</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 700 }}>
                      Words
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 700 }}>
                      AI Score
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 700 }}>
                      Classification
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 700 }}>
                      Status
                    </TableCell>
                    <TableCell align="center" sx={{ fontWeight: 700 }}>
                      Actions
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {items.map((item, idx) => (
                    <motion.tr
                      key={item.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: idx * 0.04 }}
                      style={{ backgroundColor: rowBg(item.aiScore, theme) }}
                    >
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <InsertDriveFileOutlinedIcon
                            sx={{ fontSize: 18, color: "text.secondary" }}
                          />
                          <Typography variant="body2" fontWeight={500} noWrap sx={{ maxWidth: 200 }}>
                            {item.filename}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2">{item.wordCount}</Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography
                          variant="body2"
                          fontWeight={700}
                          sx={{ color: scoreColor(item.aiScore) }}
                        >
                          {item.aiScore !== null ? `${item.aiScore}%` : "--"}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        {classificationChip(item.classification)}
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title={item.error || item.status}>
                          {statusIcon(item.status)}
                        </Tooltip>
                      </TableCell>
                      <TableCell align="center">
                        <IconButton
                          size="small"
                          onClick={() => handleRemoveItem(item.id)}
                          disabled={item.status === "processing"}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </motion.tr>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </motion.div>
        )}
      </AnimatePresence>
    </Box>
  );
}
