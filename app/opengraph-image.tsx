import { ImageResponse } from "next/og";

export const alt = "effectivity: an as-built effectivity resolver";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/* Raw hex is allowed here only (see scripts/check-tokens.mjs): image output has no CSS variables. */
export default function OpenGraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: "#0b0c0e",
        color: "#f2f3f5",
        padding: 72,
      }}
    >
      <div style={{ fontSize: 34, color: "#4a9fd8", display: "flex" }}>effectivity</div>
      <div style={{ fontSize: 68, lineHeight: 1.08, display: "flex", maxWidth: 980 }}>
        Which units does this change reach, and where does each one stand?
      </div>
      <div style={{ fontSize: 28, color: "#c7cbd3", display: "flex" }}>
        Six states. A reason code and rule ids for every decision. Synthetic data only.
      </div>
    </div>,
    size,
  );
}
