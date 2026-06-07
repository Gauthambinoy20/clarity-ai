import { createTheme, type ThemeOptions } from "@mui/material/styles";

const commonComponents: ThemeOptions["components"] = {
  MuiButton: {
    styleOverrides: {
      root: {
        borderRadius: 12,
        textTransform: "none" as const,
        fontWeight: 600,
        padding: "10px 24px",
      },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: 16,
        backgroundImage: "none",
      },
    },
  },
  MuiTextField: {
    styleOverrides: {
      root: {
        "& .MuiOutlinedInput-root": {
          borderRadius: 12,
        },
      },
    },
  },
  MuiChip: {
    styleOverrides: {
      root: {
        borderRadius: 8,
        fontWeight: 500,
      },
    },
  },
  MuiTab: {
    styleOverrides: {
      root: {
        textTransform: "none" as const,
        fontWeight: 600,
      },
    },
  },
};

const commonTypography: ThemeOptions["typography"] = {
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  h1: { fontWeight: 800, letterSpacing: "-0.02em" },
  h2: { fontWeight: 700, letterSpacing: "-0.01em" },
  h3: { fontWeight: 700, letterSpacing: "-0.01em" },
  h4: { fontWeight: 600 },
  h5: { fontWeight: 600 },
  h6: { fontWeight: 600 },
  button: { fontWeight: 600 },
};

const palette = {
  primary: { main: "#7c3aed", light: "#a78bfa", dark: "#5b21b6" },
  secondary: { main: "#06b6d4", light: "#22d3ee", dark: "#0891b2" },
  success: { main: "#22c55e", light: "#4ade80", dark: "#16a34a" },
  error: { main: "#ef4444", light: "#f87171", dark: "#dc2626" },
  warning: { main: "#f59e0b", light: "#fbbf24", dark: "#d97706" },
};

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    ...palette,
    background: {
      default: "#09090b",
      paper: "#18181b",
    },
    text: {
      primary: "#fafafa",
      secondary: "#a1a1aa",
    },
    divider: "#27272a",
  },
  typography: commonTypography,
  components: {
    ...commonComponents,
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          backgroundImage: "none",
          border: "1px solid #27272a",
          backgroundColor: "#18181b",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: "#18181b",
          borderRight: "1px solid #27272a",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "#09090b",
          borderBottom: "1px solid #27272a",
          backgroundImage: "none",
        },
      },
    },
  },
  shape: { borderRadius: 12 },
});

export const lightTheme = createTheme({
  palette: {
    mode: "light",
    ...palette,
    background: {
      default: "#fafafa",
      paper: "#ffffff",
    },
    text: {
      primary: "#18181b",
      secondary: "#71717a",
    },
    divider: "#e4e4e7",
  },
  typography: commonTypography,
  components: {
    ...commonComponents,
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          backgroundImage: "none",
          border: "1px solid #e4e4e7",
          backgroundColor: "#ffffff",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: "#ffffff",
          borderRight: "1px solid #e4e4e7",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "#ffffff",
          borderBottom: "1px solid #e4e4e7",
          backgroundImage: "none",
          color: "#18181b",
        },
      },
    },
  },
  shape: { borderRadius: 12 },
});
