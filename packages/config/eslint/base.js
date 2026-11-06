// Shared flat ESLint footing for all CUT-CLMS TypeScript workspaces.
// Composed per-package by react-library.js (UI libs) and next.js (Next.js apps).
import eslintJs from "@eslint/js";
import tseslint from "typescript-eslint";
import prettierConfig from "eslint-config-prettier/flat";

export default [
  {
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "**/out/**",
      "**/dist/**",
      "**/coverage/**",
      "**/.turbo/**",
      "**/.venv/**",
      "**/next-env.d.ts",
      "**/next.config.ts",
    ],
  },
  eslintJs.configs.recommended,
  ...tseslint.configs.recommended,
  prettierConfig,
];
