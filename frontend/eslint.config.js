// Flat config for the React + TypeScript app. The old .eslintrc.json
// referenced plugins that were never installed, so linting silently
// didn't exist; this is the real, pinned toolchain CI runs.
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";

export default tseslint.config(
  { ignores: ["dist", "coverage", "node_modules"] },
  {
    files: ["src/**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      // empty catch blocks must at least say why
      "no-empty": ["error", { allowEmptyCatch: false }],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  {
    // tests run in jsdom with vitest globals and looser ergonomics
    files: ["src/__tests__/**/*.{ts,tsx}", "src/test-setup.ts"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "react-refresh/only-export-components": "off",
    },
  },
  {
    // app entry point legitimately exports nothing
    files: ["src/main.tsx"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  }
);
