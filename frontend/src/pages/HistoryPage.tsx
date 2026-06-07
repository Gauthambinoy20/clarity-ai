import { useState, useEffect, useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  Chip,
  InputAdornment,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { getHistory } from "@/utils/api";

function getLabelColor(label: string): "success" | "error" | "warning" | "default" {
  switch (label.toLowerCase()) {
    case "human":
      return "success";
    case "ai":
      return "error";
    case "mixed":
      return "warning";
    default:
      return "default";
  }
}

function getTypeColor(type: string): string {
  switch (type) {
    case "detection":
      return "#7c3aed";
    case "plagiarism":
      return "#06b6d4";
    case "humanization":
      return "#22c55e";
    default:
      return "#a1a1aa";
  }
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["history", page + 1, rowsPerPage],
    queryFn: () => getHistory(page + 1, rowsPerPage),
  });

  const filteredItems = useMemo(() => {
    if (!data?.items) return [];
    let items = data.items;

    if (typeFilter !== "all") {
      items = items.filter((item) => item.type === typeFilter);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter((item) =>
        item.textPreview.toLowerCase().includes(q)
      );
    }

    return items;
  }, [data, search, typeFilter]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Box sx={{ maxWidth: 1200, mx: "auto" }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Analysis History
          </Typography>
          <Typography variant="body1" color="text.secondary">
            View and manage your past analyses.
          </Typography>
        </Box>

        {/* Filters */}
        <Card sx={{ mb: 3 }}>
          <CardContent
            sx={{
              display: "flex",
              gap: 2,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <TextField
              placeholder="Search text..."
              size="small"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              sx={{ minWidth: 280 }}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
              }}
            />
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Type</InputLabel>
              <Select
                value={typeFilter}
                label="Type"
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="detection">Detection</MenuItem>
                <MenuItem value="plagiarism">Plagiarism</MenuItem>
                <MenuItem value="humanization">Humanization</MenuItem>
              </Select>
            </FormControl>
          </CardContent>
        </Card>

        {/* Table */}
        <Card>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Type</TableCell>
                  <TableCell>Text Preview</TableCell>
                  <TableCell align="center">Score</TableCell>
                  <TableCell align="center">Label</TableCell>
                  <TableCell align="right">Date</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 6 }}>
                      <Typography color="text.secondary">Loading...</Typography>
                    </TableCell>
                  </TableRow>
                ) : filteredItems.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 6 }}>
                      <Typography color="text.secondary">
                        No analyses found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredItems.map((item, index) => (
                    <motion.tr
                      key={item.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                      style={{ display: "table-row" }}
                    >
                      <TableCell>
                        <Chip
                          label={item.type}
                          size="small"
                          sx={{
                            backgroundColor: `${getTypeColor(item.type)}20`,
                            color: getTypeColor(item.type),
                            fontWeight: 600,
                            fontSize: "0.75rem",
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{
                            maxWidth: 400,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {item.textPreview}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" fontWeight={700}>
                          {Math.round(item.score)}%
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={item.label}
                          size="small"
                          color={getLabelColor(item.label)}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="text.secondary">
                          {new Date(item.createdAt).toLocaleDateString()}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="View details">
                          <IconButton
                            size="small"
                            onClick={() => {
                              if (item.type === "detection") navigate("/");
                              else if (item.type === "plagiarism")
                                navigate("/plagiarism");
                              else navigate("/humanize");
                            }}
                          >
                            <VisibilityOutlinedIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </motion.tr>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
          {data && (
            <TablePagination
              component="div"
              count={data.total}
              page={page}
              onPageChange={(_, p) => setPage(p)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(parseInt(e.target.value, 10));
                setPage(0);
              }}
              rowsPerPageOptions={[10, 20, 50]}
            />
          )}
        </Card>
      </Box>
    </motion.div>
  );
}
