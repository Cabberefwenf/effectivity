import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

/* Raw hex is allowed here only (see scripts/check-tokens.mjs): image output has no CSS variables. */
export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0b0c0e",
        color: "#4a9fd8",
        fontSize: 24,
        fontWeight: 700,
      }}
    >
      e
    </div>,
    size,
  );
}
