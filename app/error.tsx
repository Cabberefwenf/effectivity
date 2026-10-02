"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="max-w-prose" role="alert">
      <p className="kicker">Error</p>
      <h1 className="mt-2 font-serif text-statement font-semibold">Something went wrong</h1>
      <p className="mt-5 text-lede text-ink-2">
        The page failed to render. Nothing you pasted was stored. Try again.
      </p>
      <p className="mt-6">
        <button type="button" className="btn btn-primary" onClick={reset}>
          Try again
        </button>
      </p>
    </div>
  );
}
