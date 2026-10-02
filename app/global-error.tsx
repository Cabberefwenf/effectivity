"use client";

/** Last resort when the root layout itself fails. Uses no tokens or fonts: nothing else is loaded. */
export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: "2rem" }}>
        <h1>Something went wrong</h1>
        <p>The page failed to load. Nothing you pasted was stored.</p>
        <button type="button" onClick={reset}>
          Try again
        </button>
      </body>
    </html>
  );
}
