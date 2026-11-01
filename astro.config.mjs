import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

import cloudflare from "@astrojs/cloudflare";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function buildLastmodMap() {
  const dates = new Map();

  // 1. Guides content
  const guidesDir = path.resolve(__dirname, 'src/content/guides');
  let latestGuideDate = null;
  if (fs.existsSync(guidesDir)) {
    for (const f of fs.readdirSync(guidesDir)) {
      if (!f.endsWith('.md')) continue;
      const content = fs.readFileSync(path.join(guidesDir, f), 'utf-8');
      const slug = f.replace(/\.md$/, '');
      const m = content.match(/updated:\s*['"]?([^'\n\r"]+)/) || content.match(/pubDate:\s*['"]?([^'\n\r"]+)/);
      if (m) {
        const d = new Date(m[1].trim());
        dates.set(`/guide/${slug}/`, d);
        if (!latestGuideDate || d > latestGuideDate) {
          latestGuideDate = d;
        }
      }
    }
  }

  // 2. Codes content
  const codesDir = path.resolve(__dirname, 'src/content/codes');
  let latestCodeDate = null;
  if (fs.existsSync(codesDir)) {
    for (const f of fs.readdirSync(codesDir)) {
      if (!f.endsWith('.md')) continue;
      const content = fs.readFileSync(path.join(codesDir, f), 'utf-8');
      const slug = f.replace(/\.md$/, '');
      const m = content.match(/updated:\s*['"]?([^'\n\r"]+)/) || content.match(/pubDate:\s*['"]?([^'\n\r"]+)/);
      if (m) {
        const d = new Date(m[1].trim());
        dates.set(`/codes/${slug}/`, d);
        if (!latestCodeDate || d > latestCodeDate) {
          latestCodeDate = d;
        }
      }
    }
  }

  // 3. Collection index & homepage aggregate dates
  if (latestCodeDate) {
    dates.set('/codes/', latestCodeDate);
  }
  if (latestGuideDate) {
    dates.set('/guide/', latestGuideDate);
    dates.set('/', latestGuideDate);
  }

  // 4. Static standalone pages
  const staticPages = [
    { route: '/', file: 'src/pages/index.astro' },
    { route: '/values/', file: 'src/pages/values/index.astro' },
    { route: '/codes/', file: 'src/pages/codes/index.astro' },
    { route: '/units/', file: 'src/pages/units/index.astro' },
    { route: '/tier-list/', file: 'src/pages/tier-list/index.astro' },
    { route: '/how-to-solo-nightmare-mode/', file: 'src/pages/how-to-solo-nightmare-mode/index.astro' },
    { route: '/discord/', file: 'src/pages/discord/index.astro' },
    { route: '/shop/', file: 'src/pages/shop/index.astro' },
    { route: '/about/', file: 'src/pages/about/index.astro' },
    { route: '/contact/', file: 'src/pages/contact/index.astro' },
    { route: '/privacy-policy/', file: 'src/pages/privacy-policy/index.astro' },
  ];
  for (const { route, file } of staticPages) {
    const fullPath = path.resolve(__dirname, file);
    if (fs.existsSync(fullPath)) {
      dates.set(route, fs.statSync(fullPath).mtime);
    }
  }

  return dates;
}

const lastmodMap = buildLastmodMap();

export default defineConfig({
  // apply-template 时自动替换为新域名
  site: 'https://ctd-guide.wiki',

  output: 'static',

  integrations: [
    sitemap({
      serialize(item) {
        try {
          const urlObj = new URL(item.url);
          let pathname = urlObj.pathname;
          if (!pathname.endsWith('/')) {
            pathname += '/';
          }
          const modDate = lastmodMap.get(pathname);
          if (modDate) {
            item.lastmod = modDate.toISOString();
          }
        } catch {
          // Keep existing item if URL parsing fails
        }
        return item;
      },
    }),
  ],

  adapter: cloudflare()
});