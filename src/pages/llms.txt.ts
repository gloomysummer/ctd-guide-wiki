import type { APIRoute } from "astro";
import { siteConfig } from "../config/site.config";
import valuesData from "../data/values.json";
import codesData from "../data/verified-codes.json";
import unitStatsData from "../data/unit-stats.json";

// llms.txt is generated, never hand-written. The hand-written version rot into a
// liability: by 2026-11-10 it still described a different site's guide page and a
// September codes page, both of which returned 404, while listing none of the
// value, tier or unit pages that actually exist. Anything derived here comes off
// the same data the pages render, so it cannot drift from them.

const BASE = siteConfig.siteUrl;

const fmtDate = (iso: string) =>
  new Date(`${iso.slice(0, 10)}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });

export const GET: APIRoute = () => {
  const valuesDate = valuesData[0]?.source?.retrievedAt ?? "unknown";
  const codesDate = codesData.updatedAt.slice(0, 10);
  const activeCodes = codesData.activeCodes.filter((c) => c.status === "ACTIVE");

  const priced = valuesData
    .filter((u) => u.valueStatus === "published" && u.value > 0)
    .sort((a, b) => b.value - a.value);

  const topUnits = priced.slice(0, 12).map((u) => {
    const stats = unitStatsData.verified[u.id] ?? unitStatsData.singleSource[u.id] ?? null;
    const dps = stats?.maxDps ? `, ${stats.maxDps.toLocaleString("en-US")} max DPS` : "";
    return `- [${u.name}](${BASE}/units/${u.id}/): ${u.value.toLocaleString("en-US")} trade points${
      u.demand ? `, ${u.demand}/10 demand` : ""
    }, ${u.rarity}${dps}`;
  });

  const body = `# ${siteConfig.siteName}

> ${siteConfig.gameName} (Roblox) value list, trade calculator, codes and unit database. Trade values are community trade points between units, not developer gem prices. Every figure carries the list date it was read from; figures we could not source are marked as unknown rather than estimated.

Last synced: values ${fmtDate(valuesDate)} · codes ${fmtDate(codesDate)}.

## Core pages

- [CTD Values List & Trade Calculator](${BASE}/values/): ${priced.length} priced units with trade value, demand rating and price history, plus a Win/Fair/Lose trade parity calculator. Current list read ${fmtDate(valuesDate)}.
- [CTD Codes](${BASE}/codes/): ${activeCodes.length} active codes, last checked ${fmtDate(codesDate)}. Working: ${activeCodes
    .map((c) => c.code)
    .join(", ")}. Redemption requires 3 wins first.
- [CTD Tier List](${BASE}/tier-list/): units ranked S to C with the reasoning behind each placement.
- [Units Database](${BASE}/units/): all ${valuesData.length} units with base DPS, attack range, placement cost and crate drop source.
- [How to Solo Nightmare Mode](${BASE}/how-to-solo-nightmare-mode/): wave-by-wave solo strategy.

## Highest-value units right now

${topUnits.join("\n")}

## Facts worth quoting

- Game: ${siteConfig.gameName} by Aligators Games, on Roblox.
- Trade values are unit-for-unit trade points, taken from the Vaulted Values X community list; they are not Robux or gem prices.
- Current value list read ${fmtDate(valuesDate)}; the timeline benchmarks on each unit page come from the 25 October 2026 list.
- ${activeCodes.length} codes are live as of ${fmtDate(codesDate)}; codes are case sensitive and require 3 wins to redeem.

## Not on this site

- We do not publish gem prices, Robux prices or crate bundle pricing.
- We do not publish a stat figure we have not read off a card; where a stat is unverified the page says so instead of estimating.
`;

  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
};
