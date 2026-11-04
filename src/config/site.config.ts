// ============================================================
// [Config 层] site.config.ts — 站点唯一真相源
//
// 起一个新站时，这是你唯一必须改的代码文件。
// 上游模板升级只会动 Code 层，与本文件的冲突是预期内的、
// 且永远保留你自己的值（见 docs/CONTENT-LAYERS.md）。
//
// 规则：所有派生值（JSON-LD、canonical、hreflang、sitemap、
// 收录提交）都从这里读，禁止在页面里硬编码域名。
// ============================================================

export const siteConfig = {
  /** 游戏官方名（用于 title/keywords/JSON-LD） */
  gameName: "Cameraman Tower Defense",
  /** 站点品牌名（og:site_name、页脚、品牌后缀） */
  siteName: "CTD Guide",
  /** 站点根 URL，结尾不带斜杠 */
  siteUrl: "https://ctd-guide.wiki",
  /** 品牌后缀（SERP title 用，严格 ≤12 字符，含 | 与空格） */
  titleSuffix: " | CTD Guide",
  /** 站点默认语言（URL 无前缀）；其余语言加前缀，缺失内容回退默认语言 */
  defaultLocale: "en",
  /** 实际存在翻译内容的语言（双轨 hreflang：只为物理存在的翻译输出 alternate） */
  locales: ["en"],
  /** 站长联系邮箱（法律合规三件套用） */
  contactEmail: "contact@ctd-guide.wiki",
  /** 广告与统计（全部默认关闭——env/config 门控，模板升级不会自动开启） */
  ads: {
    adsenseClient: "", // 例: "ca-pub-XXXXXXXXXXXXXXXX"，留空 = 不渲染广告位
    gaMeasurementId: "G-ZRY3W8SP89", // 例: "G-XXXXXXXXXX"，留空 = 不加载 GA4
  },
  /**
   * Adsterra 变现（可选，默认关闭）。2026-10-14 对标 invokyr.wiki 补入模板。
   *
   * 形状很重要：AdSlot.astro 读 siteConfig.adsterra.banners[zone].key，
   * 并校验它必须是 **32 位小写 hex**，否则整槽不渲染（占位符防御）。
   * 每个尺寸一个独立 Zone —— Adsterra 对同页同 Key 只计一次展示。
   *
   * 启用步骤：
   *   1. enabled 置 true
   *   2. 逐尺寸填真实 key（各站不同，不要跨站复制）
   *   3. 在 public/ads/banner-<zone>.html 放对应的自托管 iframe 壳
   *
   * 版式约束：成对渲染 728x90(className="ad-slot-wide") + 320x50(className="ad-slot-narrow")，
   * 由 global.css 的 .ad-slot-footer 编排块做「桌面宽幅 / 移动窄幅」二选一。
   * 漏掉那段 CSS 会导致两个横幅位**同时显示**（模板 2026-10-14 前的缺陷，已修）。
   */
  adsterra: {
    enabled: false,
    banners: {
      // host 是后台「Get code」里 <script src="..."> 的域名，不同 Zone 可能不同
      // （highrevenueformat.com / highperformanceformat.com）。留空则用脚本默认值，
      // 但**复制代码时请照抄后台给的域名**，猜错会静默不出广告。
      "banner-160x300": { key: "", host: "", width: 160, height: 300, enabled: true },
      "banner-160x600": { key: "", host: "", width: 160, height: 600, enabled: true },
      "banner-300x250": { key: "", host: "", width: 300, height: 250, enabled: true },
      "banner-320x50": { key: "", host: "", width: 320, height: 50, enabled: true },
      "banner-468x60": { key: "", host: "", width: 468, height: 60, enabled: true },
      "banner-728x90": { key: "", host: "", width: 728, height: 90, enabled: true },
    },
  },
  /** 搜索引擎站长验权 */
  verification: {
    googleSiteVerification: "RKqtXXpl8uXjIw7CY9fMjrJZdxX4LS6MeCgb9xRE9Zo", // 例: "3FCItOu1MEWiIz0Sq0o5Ur35-nj1jsxEmmn6ds3-LXc"，留空 = 不输出 meta
  },
  /** 收录提交（可选） */
  indexing: {
    indexNowKey: "b50fa05d32bd4d87a1436376190a9632", // 留空 = 不生成 key 文件
  },
  /** 官方社区与实体链接（用于 Schema.org Organization sameAs 知识图谱绑定，留空不输出） */
  officialLinks: {
    steam: "", // 例: "https://store.steampowered.com/app/xxxxxx"
    discord: "https://www.roblox.com/groups/1111394813/Aligators-Games", // Aligators Games Group
    twitter: "", // 例: "https://twitter.com/xxxxxx"
    youtube: "https://www.youtube.com/watch?v=7QBiS599euI", // Verified Valuation Reference
    officialSite: "https://www.roblox.com/games/132929771812494/Cameraman-Tower-Defense", // Roblox Experience
  },
} as const;

export type SiteConfig = typeof siteConfig;
