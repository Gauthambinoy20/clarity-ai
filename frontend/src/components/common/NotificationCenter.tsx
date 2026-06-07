import { useEffect, useCallback } from "react";
import {
  Badge,
  IconButton,
  Popover,
  Box,
  Typography,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from "@mui/material";
import NotificationsOutlinedIcon from "@mui/icons-material/NotificationsOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { useState, useRef } from "react";
import { useAppStore } from "@/stores/appStore";

const typeIcons = {
  success: <CheckCircleOutlineIcon sx={{ color: "#22c55e", fontSize: 20 }} />,
  info: <InfoOutlinedIcon sx={{ color: "#3b82f6", fontSize: 20 }} />,
  warning: <WarningAmberOutlinedIcon sx={{ color: "#f59e0b", fontSize: 20 }} />,
  error: <ErrorOutlineIcon sx={{ color: "#ef4444", fontSize: 20 }} />,
};

const AUTO_DISMISS_MS = 30000;

export default function NotificationCenter() {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const timerRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const { notifications, removeNotification, clearNotifications, markNotificationRead } =
    useAppStore();

  const unreadCount = notifications.filter((n) => !n.read).length;
  const open = Boolean(anchorEl);

  // Auto-dismiss after 30 seconds
  useEffect(() => {
    const currentTimers = timerRef.current;
    notifications.forEach((notif) => {
      if (!currentTimers.has(notif.id)) {
        const timeLeft = AUTO_DISMISS_MS - (Date.now() - notif.timestamp);
        if (timeLeft <= 0) {
          removeNotification(notif.id);
        } else {
          const timer = setTimeout(() => {
            removeNotification(notif.id);
            currentTimers.delete(notif.id);
          }, timeLeft);
          currentTimers.set(notif.id, timer);
        }
      }
    });

    // Clean up timers for removed notifications
    currentTimers.forEach((_timer, id) => {
      if (!notifications.find((n) => n.id === id)) {
        clearTimeout(currentTimers.get(id));
        currentTimers.delete(id);
      }
    });

    return () => {
      currentTimers.forEach((timer) => clearTimeout(timer));
    };
  }, [notifications, removeNotification]);

  const handleOpen = useCallback(
    (event: React.MouseEvent<HTMLElement>) => {
      setAnchorEl(event.currentTarget);
      // Mark all as read on open
      notifications.forEach((n) => {
        if (!n.read) markNotificationRead(n.id);
      });
    },
    [notifications, markNotificationRead]
  );

  const handleClose = useCallback(() => {
    setAnchorEl(null);
  }, []);

  const formatTime = (timestamp: number) => {
    const diff = Math.floor((Date.now() - timestamp) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(timestamp).toLocaleDateString();
  };

  return (
    <>
      <IconButton color="inherit" onClick={handleOpen}>
        <Badge
          badgeContent={unreadCount}
          color="error"
          max={99}
          sx={{
            "& .MuiBadge-badge": {
              fontSize: "0.65rem",
              minWidth: 18,
              height: 18,
            },
          }}
        >
          <NotificationsOutlinedIcon />
        </Badge>
      </IconButton>

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              width: 380,
              maxHeight: 480,
              borderRadius: 3,
              mt: 1,
            },
          },
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            p: 2,
            pb: 1,
          }}
        >
          <Typography variant="subtitle1" fontWeight={600}>
            Notifications
          </Typography>
          {notifications.length > 0 && (
            <Button
              size="small"
              startIcon={<DeleteOutlineIcon sx={{ fontSize: 16 }} />}
              onClick={clearNotifications}
              sx={{ textTransform: "none", fontSize: "0.75rem" }}
            >
              Clear all
            </Button>
          )}
        </Box>
        <Divider />

        {notifications.length === 0 ? (
          <Box sx={{ p: 4, textAlign: "center" }}>
            <NotificationsOutlinedIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              No notifications yet
            </Typography>
          </Box>
        ) : (
          <List dense sx={{ maxHeight: 380, overflow: "auto", py: 0 }}>
            {notifications.map((notif, i) => (
              <ListItem
                key={notif.id}
                divider={i < notifications.length - 1}
                sx={{
                  py: 1.5,
                  px: 2,
                  opacity: notif.read ? 0.7 : 1,
                  "&:hover": { backgroundColor: "action.hover" },
                }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {typeIcons[notif.type]}
                </ListItemIcon>
                <ListItemText
                  primary={notif.message}
                  secondary={formatTime(notif.timestamp)}
                  primaryTypographyProps={{
                    variant: "body2",
                    fontWeight: notif.read ? 400 : 600,
                  }}
                  secondaryTypographyProps={{
                    variant: "caption",
                  }}
                />
              </ListItem>
            ))}
          </List>
        )}
      </Popover>
    </>
  );
}
