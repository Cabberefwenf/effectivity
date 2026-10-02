import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./", import.meta.url)) },
  },
  esbuild: { jsx: "automatic" },
  test: {
    globals: true,
    environment: "node",
    include: [
      "lib/**/*.test.ts",
      "components/**/*.test.ts",
      "app/**/*.test.ts",
      "scripts/**/*.test.ts",
    ],
  },
});
