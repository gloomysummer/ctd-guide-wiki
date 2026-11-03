# CTD Guide — Cameraman Tower Defense Wiki

**Live site: [ctd-guide.wiki](https://ctd-guide.wiki)**

A data-sourced wiki for *Cameraman Tower Defense* on Roblox (Aligators Games): unit trade values, promo codes, tier rankings, and solo Nightmare-mode walkthroughs.

## What makes it different

Most Cameraman TD value lists copy each other without saying where the numbers came from. This site cites a dated source for every figure and marks what it does **not** know.

- **Trade values** come from a community value list dated **2026-10-25** (Vaulted Values X), with the price movement history for each unit.
- **Combat stats** come from in-game stat-card readings that two independent recordings agree on. Units with only a single-source reading are labelled as such. Units with no graded reading say "not published" instead of guessing.
- **Promo codes** carry a `sourceUrl` per code and are re-checked against the official Discord.

## Pages

| Path | Contents |
|---|---|
| [/values/](https://ctd-guide.wiki/values/) | Trade value table + 4-slot trade calculator |
| [/codes/](https://ctd-guide.wiki/codes/) | Active promo codes and the 3-win redemption gate |
| [/tier-list/](https://ctd-guide.wiki/tier-list/) | S-to-D meta rankings |
| [/units/](https://ctd-guide.wiki/units/) | 39-unit database with per-unit value history |
| [/how-to-solo-nightmare-mode/](https://ctd-guide.wiki/how-to-solo-nightmare-mode/) | 50-wave solo walkthrough |

## Sourcing policy

Every number on the site traces to one of:

1. A dated community value list (with the video/list ID recorded)
2. A stat-card reading reproduced by two independent recordings
3. The game's own Roblox page or the developer's announcements

If none of those exist, the page says so. There is no interpolation, no "approximately", and no filler.

## Stack

Astro 5 static site, Cloudflare Pages. Built from the `game-wiki-template` three-layer layout (code / config / content) so upstream template upgrades merge cleanly.

```bash
npm install
NODE_OPTIONS="" npm run build   # NODE_OPTIONS must be cleared: the local safe-delete shim blocks astro
npm run check:links
```

## Feedback

Corrections welcome — open an issue with the unit name and the source that contradicts us.
