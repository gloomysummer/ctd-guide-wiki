#!/usr/bin/env python3
"""seo-channel-planner.py — 游戏攻略站 SEO 意图拓词与导航频道自动规划工具

功能：
1. 自动调用 Google Search Suggest / Autocomplete 接口采集玩家真实搜索长尾词。
2. 平台分流与意图聚类分析：
   - [Steam 平台]：5 大经典意图（Survival/Bosses/Weapons/Reference/Codes）。
   - [Roblox 平台]：8 大标准频道（Trello/Codes/Tier List/Values/Raids/Weapons/Systems/Updates）。
3. 实体防污染过滤器（--entities / 自动读取 dossier.json）：
   - 过滤同名泛词/非本作实体词（如动漫角色名、别家作品名），被滤词单独列出供人工复核。
4. 直接输出符合 src/config/channels.ts 规范的代码文件（--out）或终端预览。

用法:
    # 模式 A: 传统 Steam 游戏
    python3 scripts/seo-channel-planner.py --game "Dinoblade"
    
    # 模式 B: Roblox 抽卡/地牢游戏（带 8 频道与实体防污染）
    python3 scripts/seo-channel-planner.py --game "Anime Zero" --platform roblox --entities "Shadow Monarch,Void Arbiter,Flame Director"
    python3 scripts/seo-channel-planner.py --game "Anime Zero" --platform roblox --out src/config/channels.ts
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Steam 5 大核心意图模式
STEAM_INTENT_CLUSTERS = [
    {
        "id": "walkthrough",
        "shortTitle": "Survival",
        "titleTemplate": "Campaign & Survival",
        "color": "#22d3ee",
        "patterns": [
            r"beginner", r"guide", r"how to (?:play|heal|parry|start|survive)",
            r"walkthrough", r"tips", r"controls", r"combat", r"mechanics"
        ],
        "defaultGuides": [
            ("beginner-guide", "Beginner Combat & Starter Guide"),
            ("parry-and-posture-guide", "Parry Timing & Posture Breakdown"),
        ]
    },
    {
        "id": "bosses",
        "shortTitle": "Bosses",
        "titleTemplate": "Apex Bosses & Combat Gauntlet",
        "color": "#fb7185",
        "patterns": [
            r"boss", r"bosses", r"boss rush", r"how to beat", r"final boss",
            r"apex", r"encounter", r"locations?"
        ],
        "defaultGuides": [
            ("all-bosses-guide", "All Bosses in Order & Locations"),
            ("boss-rush-mode-guide", "Boss Rush Mode & Unlock Guide"),
        ]
    },
    {
        "id": "weapons",
        "shortTitle": "Weapons",
        "titleTemplate": "Weapons & Equipment Tier List",
        "color": "#c084fc",
        "patterns": [
            r"weapon", r"weapons", r"tier list", r"best (?:weapon|sword|build|stats|gear)",
            r"all weapons", r"arsenal", r"items?"
        ],
        "defaultGuides": [
            ("legendary-weapons-tier-list", "Legendary Weapons & Gear Tier List"),
            ("best-builds-guide", "Best Builds & Stat Optimization"),
        ]
    },
    {
        "id": "reference",
        "shortTitle": "Reference",
        "titleTemplate": "Achievements & System Specs",
        "color": "#f59e0b",
        "patterns": [
            r"specs?", r"requirements?", r"steam deck", r"achievements?", r"troph(?:y|ies)",
            r"save (?:file|location)", r"how long to (?:beat|complete)", r"respec", r"settings?"
        ],
        "defaultGuides": [
            ("pc-system-requirements", "PC System Specs & Steam Deck Guide"),
            ("all-achievements-guide", "100% Achievements & Trophy Guide"),
        ]
    },
    {
        "id": "codes",
        "shortTitle": "Codes",
        "titleTemplate": "Codes & Drops Entitlements",
        "color": "#34d399",
        "patterns": [
            r"codes?", r"redeem", r"drops?", r"promos?", r"free", r"rewards?",
            r"twitch drops", r"launch entitlements?"
        ],
        "defaultGuides": [
            ("promo-codes", "Active Promo Codes & Rewards Ledger"),
        ]
    },
]

# Roblox 8 大标准意图频道（突破词驱动）
ROBLOX_INTENT_CLUSTERS = [
    {
        "id": "trello",
        "shortTitle": "Trello",
        "titleTemplate": "Official Trello & Discord Hub",
        "urlPrefix": "/trello/",
        "color": "#38bdf8",
        "patterns": [r"trello", r"discord", r"official board", r"link"],
        "defaultGuides": [
            ("trello-board-guide", "Official Trello Board & Community Hub"),
        ]
    },
    {
        "id": "codes",
        "shortTitle": "Codes",
        "titleTemplate": "Codes & Free Rewards Ledger",
        "urlPrefix": "/codes/",
        "color": "#34d399",
        "patterns": [r"codes?", r"redeem", r"free rewards", r"expired codes"],
        "defaultGuides": [
            ("active-codes", "All Active Promo Codes & Free Spins"),
            ("expired-codes", "Expired Codes Archive"),
        ]
    },
    {
        "id": "tier-list",
        "shortTitle": "Tier List",
        "titleTemplate": "Tier Lists & Meta Rankings",
        "urlPrefix": "/tier-list/",
        "color": "#f43f5e",
        "patterns": [r"tier list", r"best", r"ranking", r"meta", r"traits tier", r"accessories tier"],
        "defaultGuides": [
            ("weapon-tier-list", "Best Weapons Meta Tier List"),
            ("traits-tier-list", "Best Traits Tier List"),
        ]
    },
    {
        "id": "values",
        "shortTitle": "Values",
        "titleTemplate": "Item & Weapon Trading Values",
        "urlPrefix": "/values/",
        "color": "#eab308",
        "patterns": [r"values?", r"value list", r"worth", r"trade", r"trading", r"price"],
        "defaultGuides": [
            ("weapon-values", "Weapon & Item Value List 2026"),
        ]
    },
    {
        "id": "raids",
        "shortTitle": "Raids",
        "titleTemplate": "Raids, Dungeons & Boss Gauntlets",
        "urlPrefix": "/raids/",
        "color": "#a855f7",
        "patterns": [r"raid", r"raids", r"shadow gate", r"spirited away", r"nightmare", r"red gate", r"dungeon"],
        "defaultGuides": [
            ("shadow-gate", "Shadow Gate Raid Guide & Rewards"),
            ("spirited-away", "Spirited Away Raid Strategy"),
        ]
    },
    {
        "id": "weapons",
        "shortTitle": "Weapons",
        "titleTemplate": "Weapons & Evolution Database",
        "urlPrefix": "/weapons/",
        "color": "#ec4899",
        "patterns": [r"weapon", r"weapons", r"evolution", r"evolve", r"shadow monarch", r"cataclysm", r"flame director"],
        "defaultGuides": [
            ("shadow-monarch", "Shadow Monarch Evolution & Stats"),
            ("all-weapons", "All Weapons Catalog"),
        ]
    },
    {
        "id": "guides",
        "shortTitle": "Systems",
        "titleTemplate": "Game Systems, Pity & Mechanics",
        "urlPrefix": "/guides/",
        "color": "#14b8a6",
        "patterns": [r"guide", r"how to", r"pity", r"skill tree", r"traits?", r"synerg(?:y|ies)", r"guilds?", r"milestones?", r"afk", r"beginner"],
        "defaultGuides": [
            ("pity-system-guide", "Gacha Pity System Breakdown"),
            ("skill-tree-guide", "Optimal Skill Tree Builds"),
        ]
    },
    {
        "id": "updates",
        "shortTitle": "Updates",
        "titleTemplate": "Patch Notes & Update History",
        "urlPrefix": "/updates/",
        "color": "#6366f1",
        "patterns": [r"update", r"patch notes", r"update log", r"leaks?", r"next update"],
        "defaultGuides": [
            ("update-log", "Latest Patch Notes & Update History"),
        ]
    },
]

# 通用泛词与别家动漫/游戏过滤否定词
GENERIC_POLLUTION_WORDS = {
    "zero two", "no tsukaima", "code geass", "hero", "to hero", "apex",
    "darling in the franxx", "tower defense", "isekai", "zero to"
}


def load_known_entities(game: str, manual_entities: str = "") -> set[str]:
    """获取游戏已知实体白名单（从参数或 dossier.json 中读取）"""
    entities = set()
    if manual_entities:
        for e in manual_entities.split(","):
            if e.strip():
                entities.add(e.strip().lower())

    # 尝试从 dossier.json 加载
    dossier_candidates = [
        REPO_ROOT / "dossier" / "dossier.json",
        REPO_ROOT / "src" / "data" / "dossier.json"
    ]
    for p in dossier_candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    # 读取 metadata / systems
                    if "metadata" in d and d["metadata"].get("name"):
                        entities.add(d["metadata"]["name"].lower())
                    if "systems" in d:
                        for rarity_group in d["systems"].get("rarity", []):
                            for item in rarity_group.get("unitsOrDrops", []):
                                entities.add(item.lower())
                    if "fandomData" in d and "entities" in d["fandomData"]:
                        for ent in d["fandomData"]["entities"]:
                            entities.add(ent.lower())
            except Exception:
                pass

    return entities


def fetch_google_suggestions(query: str) -> list[str]:
    """通过 Google Suggest 获取即时搜索词"""
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(query)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if len(data) >= 2 and isinstance(data[1], list):
                return data[1]
    except Exception:
        pass
    return []


def collect_seo_keywords(game: str, is_roblox: bool = False) -> list[str]:
    """多维度扫描并扩展目标游戏的搜索长尾词库"""
    print(f"🔍 正在从 Google 搜索引擎采集 [{game}] 的真实搜索意图...")
    if is_roblox:
        seed_patterns = [
            "codes", "trello", "tier list", "values", "raids",
            "weapons", "shadow gate", "pity", "evolution", "skill tree",
            "discord", "update", "how to", "best", "wiki", "roblox"
        ]
    else:
        seed_patterns = [
            "", "how to", "best", "guide", "boss", "bosses", "weapons",
            "codes", "tier list", "specs", "achievements", "steam deck",
            "all", "unlock", "location"
        ]
    
    unique_keywords = set()
    for pattern in seed_patterns:
        q = f"{game} {pattern}".strip()
        suggestions = fetch_google_suggestions(q)
        for s in suggestions:
            clean = s.strip().lower()
            if game.lower() in clean:
                unique_keywords.add(clean)

    for char in ["a", "b", "c", "h", "w", "s", "t"]:
        q = f"{game} {char}"
        for s in fetch_google_suggestions(q):
            clean = s.strip().lower()
            if game.lower() in clean:
                unique_keywords.add(clean)

    return sorted(unique_keywords)


def filter_keywords_by_entities(
    keywords: list[str],
    game: str,
    known_entities: set[str],
    is_roblox: bool = False
) -> tuple[list[str], list[str]]:
    """实体防污染过滤器：剔除与别家动漫/通用无关短语"""
    valid = []
    filtered = []
    game_lower = game.lower()

    CORE_ROBLOX_TERMS = {
        "codes", "trello", "tier list", "values", "raids", "weapons",
        "wiki", "guide", "discord", "roblox", "update", "how to", "best", "pity"
    }

    for kw in keywords:
        kw_clean = kw.lower().strip()
        # 1. 检查是否命中明确的负面污染词
        if any(bad in kw_clean for bad in GENERIC_POLLUTION_WORDS):
            filtered.append(kw)
            continue

        if not is_roblox:
            valid.append(kw)
            continue

        # 2. Roblox 模式：必须命中核心意图词 或 命中已知游戏实体
        rem = kw_clean.replace(game_lower, "").strip()
        has_core_term = any(term in rem for term in CORE_ROBLOX_TERMS)
        has_entity = any(ent in rem for ent in known_entities) if known_entities else False

        if has_core_term or has_entity:
            valid.append(kw)
        else:
            filtered.append(kw)

    return valid, filtered


def slugify(text: str) -> str:
    """生成标准化 URL Slug"""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")


def cluster_keywords(game: str, keywords: list[str], is_roblox: bool = False) -> dict:
    """将搜索词按目标意图频道聚类"""
    clusters_config = ROBLOX_INTENT_CLUSTERS if is_roblox else STEAM_INTENT_CLUSTERS
    clusters = {c["id"]: [] for c in clusters_config}
    game_lower = game.lower()

    for kw in keywords:
        intent_phrase = kw.replace(game_lower, "").strip()
        if not intent_phrase:
            continue

        matched = False
        for c in clusters_config:
            for pat in c["patterns"]:
                if re.search(pat, intent_phrase, re.IGNORECASE):
                    clusters[c["id"]].append((intent_phrase, kw))
                    matched = True
                    break
            if matched:
                break
        
        if not matched:
            if is_roblox:
                clusters["guides"].append((intent_phrase, kw))
            else:
                if "how" in intent_phrase or "guide" in intent_phrase:
                    clusters["walkthrough"].append((intent_phrase, kw))
                else:
                    clusters["reference"].append((intent_phrase, kw))

    return clusters


def generate_channels_config(game: str, clustered_kw: dict, is_roblox: bool = False) -> str:
    """生成合规的 channels.ts 源代码"""
    clusters_config = ROBLOX_INTENT_CLUSTERS if is_roblox else STEAM_INTENT_CLUSTERS
    channels_data = []

    for c in clusters_config:
        cid = c["id"]
        items = clustered_kw.get(cid, [])
        guides = []
        seen_slugs = set()

        url_prefix = c.get("urlPrefix", f"/guide/")

        for phrase, full_kw in items[:4]:
            slug = slugify(phrase)
            if len(slug) < 3 or slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            
            title_words = [w.capitalize() for w in phrase.split()]
            title = f"{game} {' '.join(title_words)}"
            if len(title) > 45:
                title = " ".join(title_words)
            
            guide_url = f"{url_prefix}{slug}/" if cid != "codes" and cid != "trello" else f"{url_prefix}"
            guides.append({
                "id": slug,
                "title": title,
                "url": guide_url,
            })

        if len(guides) < 2:
            for def_id, def_title in c["defaultGuides"]:
                if def_id not in seen_slugs:
                    seen_slugs.add(def_id)
                    guides.append({
                        "id": def_id,
                        "title": f"{game} {def_title}",
                        "url": f"{url_prefix}{def_id}/" if cid != "trello" and cid != "codes" else url_prefix,
                    })
                if len(guides) >= 2:
                    break

        primary_url = url_prefix if is_roblox else (guides[0]["url"] if guides else "/guide/")
        
        channels_data.append({
            "id": c["id"],
            "title": c["titleTemplate"],
            "shortTitle": c["shortTitle"],
            "url": primary_url,
            "color": c["color"],
            "guides": guides,
        })

    arch_name = "Roblox 8 大意图频道" if is_roblox else "Steam 5 大核心意图频道"
    ts_code = [
        "// ============================================================",
        f"// [Config 层] channels.ts — {arch_name}架构定义",
        f"// 由 seo-channel-planner.py 根据 [{game}] Google SERP 真实搜索意图自动生成",
        "// 严格遵循 game-wiki-builder 单一真相源架构",
        "// ============================================================",
        "",
        "export interface ChannelGuide {",
        "  id: string;",
        "  title: string;",
        "  url: string;",
        "}",
        "",
        "export interface Channel {",
        "  id: string;",
        "  title: string;",
        "  shortTitle: string;",
        "  url: string;",
        "  color: string;",
        "  guides: ChannelGuide[];",
        "}",
        "",
        "export const CHANNELS: Channel[] = " + json.dumps(channels_data, indent=2) + ";",
        "",
        "export const TOTAL_GUIDES_COUNT = CHANNELS.reduce((acc, ch) => acc + ch.guides.length, 0);",
        "",
        "export function getChannelByGuideId(guideId: string): Channel {",
        "  return CHANNELS.find((ch) => ch.guides.some((g) => g.id === guideId)) || CHANNELS[0];",
        "}",
        ""
    ]
    return "\n".join(ts_code)


def main() -> int:
    parser = argparse.ArgumentParser(description="游戏攻略站 SEO 意图拓词与导航频道自动规划工具")
    parser.add_argument("--game", required=True, help="游戏官方名，例如 'Anime Zero' 或 'Dinoblade'")
    parser.add_argument("--platform", default="auto", choices=["auto", "steam", "roblox"], help="目标游戏发布平台")
    parser.add_argument("--entities", default="", help="可选英文逗号分隔的独有实体白名单，如 'Shadow Monarch,Void Arbiter'")
    parser.add_argument("--out", default="", help="可选输出文件路径，例如 'src/config/channels.ts'")
    args = parser.parse_args()

    game = args.game.strip()
    is_roblox = args.platform == "roblox" or (args.platform == "auto" and "roblox" in game.lower())

    known_entities = load_known_entities(game, args.entities)
    if known_entities:
        print(f"📦 已加载 {len(known_entities)} 项实体白名单防污染规则")

    raw_keywords = collect_seo_keywords(game, is_roblox=is_roblox)
    print(f"✅ 成功从 Google 接口采集到 {len(raw_keywords)} 个原始搜索短语！")

    valid_kw, filtered_kw = filter_keywords_by_entities(raw_keywords, game, known_entities, is_roblox=is_roblox)
    print(f"🎯 经过实体防污染过滤器校验: 采纳 {len(valid_kw)} 个有效词，过滤 {len(filtered_kw)} 个泛词/污染词")

    if filtered_kw:
        print("\n🚫 过滤掉的非本作实体/泛词列表 (供人工复核):")
        for fkw in filtered_kw[:8]:
            print(f"   • {fkw}")
        if len(filtered_kw) > 8:
            print(f"   ... (其余 {len(filtered_kw) - 8} 项已略过)")

    clustered = cluster_keywords(game, valid_kw, is_roblox=is_roblox)

    arch_title = "Roblox 8 大标准频道矩阵" if is_roblox else "Steam 5 大核心意图矩阵"
    print("\n" + "=" * 70)
    print(f"📊 [{game}] {arch_title}:")
    print("=" * 70)
    clusters_config = ROBLOX_INTENT_CLUSTERS if is_roblox else STEAM_INTENT_CLUSTERS
    for c in clusters_config:
        cid = c["id"]
        items = clustered.get(cid, [])
        print(f"▶ L1 频道: {c['shortTitle']:<10} ({c['titleTemplate']}) [意图命中: {len(items)} 个]")
        for phrase, full_kw in items[:4]:
            print(f"   • L2 意图词: {full_kw}")
        if not items:
            print(f"   • [使用标准化冷启动意图模板]")
        print()

    ts_content = generate_channels_config(game, clustered, is_roblox=is_roblox)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(ts_content, encoding="utf-8")
        print(f"🎉 成功写入 channels 配置文件: {out_path.resolve()}")
    else:
        print("=" * 70)
        print("💡 生成的 channels.ts 配置预览 (可通过 --out 保存):")
        print("=" * 70)
        print(ts_content[:900] + "\n... (更多内容已生成) ...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
