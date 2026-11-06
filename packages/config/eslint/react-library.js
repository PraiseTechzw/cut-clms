// ESLint preset for React component libraries (e.g. @cut-clms/ui).
// TypeScript footing from base, plus React Hooks rules. Prettier wins on style.
import reactHooks from "eslint-plugin-react-hooks";
import base from "./base.js";

export default [
  ...base,
  reactHooks.configs.flat.recommended,
  {
    languageOptions: {
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
  },
];
