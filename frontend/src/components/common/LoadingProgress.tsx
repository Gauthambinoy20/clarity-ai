import { useState, useEffect } from "react";
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Typography,
  LinearProgress,
} from "@mui/material";
import { motion, AnimatePresence } from "framer-motion";

const steps = [
  { label: "Analyzing perplexity...", description: "Measuring text predictability" },
  { label: "Computing burstiness...", description: "Evaluating variation patterns" },
  { label: "Running classifiers...", description: "Multi-model ensemble analysis" },
  { label: "GLTR token analysis...", description: "Token probability distribution" },
  { label: "Sentence-level scoring...", description: "Per-sentence AI probability" },
  { label: "Compiling results...", description: "Aggregating all signals" },
];

interface LoadingProgressProps {
  isLoading: boolean;
}

export default function LoadingProgress({ isLoading }: LoadingProgressProps) {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      setActiveStep(0);
      return;
    }

    const interval = setInterval(() => {
      setActiveStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 1800);

    return () => clearInterval(interval);
  }, [isLoading]);

  if (!isLoading) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.4 }}
      >
        <Box sx={{ width: "100%", py: 4 }}>
          <Box sx={{ mb: 3 }}>
            <LinearProgress
              variant="indeterminate"
              sx={{
                height: 4,
                borderRadius: 2,
                backgroundColor: "divider",
                "& .MuiLinearProgress-bar": {
                  background: "linear-gradient(90deg, #7c3aed, #06b6d4)",
                  borderRadius: 2,
                },
              }}
            />
          </Box>

          <Stepper activeStep={activeStep} orientation="vertical">
            {steps.map((step, index) => (
              <Step key={step.label} completed={index < activeStep}>
                <StepLabel
                  StepIconProps={{
                    sx: {
                      "&.Mui-active": { color: "primary.main" },
                      "&.Mui-completed": { color: "success.main" },
                    },
                  }}
                >
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{
                      opacity: index <= activeStep ? 1 : 0.4,
                      x: 0,
                    }}
                    transition={{ delay: index * 0.1, duration: 0.3 }}
                  >
                    <Typography
                      variant="body1"
                      fontWeight={index === activeStep ? 600 : 400}
                      color={index <= activeStep ? "text.primary" : "text.secondary"}
                    >
                      {step.label}
                    </Typography>
                    {index === activeStep && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          {step.description}
                        </Typography>
                      </motion.div>
                    )}
                  </motion.div>
                </StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>
      </motion.div>
    </AnimatePresence>
  );
}
