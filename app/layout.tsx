import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Source_Serif_4 } from "next/font/google";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { SyntheticBanner } from "@/components/SyntheticBanner";
import { SITE, isIndexable, siteOrigin } from "@/lib/site";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});
const serif = Source_Serif_4({
  subsets: ["latin"],
  weight: ["600"],
  variable: "--font-serif",
  display: "swap",
});

const TITLE = "effectivity: as-built effectivity resolver";

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin()),
  title: { default: TITLE, template: "%s | effectivity" },
  description: SITE.description,
  applicationName: SITE.name,
  alternates: { canonical: "/" },
  robots: isIndexable() ? { index: true, follow: true } : { index: false, follow: false },
  openGraph: {
    type: "website",
    siteName: SITE.name,
    title: TITLE,
    description: SITE.description,
    url: "/",
  },
  twitter: { card: "summary_large_image", title: TITLE, description: SITE.description },
};

export const viewport: Viewport = {
  themeColor: "#0b0c0e",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable} ${serif.variable}`}>
      <body>
        <a href="#main" className="skip">
          Skip to content
        </a>
        <SyntheticBanner />
        <SiteHeader />
        <main id="main" tabIndex={-1} className="shell pt-12 outline-none">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
