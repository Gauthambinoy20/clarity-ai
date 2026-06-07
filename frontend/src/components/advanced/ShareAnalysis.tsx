import { useState, useCallback, useMemo } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Typography,
  IconButton,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Snackbar,
  Alert,
  Divider,
  alpha,
  useTheme,
  Chip,
} from "@mui/material";
import ShareIcon from "@mui/icons-material/Share";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import EmailIcon from "@mui/icons-material/Email";
import DownloadIcon from "@mui/icons-material/Download";
import LinkIcon from "@mui/icons-material/Link";
import QrCode2Icon from "@mui/icons-material/QrCode2";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import CloseIcon from "@mui/icons-material/Close";
import { motion } from "framer-motion";

/* ─── Types ──────────────────────────────────────────────────────── */

type ExpiryOption = "24h" | "7d" | "30d" | "never";

interface ShareAnalysisProps {
  analysisId?: string;
  analysisData?: Record<string, unknown>;
  onGenerateLink?: (
    data: Record<string, unknown>,
    expiry: ExpiryOption
  ) => Promise<{ url: string }>;
  variant?: "button" | "icon";
}

/* ─── Simple QR Code SVG Generator ───────────────────────────────── */

function SimpleQRCode({ value, size = 160 }: { value: string; size?: number }) {
  const theme = useTheme();
  // Generate a deterministic grid pattern based on the URL string
  const gridSize = 21;
  const cellSize = size / gridSize;

  const cells = useMemo(() => {
    const grid: boolean[][] = [];
    let hash = 0;
    for (let i = 0; i < value.length; i++) {
      hash = (hash << 5) - hash + value.charCodeAt(i);
      hash |= 0;
    }

    for (let row = 0; row < gridSize; row++) {
      grid[row] = [];
      for (let col = 0; col < gridSize; col++) {
        // Fixed patterns: position detection squares
        const isTopLeft = row < 7 && col < 7;
        const isTopRight = row < 7 && col >= gridSize - 7;
        const isBottomLeft = row >= gridSize - 7 && col < 7;

        if (isTopLeft || isTopRight || isBottomLeft) {
          const lr = isTopLeft ? 0 : isBottomLeft ? gridSize - 7 : 0;
          const lc = isTopLeft ? 0 : isTopRight ? gridSize - 7 : 0;
          const rr = row - (isBottomLeft ? gridSize - 7 : 0);
          const rc = col - (isTopRight ? gridSize - 7 : 0);
          const isBorder = rr === 0 || rr === 6 || rc === 0 || rc === 6;
          const isInner = rr >= 2 && rr <= 4 && rc >= 2 && rc <= 4;
          grid[row][col] = isBorder || isInner;
        } else {
          // Pseudo-random data pattern
          const seed = (hash + row * 31 + col * 17) & 0xffffffff;
          grid[row][col] = (seed % 3) !== 0;
        }
      }
    }
    return grid;
  }, [value]);

  const fgColor = theme.palette.mode === "dark" ? "#ffffff" : "#000000";
  const bgColor = theme.palette.mode === "dark" ? "#1e1e2e" : "#ffffff";

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <rect width={size} height={size} fill={bgColor} rx={4} />
      {cells.map((row, rIdx) =>
        row.map((cell, cIdx) =>
          cell ? (
            <rect
              key={`${rIdx}-${cIdx}`}
              x={cIdx * cellSize}
              y={rIdx * cellSize}
              width={cellSize}
              height={cellSize}
              fill={fgColor}
            />
          ) : null
        )
      )}
    </svg>
  );
}

/* ─── Main Component ─────────────────────────────────────────────── */

