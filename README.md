# game-wiki-template

游戏攻略站模板（Astro 5 + Cloudflare Pages），从 sandustry.quest / scavland.wiki /
graveyardkeeper2.quest 三站的实战代码提炼，融合 [AnvilWiki](https://github.com/PNGTRID/AnvilWiki)
的门禁与分层纪律。

## 设计原则

1. **三层分离**（fork 后 merge 永远干净）：
   - **Code 层** `src/layouts` `src/components` `src/pages` `scripts` —— 几乎不碰，上游升级落这里
   - **Config 层** `src/config/site.config.ts` `astro.config.mjs` `public/robots.txt` —— 起站改一次
   - **Content 层** `src/content/` —— 你的全部内容
2. **每个断言有出处**：schema 强制 `summary`（40-60 词直答块）+ `evidence` 槽位；codes 每码带 `sourceUrl`。
3. **门禁前置**：`check:config → check:content → build → check:links` 四道本地门禁，绿了才推送。
4. **可选功能默认关闭**：广告/GA/IndexNow 全部 config 门控，模板升级不会自动开启。

## 起站五步（目标：1 天内上线）

```bash
# 1. 从模板建你的仓库
git clone <this-template> your-wiki && cd your-wiki && rm -rf .git && git init

# 2. 应用站点信息（只改 Config 层）
python3 scripts/apply-template.py

# 3. 安装并本地验证
npm install && npm run build

# 4. 跑门禁
npm run check:config && npm run check:content && npm run check:links

# 5. 门禁上锁（挂 pre-push，物理执行四道门禁）
npm run setup:hooks

# 6. 推 GitHub → Cloudflare Pages 连仓库（build: npm run build，输出: dist，环境变量 NODE_VERSION=22）

# 7. 双引擎秒级收录推送（上线后执行，Google Indexing API + 微软 Bing IndexNow）
npm run submit:bing
```

> **首发策略**：英语单向击穿——单语言最轻形态先上，验证 US 收录与流量后再开本地化（`locales` 数组加语言即可，双轨 hreflang 只为物理存在的翻译输出 alternate）。

## 门禁一览

| 命令 | 检查什么 | 性质 |
|---|---|---|
| `npm run check:config` | site.config / astro.config / robots.txt 三处域名一致；品牌后缀 ≤12 字符 | 阻断 |
| `npm run check:content` | summary 40-60 词、TDH、codes 带出处、虚构模式 denylist 初筛 | 阻断 |
| `npm run build` | Zod schema 校验 + 全站构建 | 阻断 |
| `npm run check:links` | dist 内链全检（外链只计数不抓取） | 报告（`--strict` 阻断） |

## 内容纪律（写给未来每一个 AI 会话）

- **绝不编造游戏数据**。查不到的数据留空，并注明"源未公布"。
- 时效内容（codes/patch notes）必须维护 `updated` 字段。
- H2 用问题句式，答案紧跟标题，先给 40-60 词直答再展开。
- 读完 [docs/CONTENT-LAYERS.md](docs/CONTENT-LAYERS.md) 再动内容——双层架构是本模板的魂。
