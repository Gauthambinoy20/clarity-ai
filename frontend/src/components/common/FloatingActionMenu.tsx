import { useNavigate } from "react-router-dom";
import { SpeedDial, SpeedDialAction, SpeedDialIcon } from "@mui/material";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import ContentPasteSearchOutlinedIcon from "@mui/icons-material/ContentPasteSearchOutlined";
import AutoFixHighOutlinedIcon from "@mui/icons-material/AutoFixHighOutlined";
import AnalyticsOutlinedIcon from "@mui/icons-material/AnalyticsOutlined";
import CompareArrowsOutlinedIcon from "@mui/icons-material/CompareArrowsOutlined";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

const actions = [
  {
    icon: <SearchOutlinedIcon />,
    name: "New Detection",
    path: "/",
  },
  {
    icon: <ContentPasteSearchOutlinedIcon />,
    name: "New Plagiarism Check",
    path: "/plagiarism",
  },
  {
    icon: <AutoFixHighOutlinedIcon />,
    name: "Humanize Text",
    path: "/humanize",
  },
  {
    icon: <AnalyticsOutlinedIcon />,
    name: "Quick Analytics",
    path: "/analytics",
  },
  {
    icon: <CompareArrowsOutlinedIcon />,
    name: "Compare Texts",
    path: "/compare",
  },
];

export default function FloatingActionMenu() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.5, type: "spring", stiffness: 260, damping: 20 }}
        style={{
          position: "fixed",
          bottom: 24,
          right: 24,
          zIndex: 1200,
        }}
      >
        <SpeedDial
          ariaLabel="Quick actions"
          icon={<SpeedDialIcon />}
          open={open}
          onOpen={() => setOpen(true)}
          onClose={() => setOpen(false)}
          direction="up"
          FabProps={{
            sx: {
              background: "linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%)",
              "&:hover": {
                background: "linear-gradient(135deg, #6d28d9 0%, #0891b2 100%)",
              },
            },
          }}
        >
          {actions.map((action) => (
            <SpeedDialAction
              key={action.name}
              icon={action.icon}
              tooltipTitle={action.name}
              tooltipOpen
              onClick={() => {
                navigate(action.path);
                setOpen(false);
              }}
              FabProps={{
                sx: {
                  backgroundColor: "background.paper",
                  "&:hover": {
                    backgroundColor: "action.hover",
                  },
                },
              }}
            />
          ))}
        </SpeedDial>
      </motion.div>
    </AnimatePresence>
  );
}
