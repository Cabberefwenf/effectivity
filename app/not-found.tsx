import Link from "next/link";

export default function NotFound() {
  return (
    <div className="max-w-prose">
      <p className="kicker">404</p>
      <h1 className="mt-2 font-serif text-statement font-semibold">That page does not exist</h1>
      <p className="mt-5 text-lede text-ink-2">
        The resolver, the rules and the limits are linked in the header.
      </p>
      <p className="mt-6">
        <Link href="/" className="btn btn-primary">
          Back to the resolver
        </Link>
      </p>
    </div>
  );
}
