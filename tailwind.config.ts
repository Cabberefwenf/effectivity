import type { Config } from "tailwindcss";

/**
 * Colors are CSS variables (app/globals.css) so every hue is written once, as a token.
 * Radius is near zero by design. The type ramp has a floor: nothing below `meta`.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "ui-serif", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        bg: "rgb(var(--bg) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        elevated: "rgb(var(--elevated) / <alpha-value>)",
        inset: "rgb(var(--inset) / <alpha-value>)",
        ink: "rgb(var(--ink) / <alpha-value>)",
        "ink-2": "rgb(var(--ink-2) / <alpha-value>)",
        "ink-3": "rgb(var(--ink-3) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        rule: "rgb(var(--rule) / <alpha-value>)",
        "rule-strong": "rgb(var(--rule-strong) / <alpha-value>)",
        engineering: "rgb(var(--engineering) / <alpha-value>)",
        "engineering-fill": "rgb(var(--engineering-fill) / <alpha-value>)",
        "engineering-soft": "rgb(var(--engineering-soft) / <alpha-value>)",
        governing: "rgb(var(--governing) / <alpha-value>)",
        "governing-soft": "rgb(var(--governing-soft) / <alpha-value>)",
        conflict: "rgb(var(--conflict) / <alpha-value>)",
        "conflict-soft": "rgb(var(--conflict-soft) / <alpha-value>)",
        unresolved: "rgb(var(--unresolved) / <alpha-value>)",
        "unresolved-soft": "rgb(var(--unresolved-soft) / <alpha-value>)",
        human: "rgb(var(--human) / <alpha-value>)",
        "human-soft": "rgb(var(--human-soft) / <alpha-value>)",
      },
      fontSize: {
        meta: ["0.8125rem", { lineHeight: "1.45" }],
        small: ["0.9375rem", { lineHeight: "1.5" }],
        body: ["1.0625rem", { lineHeight: "1.6" }],
        lede: ["1.25rem", { lineHeight: "1.5" }],
        subsection: ["clamp(1.125rem, 1.3vw, 1.3125rem)", { lineHeight: "1.3" }],
        section: ["clamp(1.5rem, 2vw, 1.875rem)", { lineHeight: "1.15" }],
        statement: ["clamp(2.25rem, 4.2vw, 3.75rem)", { lineHeight: "1.04" }],
      },
      borderRadius: { none: "0", sm: "1px", DEFAULT: "2px", md: "3px" },
      maxWidth: { prose: "68ch", tight: "58ch" },
    },
  },
  plugins: [],
};

export default config;
