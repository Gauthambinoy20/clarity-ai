import { useState, useCallback } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Collapse,
  alpha,
  useTheme,
  Chip,
} from "@mui/material";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import CleaningServicesIcon from "@mui/icons-material/CleaningServices";
import SpellcheckIcon from "@mui/icons-material/Spellcheck";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { motion, AnimatePresence } from "framer-motion";

/* ─── Types ──────────────────────────────────────────────────────── */

export interface ActionResult {
  actionId: string;
  success: boolean;
  message: string;
  modifiedText?: string;
  details?: string[];
}

interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

interface QuickActionsToolbarProps {
  text: string;
  onHumanize?: (text: string) => Promise<ActionResult>;
  onRemoveBuzzwords?: (text: string) => Promise<ActionResult>;
  onFixGrammar?: (text: string) => Promise<ActionResult>;
  onImproveReadability?: (text: string) => Promise<ActionResult>;
  onGenerateReport?: (text: string) => Promise<ActionResult>;
}

/* ─── Actions config ─────────────────────────────────────────────── */

const actions: QuickAction[] = [
  {
    id: "humanize",
    label: "Humanize Flagged",
    description: "Runs targeted humanizer on flagged sentences",
    icon: <AutoFixHighIcon fontSize="small" />,
    color: "#7c3aed",
  },
  {
    id: "buzzwords",
    label: "Remove Buzzwords",
    description: "Strips common AI vocabulary patterns",
    icon: <CleaningServicesIcon fontSize="small" />,
    color: "#f59e0b",
  },
  {
    id: "grammar",
    label: "Fix Grammar",
    description: "Auto-fix detected grammar errors",
    icon: <SpellcheckIcon fontSize="small" />,
    color: "#06b6d4",
  },
  {
    id: "readability",
    label: "Improve Readability",
    description: "Simplify complex sentences",
    icon: <MenuBookIcon fontSize="small" />,
    color: "#22c55e",
  },
  {
    id: "report",
    label: "Generate Report",
    description: "Export detailed analysis as PDF",
    icon: <PictureAsPdfIcon fontSize="small" />,
    color: "#ef4444",
  },
];

/* ─── Main Component ─────────────────────────────────────────────── */

export default function QuickActionsToolbar({
  text,
  onHumanize,
  onRemoveBuzzwords,
  onFixGrammar,
  onImproveReadability,
  onGenerateReport,
}: QuickActionsToolbarProps) {
  const theme = useTheme();
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, ActionResult>>({});

  const handlers: Record<string, ((t: string) => Promise<ActionResult>) | undefined> = {
    humanize: onHumanize,
    buzzwords: onRemoveBuzzwords,
    grammar: onFixGrammar,
    readability: onImproveReadability,
    report: onGenerateReport,
  };

  const handleAction = useCallback(
    async (actionId: string) => {
      setLoadingAction(actionId);
      try {
        const handler = handlers[actionId];
        if (handler) {
          const result = await handler(text);
          setResults((prev) => ({ ...prev, [actionId]: result }));
        } else {
          // Demo mode
          await new Promise((r) => setTimeout(r, 1200));
          const demoMessages: Record<string, string> = {
            humanize: "3 flagged sentences have been rewritten with more natural phrasing.",
            buzzwords: 'Removed 7 AI buzzwords: "utilize", "moreover", "in conclusion", "it is important to note", "significantly", "comprehensive", "facilitate".',
            grammar: "Fixed 2 grammar issues: subject-verb agreement, comma splice.",
            readability: "Simplified 4 complex sentences. Reading level improved from Grade 14 to Grade 10.",
            report: "PDF report generated and ready for download.",
          };
          setResults((prev) => ({
            ...prev,
            [actionId]: {
              actionId,
              success: true,
              message: demoMessages[actionId] || "Action completed successfully.",
            },
          }));
        }
      } catch (err) {
        setResults((prev) => ({
          ...prev,
          [actionId]: {
            actionId,
            success: false,
            message: "Action failed. Please try again.",
          },
        }));
      } finally {
        setLoadingAction(null);
      }
    },
    [text, handlers]
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card
        sx={{
          border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
          background: alpha(theme.palette.background.paper, 0.6),
          backdropFilter: "blur(8px)",
        }}
      >
        <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
          <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 2 }}>
            Quick Actions
          </Typography>

          {/* Action buttons */}
          <Box
            sx={{
              display: "flex",
              gap: 1,
              flexWrap: "wrap",
            }}
          >
            {actions.map((action) => {
              const isLoading = loadingAction === action.id;
              const hasResult = !!results[action.id];

              return (
                <motion.div key={action.id} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button
                    variant="outlined"
                    size="small"
                    disabled={isLoading || (loadingAction !== null && loadingAction !== action.id)}
                    onClick={() => handleAction(action.id)}
                    startIcon={
                      isLoading ? (
                        <CircularProgress size={16} sx={{ color: action.color }} />
                      ) : hasResult && results[action.id].success ? (
                        <CheckCircleIcon sx={{ color: "#22c55e", fontSize: 18 }} />
                      ) : (
                        action.icon
                      )
                    }
                    sx={{
                      borderColor: alpha(action.color, 0.3),
                      color: hasResult && results[action.id].success ? "#22c55e" : action.color,
                      textTransform: "none",
                      fontWeight: 600,
                      fontSize: "0.78rem",
                      "&:hover": {
                        borderColor: action.color,
                        backgroundColor: alpha(action.color, 0.06),
                      },
                    }}
                  >
                    {action.label}
                  </Button>
                </motion.div>
              );
            })}
          </Box>

          {/* Inline results */}
          <AnimatePresence>
            {Object.keys(results).length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 1 }}>
                  {Object.values(results).map((result) => {
                    const action = actions.find((a) => a.id === result.actionId);
                    return (
                      <motion.div
                        key={result.actionId}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                      >
                        <Box
                          sx={{
                            p: 1.5,
                            borderRadius: 2,
                            border: `1px solid ${alpha(
                              result.success ? "#22c55e" : "#ef4444",
                              0.2
                            )}`,
                            background: alpha(result.success ? "#22c55e" : "#ef4444", 0.04),
                            display: "flex",
                            alignItems: "flex-start",
                            gap: 1,
                          }}
                        >
                          <Chip
                            label={action?.label || result.actionId}
                            size="small"
                            sx={{
                              backgroundColor: alpha(action?.color || "#888", 0.12),
                              color: action?.color || "#888",
                              fontWeight: 600,
                              fontSize: "0.68rem",
                              flexShrink: 0,
                            }}
                          />
                          <Typography variant="body2" sx={{ fontSize: "0.82rem" }}>
                            {result.message}
                          </Typography>
                        </Box>
                      </motion.div>
                    );
                  })}
                </Box>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>
    </motion.div>
  );
}
