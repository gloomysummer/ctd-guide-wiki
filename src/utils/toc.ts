import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

export interface TocHeading {
  depth: number;
  slug: string;
  text: string;
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

export function extractTocFromAstroUrl(metaUrl: string): TocHeading[] {
  try {
    const filePath = fileURLToPath(metaUrl);
    if (!fs.existsSync(filePath)) return [];
    const content = fs.readFileSync(filePath, 'utf-8');
    const body = content.replace(/^---[\s\S]*?---/, '');
    
    const headings: TocHeading[] = [];
    const regex = /<(h[23])(?:\s+[^>]*?id=["']([^"']+)["'])?[^>]*>(.*?)<\/\1>/gis;
    let match;
    while ((match = regex.exec(body)) !== null) {
      const tag = match[1].toLowerCase();
      const id = match[2];
      const rawText = match[3];
      const text = rawText.replace(/<[^>]+>/g, '').trim();
      if (!text) continue;
      if (text.includes('ON THIS PAGE') || text.includes('EXPLORE THE WIKI') || text.includes('Table of Contents')) continue;
      const slug = id || slugify(text);
      headings.push({
        depth: tag === 'h2' ? 2 : 3,
        slug,
        text,
      });
    }
    return headings;
  } catch (err) {
    console.warn('[extractTocFromAstroUrl] Failed:', err);
    return [];
  }
}
