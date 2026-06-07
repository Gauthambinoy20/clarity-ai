import { Box, Typography } from "@mui/material";
import { motion } from "framer-motion";
import BatchProcessor from "@/components/advanced/BatchProcessor";

export default function BatchPage() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight={800} gutterBottom>
          Batch Processing
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload multiple files or paste multiple texts to analyze them all at once.
        </Typography>
      </Box>

      <BatchProcessor />
    </motion.div>
  );
}
