// ============================================================
// [Config 层] channels.ts — Cameraman Tower Defense 5 大意图频道架构
// 严格遵循建站工单要求：Values / Codes / Units / Tier List / Guides
// channels.ts 是唯一真相源，1:1 驱动顶栏 Mega Menu、移动抽屉、首页侧栏、详情页导览树、页脚
// ============================================================

export interface ChannelGuide {
  id: string;
  title: string;
  url: string;
  description?: string;
  tag?: string;
}

export interface Channel {
  id: string;
  title: string;
  shortTitle: string;
  url: string;
  color: string;
  guides: ChannelGuide[];
}

export const CHANNELS: Channel[] = [
  {
    id: "values",
    title: "Unit Trading Values & Calculator",
    shortTitle: "Values",
    url: "/values/",
    color: "#38bdf8",
    guides: [
      {
        id: "trading-values-calculator",
        title: "CTD Trading Values & Trade Calculator",
        url: "/values/",
        description: "Real-time Win/Fair/Lose trade calculator and authoritative unit pricing benchmark.",
        tag: "P0 TOOL"
      }
    ]
  },
  {
    id: "codes",
    title: "Codes & Free Rewards Ledger",
    shortTitle: "Codes",
    url: "/codes/",
    color: "#10b981",
    guides: [
      {
        id: "active-promo-codes",
        title: "Active Cameraman Tower Defense Codes (November 2026)",
        url: "/codes/",
        description: "Verified working coin promo codes, instant one-click copy, and redemption unlock rules.",
        tag: "P0 CODES"
      }
    ]
  },
  {
    id: "units",
    title: "Units Database & Roster",
    shortTitle: "Units",
    url: "/units/",
    color: "#818cf8",
    guides: [
      {
        id: "all-units-index",
        title: "Complete 40 Units Roster & Index",
        url: "/units/",
        description: "Full index of all 40 Godly, Mythic, Legendary, Epic, Rare, and Basic units.",
        tag: "P1 ROSTER"
      },
      {
        id: "upgraded-titan-tv-man",
        title: "Upgraded Titan TV Man (UTTVM)",
        url: "/units/upgraded-titan-tv-man/",
        description: "Apex Godly titan holding 5,425 trade points with 30,000 advertised card DPS.",
        tag: "GODLY"
      },
      {
        id: "upgraded-titan-cameraman",
        title: "Upgraded Titan Cameraman (UTCM)",
        url: "/units/upgraded-titan-cameraman/",
        description: "S-Tier Godly unit stats, DPS scaling, summon pity benchmark, and best placements.",
        tag: "GODLY"
      },
      {
        id: "chaos-cameraman",
        title: "Chaos Cameraman",
        url: "/units/chaos-cameraman/",
        description: "Endgame Mythic carry with critical chain-strike attack mechanics.",
        tag: "MYTHIC"
      },
      {
        id: "executioner-tv-man",
        title: "Executioner TV Man",
        url: "/units/executioner-tv-man/",
        description: "Heavily buffed single-target executioner capable of melting Nightmare bosses.",
        tag: "BUFFED"
      }
    ]
  },
  {
    id: "tier-list",
    title: "Unit Tier List & Meta Rankings",
    shortTitle: "Tier List",
    url: "/tier-list/",
    color: "#f43f5e",
    guides: [
      {
        id: "meta-tier-list",
        title: "Cameraman Tower Defense Meta Tier List (Update 5)",
        url: "/tier-list/",
        description: "Complete S-to-D tier rankings across all 40 units based on DPS, cost, and Nightmare utility.",
        tag: "P1 META"
      }
    ]
  },
  {
    id: "guides",
    title: "Tactical Walkthroughs & Hubs",
    shortTitle: "Guides",
    url: "/how-to-solo-nightmare-mode/",
    color: "#f59e0b",
    guides: [
      {
        id: "how-to-solo-nightmare-mode",
        title: "How to Solo Nightmare Mode in Cameraman Tower Defense",
        url: "/how-to-solo-nightmare-mode/",
        description: "Step-by-step 50-wave solo strategy, early-game farming, and Desert map placements.",
        tag: "P1 GUIDE"
      },
      {
        id: "discord-hub",
        title: "Official Discord & Community Trading Hub",
        url: "/discord/",
        description: "Aligators Games official community coordinates, verification guides, and trade rules.",
        tag: "P2 HUB"
      },
      {
        id: "shop-economy-guide",
        title: "In-Game Shop, Crates & Economy Guide",
        url: "/shop/",
        description: "Coin summon crates, VIP gamepasses, gem economy, and free-to-play spending advice.",
        tag: "P2 HUB"
      }
    ]
  }
];

export const TOTAL_GUIDES_COUNT = CHANNELS.reduce((acc, ch) => acc + ch.guides.length, 0);

export function getChannelByGuideId(guideId: string): Channel {
  return CHANNELS.find((ch) => ch.guides.some((g) => g.id === guideId)) || CHANNELS[0];
}

/**
 * 按当前页面 URL 反查所属频道（DualSidebar / MobileToc 用）
 */
export function getChannelByGuideUrl(currentUrl: string): Channel {
  const norm = currentUrl.endsWith('/') ? currentUrl : `${currentUrl}/`;

  for (const ch of CHANNELS) {
    if (ch.guides.some((g) => g.url === norm)) return ch;
  }
  const prefixHits = CHANNELS
    .filter((ch) => ch.url !== '/' && norm.startsWith(ch.url))
    .sort((a, b) => b.url.length - a.url.length);
  return prefixHits[0] || CHANNELS[0];
}
