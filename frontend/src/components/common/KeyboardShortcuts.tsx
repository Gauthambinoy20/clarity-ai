import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Typography,
  Chip,
  IconButton,
  Divider,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import KeyboardOutlinedIcon from "@mui/icons-material/KeyboardOutlined";
import {
  useKeyboardShortcuts,
  SHORTCUT_DEFINITIONS,
} from "@/hooks/useKeyboardShortcuts";

interface KeyboardShortcutsProps {
  onAnalyze?: () => void;
  onExport?: () => void;
}

export default function KeyboardShortcuts({
  onAnalyze,
  onExport,
}: KeyboardShortcutsProps) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const navigate = useNavigate();

  useKeyboardShortcuts([
    {
      key: "Enter",
      ctrl: true,
      handler: () => onAnalyze?.(),
      description: "Submit / Analyze",
    },
    {
      key: "d",
      ctrl: true,
      shift: true,
      handler: () => navigate("/"),
      description: "Go to AI Detection",
    },
    {
      key: "h",
      ctrl: true,
      shift: true,
      handler: () => navigate("/humanize"),
      description: "Go to Humanize",
    },
    {
      key: "p",
      ctrl: true,
      shift: true,
      handler: () => navigate("/plagiarism"),
      description: "Go to Plagiarism",
    },
    {
      key: "a",
      ctrl: true,
      shift: true,
      handler: () => navigate("/analytics"),
      description: "Go to Analytics",
    },
    {
      key: "c",
      ctrl: true,
      shift: true,
      handler: () => navigate("/compare"),
      description: "Go to Compare",
    },
    {
      key: "e",
      ctrl: true,
      handler: () => onExport?.(),
      description: "Export results",
    },
    {
      key: "/",
      ctrl: true,
      handler: () => setDialogOpen((prev) => !prev),
      description: "Show keyboard shortcuts",
    },
  ]);

  return (
    <Dialog
      open={dialogOpen}
      onClose={() => setDialogOpen(false)}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: { sx: { borderRadius: 3 } },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          pb: 1,
        }}
      >
        <KeyboardOutlinedIcon color="primary" />
        <Typography variant="h6" fontWeight={600} sx={{ flex: 1 }}>
          Keyboard Shortcuts
        </Typography>
        <IconButton size="small" onClick={() => setDialogOpen(false)}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <Divider />
      <DialogContent sx={{ pt: 2 }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          {SHORTCUT_DEFINITIONS.map((shortcut) => (
            <Box
              key={shortcut.keys}
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                py: 0.75,
              }}
            >
              <Typography variant="body2" color="text.secondary">
                {shortcut.description}
              </Typography>
              <Box sx={{ display: "flex", gap: 0.5 }}>
                {shortcut.keys.split(" + ").map((key) => (
                  <Chip
                    key={key}
                    label={key}
                    size="small"
                    variant="outlined"
                    sx={{
                      fontFamily: "monospace",
                      fontWeight: 600,
                      fontSize: "0.75rem",
                      minWidth: 32,
                    }}
                  />
                ))}
              </Box>
            </Box>
          ))}
        </Box>
      </DialogContent>
    </Dialog>
  );
}
