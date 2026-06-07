import { useCallback } from "react";
import { Box, Card, Typography } from "@mui/material";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined";
import { useDropzone } from "react-dropzone";
import { motion } from "framer-motion";

interface FileUploadProps {
  onFileContent: (text: string, filename: string) => void;
  disabled?: boolean;
}

export default function FileUpload({ onFileContent, disabled }: FileUploadProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = () => {
        const content = reader.result as string;
        onFileContent(content, file.name);
      };
      reader.readAsText(file);
    },
    [onFileContent]
  );

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } =
    useDropzone({
      onDrop,
      accept: {
        "text/plain": [".txt"],
        "application/pdf": [".pdf"],
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
          [".docx"],
      },
      maxFiles: 1,
      disabled,
    });

  return (
    <Card
      {...getRootProps()}
      component={motion.div}
      whileHover={disabled ? {} : { scale: 1.01 }}
      whileTap={disabled ? {} : { scale: 0.99 }}
      sx={{
        p: 4,
        textAlign: "center",
        cursor: disabled ? "default" : "pointer",
        border: "2px dashed",
        borderColor: isDragActive ? "primary.main" : "divider",
        backgroundColor: isDragActive ? "primary.main" : "transparent",
        opacity: disabled ? 0.5 : 1,
        transition: "all 0.2s ease",
        "&:hover": disabled
          ? {}
          : {
              borderColor: "primary.light",
            },
      }}
    >
      <input {...getInputProps()} />

      {acceptedFiles.length > 0 ? (
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 1 }}>
          <InsertDriveFileOutlinedIcon color="primary" />
          <Typography variant="body2" fontWeight={500}>
            {acceptedFiles[0].name}
          </Typography>
        </Box>
      ) : (
        <>
          <CloudUploadOutlinedIcon
            sx={{ fontSize: 48, color: "text.secondary", mb: 1 }}
          />
          <Typography variant="body1" fontWeight={500} gutterBottom>
            {isDragActive ? "Drop file here" : "Drag & drop a file"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Supports PDF, DOCX, TXT
          </Typography>
        </>
      )}
    </Card>
  );
}
