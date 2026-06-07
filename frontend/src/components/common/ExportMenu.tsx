import { useState, useCallback } from "react";
import {
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Snackbar,
  Alert,
} from "@mui/material";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import DataObjectOutlinedIcon from "@mui/icons-material/DataObjectOutlined";
import TableChartOutlinedIcon from "@mui/icons-material/TableChartOutlined";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import ShareOutlinedIcon from "@mui/icons-material/ShareOutlined";
import { exportPdf, exportJson, exportCsv, getShareLink } from "@/utils/api";

interface ExportMenuProps {
  data: Record<string, unknown>;
  text: string;
  disabled?: boolean;
}

export default function ExportMenu({ data, text, disabled = false }: ExportMenuProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error";
  }>({ open: false, message: "", severity: "success" });

  const open = Boolean(anchorEl);

  const showToast = useCallback(
    (message: string, severity: "success" | "error" = "success") => {
      setSnackbar({ open: true, message, severity });
    },
    []
  );

  const handleExportPdf = useCallback(async () => {
    setAnchorEl(null);
    try {
      const blob = await exportPdf(data, text);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "clarityai-report.pdf";
      a.click();
      window.URL.revokeObjectURL(url);
      showToast("PDF exported successfully");
    } catch {
      showToast("Failed to export PDF", "error");
    }
  }, [data, text, showToast]);

  const handleExportJson = useCallback(async () => {
    setAnchorEl(null);
    try {
      const blob = await exportJson(data);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "clarityai-report.json";
      a.click();
      window.URL.revokeObjectURL(url);
      showToast("JSON exported successfully");
    } catch {
      showToast("Failed to export JSON", "error");
    }
  }, [data, showToast]);

  const handleExportCsv = useCallback(async () => {
    setAnchorEl(null);
    try {
      const blob = await exportCsv(data);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "clarityai-report.csv";
      a.click();
      window.URL.revokeObjectURL(url);
      showToast("CSV exported successfully");
    } catch {
      showToast("Failed to export CSV", "error");
    }
  }, [data, showToast]);

  const handleCopy = useCallback(async () => {
    setAnchorEl(null);
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      showToast("Copied to clipboard");
    } catch {
      showToast("Failed to copy", "error");
    }
  }, [data, showToast]);

  const handleShare = useCallback(async () => {
    setAnchorEl(null);
    try {
      const result = await getShareLink(data);
      await navigator.clipboard.writeText(result.url);
      showToast("Share link copied to clipboard");
    } catch {
      showToast("Failed to generate share link", "error");
    }
  }, [data, showToast]);

  return (
    <>
      <Button
        variant="outlined"
        startIcon={<FileDownloadOutlinedIcon />}
        onClick={(e) => setAnchorEl(e.currentTarget)}
        disabled={disabled}
        size="small"
      >
        Export
      </Button>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        slotProps={{
          paper: { sx: { minWidth: 200, borderRadius: 2, mt: 1 } },
        }}
      >
        <MenuItem onClick={handleExportPdf}>
          <ListItemIcon>
            <PictureAsPdfOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as PDF</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleExportJson}>
          <ListItemIcon>
            <DataObjectOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as JSON</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleExportCsv}>
          <ListItemIcon>
            <TableChartOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as CSV</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleCopy}>
          <ListItemIcon>
            <ContentCopyOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Copy to Clipboard</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleShare}>
          <ListItemIcon>
            <ShareOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Share Link</ListItemText>
        </MenuItem>
      </Menu>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ borderRadius: 2 }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
}