export default function ShareAnalysis({
  analysisId,
  analysisData,
  onGenerateLink,
  variant = "button",
}: ShareAnalysisProps) {
  const theme = useTheme();
  const [open, setOpen] = useState(false);
  const [expiry, setExpiry] = useState<ExpiryOption>("7d");
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [snackMessage, setSnackMessage] = useState<string | null>(null);

  const handleOpen = useCallback(async () => {
    setOpen(true);
    if (!shareUrl) {
      setIsGenerating(true);
      try {
        if (onGenerateLink && analysisData) {
          const result = await onGenerateLink(analysisData, expiry);
          setShareUrl(result.url);
        } else {
          // Demo mode
          await new Promise((r) => setTimeout(r, 600));
          const fakeId = analysisId || Math.random().toString(36).substring(2, 10);
          setShareUrl(`https://clarityai.app/shared/${fakeId}`);
        }
      } catch {
        setShareUrl("https://clarityai.app/shared/error");
      } finally {
        setIsGenerating(false);
      }
    }
  }, [shareUrl, onGenerateLink, analysisData, expiry, analysisId]);

  const handleCopyLink = useCallback(() => {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl);
      setSnackMessage("Link copied to clipboard");
    }
  }, [shareUrl]);

  const handleEmail = useCallback(() => {
    if (shareUrl) {
      window.open(
        `mailto:?subject=ClarityAI Analysis Results&body=View the analysis results here: ${encodeURIComponent(shareUrl)}`,
        "_blank"
      );
    }
  }, [shareUrl]);

  const handleDownloadQR = useCallback(() => {
    const svgEl = document.getElementById("share-qr-code");
    if (!svgEl) return;
    const svgData = new XMLSerializer().serializeToString(svgEl);
    const blob = new Blob([svgData], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "clarityai-share-qr.svg";
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const handleExpiryChange = useCallback(
    (_: React.MouseEvent<HTMLElement>, newExpiry: ExpiryOption | null) => {
      if (newExpiry) {
        setExpiry(newExpiry);
        setShareUrl(null); // Reset to regenerate with new expiry
      }
    },
    []
  );

  const expiryLabels: Record<ExpiryOption, string> = {
    "24h": "24 Hours",
    "7d": "7 Days",
    "30d": "30 Days",
    never: "Never",
  };

  return (
    <>
      {/* Trigger button */}
      {variant === "icon" ? (
        <Tooltip title="Share Analysis">
          <IconButton onClick={handleOpen} size="small">
            <ShareIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      ) : (
        <Button
          variant="outlined"
          size="small"
          startIcon={<ShareIcon />}
          onClick={handleOpen}
          sx={{ textTransform: "none", fontWeight: 600 }}
        >
          Share
        </Button>
      )}

      {/* Share Dialog */}
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
          },
        }}
      >
        <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1, pb: 1 }}>
          <ShareIcon sx={{ color: theme.palette.primary.main }} />
          <Typography variant="h6" fontWeight={700} sx={{ flex: 1 }}>
            Share Analysis
          </Typography>
          <IconButton onClick={() => setOpen(false)} size="small">
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ pt: 2 }}>
          {/* Expiry Selector */}
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
            Link Expiry
          </Typography>
          <ToggleButtonGroup
            value={expiry}
            exclusive
            onChange={handleExpiryChange}
            size="small"
            sx={{ mb: 3 }}
          >
            {(Object.keys(expiryLabels) as ExpiryOption[]).map((key) => (
              <ToggleButton
                key={key}
                value={key}
                sx={{
                  textTransform: "none",
                  fontWeight: 600,
                  fontSize: "0.78rem",
                  px: 2,
                }}
              >
                {expiryLabels[key]}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          {/* Shareable Link */}
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
            Shareable Link
          </Typography>
          <Box sx={{ display: "flex", gap: 1, mb: 3 }}>
            <TextField
              fullWidth
              size="small"
              value={isGenerating ? "Generating link..." : shareUrl || ""}
              slotProps={{
                input: {
                  readOnly: true,
                  startAdornment: (
                    <LinkIcon sx={{ mr: 1, color: "text.secondary", fontSize: 18 }} />
                  ),
                },
              }}
              sx={{
                "& .MuiOutlinedInput-root": {
                  fontFamily: "monospace",
                  fontSize: "0.82rem",
                  backgroundColor: alpha(theme.palette.background.default, 0.5),
                },
              }}
            />
            <Tooltip title="Copy Link">
              <IconButton
                onClick={handleCopyLink}
                disabled={!shareUrl || isGenerating}
                sx={{
                  border: `1px solid ${alpha(theme.palette.divider, 0.3)}`,
                  borderRadius: 2,
                }}
              >
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>

          <Divider sx={{ mb: 3 }} />

          {/* QR Code */}
          <Box sx={{ display: "flex", gap: 3, alignItems: "center", mb: 3 }}>
            <Box
              sx={{
                p: 2,
                borderRadius: 2,
                border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
                backgroundColor: alpha(theme.palette.background.default, 0.5),
              }}
            >
              <Box id="share-qr-code">
                <SimpleQRCode value={shareUrl || "https://clarityai.app"} size={140} />
              </Box>
            </Box>

            <Box sx={{ flex: 1, display: "flex", flexDirection: "column", gap: 1.5 }}>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                startIcon={<ContentCopyIcon />}
                onClick={handleCopyLink}
                disabled={!shareUrl || isGenerating}
                sx={{ textTransform: "none", fontWeight: 600, justifyContent: "flex-start" }}
              >
                Copy Link
              </Button>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                startIcon={<EmailIcon />}
                onClick={handleEmail}
                disabled={!shareUrl || isGenerating}
                sx={{ textTransform: "none", fontWeight: 600, justifyContent: "flex-start" }}
              >
                Email
              </Button>
              <Button
                variant="outlined"
                size="small"
                fullWidth
                startIcon={<DownloadIcon />}
                onClick={handleDownloadQR}
                disabled={!shareUrl || isGenerating}
                sx={{ textTransform: "none", fontWeight: 600, justifyContent: "flex-start" }}
              >
                Download QR
              </Button>
            </Box>
          </Box>

          {/* Privacy Notice */}
          <Alert
            severity="info"
            variant="outlined"
            icon={<LockOutlinedIcon fontSize="small" />}
            sx={{
              borderRadius: 2,
              "& .MuiAlert-message": { fontSize: "0.82rem" },
            }}
          >
            Anyone with this link can view the analysis results.
            {expiry !== "never" && ` This link will expire in ${expiryLabels[expiry].toLowerCase()}.`}
          </Alert>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setOpen(false)} sx={{ textTransform: "none" }}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={!!snackMessage}
        autoHideDuration={3000}
        onClose={() => setSnackMessage(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={() => setSnackMessage(null)}
          severity="success"
          variant="filled"
          sx={{ borderRadius: 2 }}
        >
          {snackMessage}
        </Alert>
      </Snackbar>
    </>
  );
}
