import type { MetadataRoute } from "next";
import { siteOrigin } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const origin = siteOrigin();
  return ["/", "/rules", "/packaging", "/dashboard", "/about"].map((path) => ({
    url: `${origin}${path}`,
  }));
}
