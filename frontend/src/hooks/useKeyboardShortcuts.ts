import { useEffect, useCallback, useRef } from "react";

interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  handler: () => void;
  description?: string;
}

export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  const shortcutsRef = useRef(shortcuts);
  shortcutsRef.current = shortcuts;

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    for (const shortcut of shortcutsRef.current) {
      const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey;
      const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
      const altMatch = shortcut.alt ? event.altKey : !event.altKey;
      const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();

      if (ctrlMatch && shiftMatch && altMatch && keyMatch) {
        event.preventDefault();
        event.stopPropagation();
        shortcut.handler();
        return;
      }
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);
}

export const SHORTCUT_DEFINITIONS = [
  { keys: "Ctrl + Enter", description: "Submit / Analyze" },
  { keys: "Ctrl + Shift + D", description: "Go to AI Detection" },
  { keys: "Ctrl + Shift + H", description: "Go to Humanize" },
  { keys: "Ctrl + Shift + P", description: "Go to Plagiarism" },
  { keys: "Ctrl + Shift + A", description: "Go to Analytics" },
  { keys: "Ctrl + Shift + C", description: "Go to Compare" },
  { keys: "Ctrl + E", description: "Export results" },
  { keys: "Ctrl + /", description: "Show keyboard shortcuts" },
];
