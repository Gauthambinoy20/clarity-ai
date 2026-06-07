import { useState } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import {
  AppBar,
  Box,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  useMediaQuery,
  useTheme,
  Chip,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import ContentPasteSearchOutlinedIcon from "@mui/icons-material/ContentPasteSearchOutlined";
import AutoFixHighOutlinedIcon from "@mui/icons-material/AutoFixHighOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import AnalyticsOutlinedIcon from "@mui/icons-material/AnalyticsOutlined";
import CompareArrowsOutlinedIcon from "@mui/icons-material/CompareArrowsOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import BatchPredictionOutlinedIcon from "@mui/icons-material/BatchPredictionOutlined";
import { AnimatePresence } from "framer-motion";
import { useAppStore } from "@/stores/appStore";

import DetectPage from "@/pages/DetectPage";
import PlagiarismPage from "@/pages/PlagiarismPage";
import HumanizePage from "@/pages/HumanizePage";
import HistoryPage from "@/pages/HistoryPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import ComparePage from "@/pages/ComparePage";
import DashboardPage from "@/pages/DashboardPage";
import BatchPage from "@/pages/BatchPage";
import FloatingActionMenu from "@/components/common/FloatingActionMenu";
import NotificationCenter from "@/components/common/NotificationCenter";

const DRAWER_WIDTH = 260;

const navItems = [
  {
    label: "Dashboard",
    path: "/dashboard",
    icon: <DashboardOutlinedIcon />,
  },
  {
    label: "AI Detection",
    path: "/",
    icon: <SearchOutlinedIcon />,
  },
  {
    label: "Plagiarism",
    path: "/plagiarism",
    icon: <ContentPasteSearchOutlinedIcon />,
  },
  {
    label: "Humanize",
    path: "/humanize",
    icon: <AutoFixHighOutlinedIcon />,
  },
  {
    label: "Analytics",
    path: "/analytics",
    icon: <AnalyticsOutlinedIcon />,
  },
  {
    label: "Compare",
    path: "/compare",
    icon: <CompareArrowsOutlinedIcon />,
  },
  {
    label: "Batch",
    path: "/batch",
    icon: <BatchPredictionOutlinedIcon />,
  },
  {
    label: "History",
    path: "/history",
    icon: <HistoryOutlinedIcon />,
  },
];

export default function App() {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const { themeMode, toggleTheme, drawerOpen, setDrawerOpen } = useAppStore();

  const drawerContent = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Box sx={{ p: 2.5, display: "flex", alignItems: "center", gap: 1.5 }}>
        <Box
          sx={{
            width: 36,
            height: 36,
            borderRadius: 2,
            background: "linear-gradient(135deg, #7c3aed, #06b6d4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography variant="h6" fontWeight={800} sx={{ color: "#fff", fontSize: 18 }}>
            C
          </Typography>
        </Box>
        <Box>
          <Typography variant="h6" fontWeight={700} sx={{ lineHeight: 1.2 }}>
            ClarityAI
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Content Analysis
          </Typography>
        </Box>
      </Box>
      <Divider />
      <List sx={{ flex: 1, px: 1.5, pt: 2 }}>
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={() => {
                  navigate(item.path);
                  if (isMobile) setDrawerOpen(false);
                }}
                sx={{
                  borderRadius: 2,
                  backgroundColor: isActive
                    ? "primary.main"
                    : "transparent",
                  color: isActive ? "#fff" : "text.primary",
                  "&:hover": {
                    backgroundColor: isActive
                      ? "primary.dark"
                      : "action.hover",
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: isActive ? "#fff" : "text.secondary",
                    minWidth: 40,
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontWeight: isActive ? 600 : 400 }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
      <Divider />
      <Box sx={{ p: 2, textAlign: "center" }}>
        <Chip
          label="v1.0.0"
          size="small"
          variant="outlined"
          sx={{ fontSize: "0.7rem" }}
        />
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      {/* Sidebar */}
      {isMobile ? (
        <Drawer
          variant="temporary"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          sx={{
            "& .MuiDrawer-paper": { width: DRAWER_WIDTH },
          }}
        >
          {drawerContent}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            "& .MuiDrawer-paper": { width: DRAWER_WIDTH },
          }}
        >
          {drawerContent}
        </Drawer>
      )}

      {/* Main content */}
      <Box
        sx={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
        }}
      >
        <AppBar
          position="sticky"
          elevation={0}
          sx={{
            ml: isMobile ? 0 : `${DRAWER_WIDTH}px`,
            width: isMobile ? "100%" : `calc(100% - ${DRAWER_WIDTH}px)`,
          }}
        >
          <Toolbar>
            {isMobile && (
              <IconButton
                edge="start"
                onClick={() => setDrawerOpen(true)}
                sx={{ mr: 1 }}
              >
                <MenuIcon />
              </IconButton>
            )}
            <Box sx={{ flex: 1 }} />
            <NotificationCenter />
            <IconButton onClick={toggleTheme} color="inherit">
              {themeMode === "dark" ? (
                <Brightness7Icon />
              ) : (
                <Brightness4Icon />
              )}
            </IconButton>
          </Toolbar>
        </AppBar>

        <Box
          component="main"
          sx={{
            flex: 1,
            p: { xs: 2, sm: 3, md: 4 },
            overflow: "auto",
          }}
        >
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<DetectPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/plagiarism" element={<PlagiarismPage />} />
              <Route path="/humanize" element={<HumanizePage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/compare" element={<ComparePage />} />
              <Route path="/batch" element={<BatchPage />} />
              <Route path="/history" element={<HistoryPage />} />
            </Routes>
          </AnimatePresence>
        </Box>

        <FloatingActionMenu />
      </Box>
    </Box>
  );
}
