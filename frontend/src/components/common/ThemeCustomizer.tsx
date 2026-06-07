import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Drawer,
  Typography,
  Slider,
  Radio,
  RadioGroup,
  FormControlLabel,
  ToggleButton,
  ToggleButtonGroup,
  Divider,
  IconButton,
  Button,
  Switch,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import PaletteIcon from "@mui/icons-material/Palette";
import RestoreIcon from "@mui/icons-material/Restore";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ThemePreset {
  id: string;
  name: string;
  primary: string;
  secondary: string;
  gradient: string;
}

interface ThemePreferences {
  colorScheme: string;
  fontSize: "small" | "medium" | "large";
  borderRadius: number; // 0 = sharp, 16 = rounded, 24 = pill
  animationsEnabled: boolean;
}

interface ThemeCustomizerProps {
  open: boolean;
  onClose: () => void;
  onPreferencesChange?: (prefs: ThemePreferences) => void;
}

// ---------------------------------------------------------------------------
// Color presets
// ---------------------------------------------------------------------------

const COLOR_PRESETS: ThemePreset[] = [
  {
    id: "default-purple",
    name: "Default Purple",
    primary: "#7c3aed",
    secondary: "#06b6d4",
    gradient: "linear-gradient(135deg, #7c3aed, #06b6d4)",
  },
  {
    id: "ocean-blue",
    name: "Ocean Blue",
    primary: "#2563eb",
    secondary: "#0ea5e9",
    gradient: "linear-gradient(135deg, #2563eb, #0ea5e9)",
  },
  {
    id: "forest-green",
    name: "Forest Green",
    primary: "#059669",
    secondary: "#10b981",
    gradient: "linear-gradient(135deg, #059669, #10b981)",
  },
  {
    id: "sunset-orange",
    name: "Sunset Orange",
    primary: "#ea580c",
    secondary: "#f59e0b",
    gradient: "linear-gradient(135deg, #ea580c, #f59e0b)",
  },
  {
    id: "monochrome",
    name: "Monochrome",
    primary: "#525252",
    secondary: "#737373",
    gradient: "linear-gradient(135deg, #525252, #737373)",
  },
];

const FONT_SIZE_MAP: Record<string, number> = {
  small: 13,
  medium: 14,
  large: 16,
};

const BORDER_RADIUS_MARKS = [
  { value: 0, label: "Sharp" },
  { value: 12, label: "Rounded" },
  { value: 24, label: "Pill" },
];

const STORAGE_KEY = "clarityai-theme-preferences";

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------

function loadPreferences(): ThemePreferences {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored) as ThemePreferences;
    }
  } catch {
    // Ignore parse errors
  }
  return {
    colorScheme: "default-purple",
    fontSize: "medium",
    borderRadius: 12,
    animationsEnabled: true,
  };
}

function savePreferences(prefs: ThemePreferences) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Ignore storage errors
  }
}

// ---------------------------------------------------------------------------
// Apply to document
// ---------------------------------------------------------------------------

