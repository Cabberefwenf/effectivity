import type { MetadataRoute } from "next";
import { siteOrigin } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const origin = siteOrigin();
  return ["/", "/rules", "/about"].map((path) => ({ url: `${origin}${path}` }));
}
