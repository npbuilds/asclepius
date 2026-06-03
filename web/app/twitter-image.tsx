/**
 * Twitter card image — Next.js convention. Re-exports the same image
 * generator as opengraph-image.tsx so social previews are consistent
 * across LinkedIn (OG) and Twitter (X) without maintaining two layouts.
 *
 * Twitter actually accepts 1200×630 (the OG default); the only place
 * the aspect ratio matters is in the rendered card-style preview, where
 * the wider-than-tall layout reads as a "summary_large_image" card.
 */

export {
  alt,
  size,
  contentType,
  default,
} from "./opengraph-image";