function applyPreferences(prefs: ThemePreferences) {
  const root = document.documentElement;

  // Font size
  root.style.fontSize = `${FONT_SIZE_MAP[prefs.fontSize] || 14}px`;

  // Border radius CSS variable
  root.style.setProperty("--clarity-border-radius", `${prefs.borderRadius}px`);

  // Color scheme CSS variables
  const preset = COLOR_PRESETS.find((p) => p.id === prefs.colorScheme) || COLOR_PRESETS[0];
  root.style.setProperty("--clarity-primary", preset.primary);
  root.style.setProperty("--clarity-secondary", preset.secondary);
  root.style.setProperty("--clarity-gradient", preset.gradient);

  // Animations
  if (!prefs.animationsEnabled) {
    root.style.setProperty("--clarity-animation-duration", "0s");
    root.classList.add("reduce-motion");
  } else {
    root.style.removeProperty("--clarity-animation-duration");
    root.classList.remove("reduce-motion");
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ThemeCustomizer({
  open,
  onClose,
  onPreferencesChange,
}: ThemeCustomizerProps) {
  const [prefs, setPrefs] = useState<ThemePreferences>(loadPreferences);

  // Apply on mount and whenever prefs change
  useEffect(() => {
    applyPreferences(prefs);
    savePreferences(prefs);
    onPreferencesChange?.(prefs);
  }, [prefs, onPreferencesChange]);

  const updatePref = useCallback(
    <K extends keyof ThemePreferences>(key: K, value: ThemePreferences[K]) => {
      setPrefs((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const resetDefaults = () => {
    const defaults: ThemePreferences = {
      colorScheme: "default-purple",
      fontSize: "medium",
      borderRadius: 12,
      animationsEnabled: true,
    };
    setPrefs(defaults);
  };

  const activePreset = COLOR_PRESETS.find((p) => p.id === prefs.colorScheme) || COLOR_PRESETS[0];

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        "& .MuiDrawer-paper": {
          width: 340,
          p: 0,
        },
      }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            p: 2.5,
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <PaletteIcon color="primary" />
            <Typography variant="h6" fontWeight={700}>
              Theme
            </Typography>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: "auto", px: 2.5, py: 2 }}>
          {/* Color Scheme */}
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5 }}>
            Color Scheme
          </Typography>
          <RadioGroup
            value={prefs.colorScheme}
            onChange={(e) => updatePref("colorScheme", e.target.value)}
          >
            {COLOR_PRESETS.map((preset) => (
              <FormControlLabel
                key={preset.id}
                value={preset.id}
                control={<Radio size="small" />}
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Box
                      sx={{
                        width: 24,
                        height: 24,
                        borderRadius: 1,
                        background: preset.gradient,
                        border: preset.id === prefs.colorScheme ? "2px solid" : "none",
                        borderColor: "primary.main",
                      }}
                    />
                    <Typography variant="body2">{preset.name}</Typography>
                  </Box>
                }
                sx={{ mb: 0.5 }}
              />
            ))}
          </RadioGroup>

          {/* Preview swatch */}
          <Box
            sx={{
              mt: 1,
              mb: 3,
              height: 40,
              borderRadius: `${prefs.borderRadius}px`,
              background: activePreset.gradient,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Typography variant="caption" sx={{ color: "#fff", fontWeight: 600 }}>
              Preview
            </Typography>
          </Box>

          <Divider sx={{ mb: 2.5 }} />

          {/* Font Size */}
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5 }}>
            Font Size
          </Typography>
          <ToggleButtonGroup
            value={prefs.fontSize}
            exclusive
            onChange={(_, val) => {
              if (val) updatePref("fontSize", val);
            }}
            fullWidth
            size="small"
            sx={{ mb: 3 }}
          >
            <ToggleButton value="small">
              <Typography variant="caption">Small</Typography>
            </ToggleButton>
            <ToggleButton value="medium">
              <Typography variant="body2">Medium</Typography>
            </ToggleButton>
            <ToggleButton value="large">
              <Typography variant="body1">Large</Typography>
            </ToggleButton>
          </ToggleButtonGroup>

          <Divider sx={{ mb: 2.5 }} />

          {/* Border Radius */}
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5 }}>
            Border Radius
          </Typography>
          <Box sx={{ px: 1, mb: 1 }}>
            <Slider
              value={prefs.borderRadius}
              onChange={(_, val) => updatePref("borderRadius", val as number)}
              min={0}
              max={24}
              step={1}
              marks={BORDER_RADIUS_MARKS}
              valueLabelDisplay="auto"
              valueLabelFormat={(v) => `${v}px`}
              sx={{
                "& .MuiSlider-markLabel": {
                  fontSize: "0.7rem",
                },
              }}
            />
          </Box>

          {/* Radius preview */}
          <Box sx={{ display: "flex", gap: 1.5, mb: 3, justifyContent: "center" }}>
            <Box
              sx={{
                width: 48,
                height: 32,
                borderRadius: `${prefs.borderRadius}px`,
                border: 2,
                borderColor: "primary.main",
              }}
            />
            <Box
              sx={{
                width: 48,
                height: 32,
                borderRadius: `${prefs.borderRadius}px`,
                backgroundColor: "primary.main",
              }}
            />
            <Box
              sx={{
                width: 80,
                height: 32,
                borderRadius: `${prefs.borderRadius}px`,
                background: activePreset.gradient,
              }}
            />
          </Box>

          <Divider sx={{ mb: 2.5 }} />

          {/* Animations */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 1,
            }}
          >
            <Typography variant="subtitle2" fontWeight={600}>
              Animations
            </Typography>
            <Switch
              checked={prefs.animationsEnabled}
              onChange={(e) => updatePref("animationsEnabled", e.target.checked)}
              size="small"
            />
          </Box>
          <Typography variant="caption" color="text.secondary">
            Disable for reduced motion. Turns off all transitions and animations.
          </Typography>
        </Box>

        {/* Footer */}
        <Box sx={{ p: 2.5, borderTop: 1, borderColor: "divider" }}>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<RestoreIcon />}
            onClick={resetDefaults}
            size="small"
          >
            Reset to Defaults
          </Button>
        </Box>
      </Box>
    </Drawer>
  );
}
