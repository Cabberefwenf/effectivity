import type { State } from "@/lib/states";

/** One distinct shape per state, so status survives without colour. Decorative: the word is always beside it. */
export function StateGlyph({ state, size = 16 }: { state: State; size?: number }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    "aria-hidden": true,
    focusable: false,
  } as const;
  switch (state) {
    case "out_of_effectivity":
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="6" strokeDasharray="2 2" />
          <path d="M5 8h6" />
        </svg>
      );
    case "not_yet_reached":
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="6" />
        </svg>
      );
    case "incorporable":
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="6" />
          <path d="M5.2 8.2l2 2 3.6-4" />
        </svg>
      );
    case "late":
      return (
        <svg {...common}>
          <path d="M8 2.2l6.2 11H1.8z" />
          <path d="M8 6.5v3.2M8 11.5v.2" />
        </svg>
      );
    case "blocked_material":
      return (
        <svg {...common}>
          <rect x="2.5" y="2.5" width="11" height="11" />
          <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" />
        </svg>
      );
    case "incorporated":
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="6" fill="currentColor" fillOpacity="0.22" />
          <path d="M5.2 8.2l2 2 3.6-4" />
        </svg>
      );
  }
}
