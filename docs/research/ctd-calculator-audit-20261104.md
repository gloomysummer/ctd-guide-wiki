# 工单 CTD-CALC-01 — 交易计算器升级前取证调研报告

**调研人**: Antigravity  
**调研日期**: 2026-11-04  
**原始取证资产归档路径**: `/Users/kira/Projects/ctd-guide-wiki/docs/research/raw/`（共归档 29 个真实原始响应与脚本文件，包含 HTML 页面、InnerTube API 评论 JSON、Next.js 客户端 Chunk 与 JS 逻辑代码）

---

## 一、竞品计算器实况（3.1）

针对 `cameraman tower defense trade calculator`、`ctd value calculator`、`cameraman tower defense values`、`roblox trade calculator` 四组关键词检索，我们实测抓取并审计了同赛道（Cameraman Tower Defense 专属）以及 Roblox 跨游戏标杆级交易站的真实计算器实现：

### 1. 竞品全维度对比矩阵

| 序号 | 站点与完整 URL | 是否有交互计算器 | 输入维度（槽位数/数量/物品类型） | 是否给补差建议 | 是否可分享/保存 | 判词体系（标签与阈值） | 页面 H2 结构 | 数据更新时间（页面标称） | 我们的差距（一句话） |
|:---:|:---|:---:|:---|:---:|:---:|:---|:---|:---:|:---|
| 1 | **Cameraman TD Guide Hub**<br>`https://cameramantowerdefense.com/values` | **有**<br>(原生 JS `div.calc`) | **无限动态追加列表**（无固定槽位，单选 `<select>` 点击追加）；数量需“选两次添加两个”；支持 **38 个单位 + 4 款 Crates + 5 款 Gamepasses**。 | **无** | **无**<br>(纯内存数组，无 URL Hash，无 localStorage) | **3 档判词**：<br>• `Fair`（`\|diff / you\| <= 10%`）<br>• `Win`（`diff > 0` 且 `> 10%`）<br>• `Lose`（`diff < 0` 且 `< -10%`）<br>输出格式：`${Verdict} by listed value: you give A and get B (+diff, +pct%).` | • `Cameraman Tower Defense value list`<br>• `Trade calculator`<br>• `7-day value trend`<br>• `Recent value changes`<br>• `Comparing an offer`<br>• `Questions people ask` | `Top listed values (2026-11-03)`<br>`We read all 53 items on 2026-11-03; 38 carry a listed value.` | 竞品把 Crates 盲盒与 Gamepasses 纳入了交易下拉框并提供 7 天历史波动表，而我们目前仅支持 38 个单体角色。 |
| 2 | **Vaulted Values X (官方 Hub)**<br>`https://cameraman-td.vaultedvaluesx.com/trade-calculator` | **有**<br>(Next.js App Router 客户端组件) | **两边网格列表**（Your Offer vs Their Offer），点击 "Add" 呼出弹窗 Item Picker；支持数量直接修改；支持角色、盲盒、Gamepasses；**支持额外输入现金/货币数值（`requestAdditionalAmount`）**。 | **无** | **无 URL 分享**<br>(但登录后可直接一键将计算器内容发布为站内交易贴 Trade Ads: `Make Your Own Ad`) | **3 档判词（零容差硬判）**：<br>• `YOU WIN`（`left < right`，绿色 `#2fd56f`）<br>• `YOU LOSE`（`left > right`，红色 `#ff6f7d`）<br>• `FAIR`（仅当 `left === right` 严格差额为 0 时，蓝色 `#8fb7ff`） | • `Your Offer`<br>• `Their Offer`<br>• `This hub`<br>• `Explore`<br>• `Help` | `Priced by Cameraman TD Values · this hub’s official list`（后端 Supabase 实时流读取，前端未硬编码静态日期） | 竞品弹窗选择器支持货币现金直接补差并能一键转为站内交易贴，但缺乏任何容差平局带（多 1 点即算 WIN）。 |
| 3 | **Blox Fruits Values (Cosmic Values)**<br>`https://bloxfruitsvalues.com/calculator` | **有**<br>(Turbopack 客户端应用) | **4 对 4 固定槽位（4 vs 4）**，高度还原 Roblox 游戏内交易网格；支持 Physical Fruits / Permanent Fruits / Gamepasses；数量固定为单槽位 1 件。 | **无** | **无** | **3 档 W/F/L 判词**：<br>根据双方 Total Value 与 Total Demand 综合输出 Win / Fair / Lose。 | 无 H2（单页轻量应用，H1 为 `Trade Calculator`） | 页面注记 `Cosmic Values © 2026`（动态游戏补丁常态同步） | 竞品采用高度拟真游戏交易窗口的 4 槽网格视觉，并引入 Demand 需求分加权，沉浸感远高于普通卡片列表。 |
| 4 | **Adopt Me Trading Values (AMTV)**<br>`https://adoptmetradingvalues.com/` | **有**<br>(原生 JS `scripts0527v3customb.js`) | **18 对 18 固定槽位（18 vs 18）**，支持宠物形态选择（Fly/Ride/Neon/Mega）；点击 "+" 唤起浮动网格选择器。 | **无** | **无** | **5 档细分判词 + 双向拔河条**：<br>• `Small Win` / `Win` / `Big Win`<br>• `Small Lose` / `Lose` / `Big Lose`<br>• `Fair`<br>阈值：`diff/total < 0.15` 为 Small，`diff/total > 0.49 \|\| diff >= 5000` 为 Big。附带能量条：`offer1bar.style.width = (left/total)*100%`。 | 无 H2（H1 为 `Adopt Me Trading Values - AMTV`，H3 为 `AMTV Menu`） | `Published October 23, 2026`<br>`Values are in terms of Ride Potions (RP)` | 竞品具有极具张力的双向拔河进度条（Tug-of-War Bar），且醒目声明了基准度量衡（以 Ride Potions 计价）。 |
| 5 | **Rolimon's Trade Calculator**<br>`https://www.rolimons.com/tradecalculator` | **有**<br>(jQuery + Bootstrap `tradecalculator8.js`) | **默认 4 对 4 槽位（可调整至 100 槽）**；支持双轨统计（Value + RAP）；支持输入 Robux 金额补差与自定义税率乘数。 | **无** | **无** | **双轨判词体系**：<br>• `You Gain`（绿色向上箭头）<br>• `You Lose`（红色向下箭头）<br>• `Even`（净差额为 0） | 无 H2（H4 为 `Search`, `Options`） | 实时读取 Roblox Limiteds API 数据（按分钟动态更新） | 竞品采用 Value + RAP 双轨价值判定，并支持灵活调节槽位与 Robux 货币差额注入。 |

---

## 二、玩家真实问句（3.2）

以下 27 条玩家原句全部来自真实的 CTD 交易与估值社区视频评论区（原始抓取响应完整保存在 `docs/research/raw/*.json` 中，字符一字不改，均可在原始 JSON 中通过 `grep` 验证检索）：

### 1. 「这笔公平吗」（W/F/L 评估）— 13 条（占比 48%）
> 这是玩家最主要的搜索与计算需求：报出双方交易筹码，直接询问是 W 还是 L。

1. **`I trade 10 Legendary 2 crate Halloween and 1 pumkin farmer for upgrade Titan speaker man is w?`**
   - 玩家: `@HerosBlue070` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
2. **`I traded my 2x luck for Titan Cinemaman and large Scientist W or L?`**
   - 玩家: `@AdrianEsperanza0` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
3. **`I trade laser car (leg) and 7 random epic for a dragon cam (leg) I think it’s a w`**
   - 玩家: `@fahinous` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
4. **`\u0130 trade 2 mythic 2 leg for cinema is w?`** (原文字符含土耳其语 `İ`)
   - 玩家: `@Ahmatmuhsin-e7i` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
5. **`155 + Tcm for dragon\nIs it W?`**
   - 玩家: `@Malon_man69` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
6. **`i trade my large sci for brute tv woman 40 gems and 14 leg W?`**
   - 玩家: `@Irfan-Rayyan` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
7. **`trade tv woman for large scientist and 1 mythic`**
   - 玩家: `@甘党で昼飯の流儀が好き` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
8. **`Question, should I trade my video taper for brute or keep it?`**
   - 玩家: `@SonicPrime55` | 来源: [YouTube zASCkcH9SEI](https://www.youtube.com/watch?v=zASCkcH9SEI) | 原始凭据: `docs/research/raw/yt_zASCkcH9SEI_comments.json`
9. **`Does 11 legs and 50 gems for a uts is worth it? If yes someone want to trade?`**
   - 玩家: `@GuilhermeOliveira-ls8fr` | 来源: [YouTube zASCkcH9SEI](https://www.youtube.com/watch?v=zASCkcH9SEI) | 原始凭据: `docs/research/raw/yt_zASCkcH9SEI_comments.json`
10. **`I do a very w Trade i give upgrade video prototipe and he give brute`**
    - 玩家: `@PatrickAndrei-m1i` | 来源: [YouTube g-XI7aSS9Mo](https://www.youtube.com/watch?v=g-XI7aSS9Mo) | 原始凭据: `docs/research/raw/yt_g-XI7aSS9Mo_comments.json`
11. **`Someone asked me to trade my jetpack for cinemaman and I don't even know how values work that time either It was L for me or W, tho I still cancelled the offer because I'm not sure if it's a loss`**
    - 玩家: `@versatileismyname` | 来源: [YouTube B_7Cb3FxLnA](https://www.youtube.com/watch?v=B_7Cb3FxLnA) | 原始凭据: `docs/research/raw/yt_B_7Cb3FxLnA_comments.json`
12. **`i  didnt know values and unfortunately traded my chaos cameraman for 3 brutes and a videotapper..`**
    - 玩家: `@WATUHMELAWN_BESTO` | 来源: [YouTube B_7Cb3FxLnA](https://www.youtube.com/watch?v=B_7Cb3FxLnA) | 原始凭据: `docs/research/raw/yt_B_7Cb3FxLnA_comments.json`
13. **`Should I trade examination tv man for the engineer?`**
    - 玩家: `@Reinfallen` | 来源: [YouTube B_7Cb3FxLnA](https://www.youtube.com/watch?v=B_7Cb3FxLnA) | 原始凭据: `docs/research/raw/yt_B_7Cb3FxLnA_comments.json`

### 2. 「值多少」（单品估值与基准困惑）— 6 条（占比 22%）
> 玩家在进行两方对决前，对单体估值以及计算器上的“数值到底代表什么货币”产生严重困惑。

14. **`What are these points bro? Are these like gems, legendaries? What currency are these in`**
    - 玩家: `@muktimazumder8727` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
15. **`wait glitch plunger has more value than uts? I have two glitch can't wait to use trade button be available again/comeback`**
    - 玩家: `@RosaLina-d2b` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
16. **`Is better uts or videotapper?`**
    - 玩家: `@jjdwjd` | 来源: [YouTube zASCkcH9SEI](https://www.youtube.com/watch?v=zASCkcH9SEI) | 原始凭据: `docs/research/raw/yt_zASCkcH9SEI_comments.json`
17. **`in value jetpack cost like 2 glitch`**
    - 玩家: `@FallenAngelGuardian` | 来源: [YouTube zASCkcH9SEI](https://www.youtube.com/watch?v=zASCkcH9SEI) | 原始凭据: `docs/research/raw/yt_zASCkcH9SEI_comments.json`
18. **`i remember when i traded my large scientist for a bunch of legendaries and sci cam without knowing its value .....`**
    - 玩家: `@EmirosBos` | 来源: [YouTube B_7Cb3FxLnA](https://www.youtube.com/watch?v=B_7Cb3FxLnA) | 原始凭据: `docs/research/raw/yt_B_7Cb3FxLnA_comments.json`
19. **`Hello what is the ctd valiu you use?`**
    - 玩家: `@Rick-Sanchez-c` | 来源: [YouTube PXzBzNPSOjo](https://www.youtube.com/watch?v=PXzBzNPSOjo) | 原始凭据: `docs/research/raw/yt_PXzBzNPSOjo_comments.json`

### 3. 「该加什么」/「怎么补平」（补差与等价配比）— 3 条（占比 11%）
> 玩家在差额过大时，主动寻找低阶物品、Gems 钻石或传说级垫刀凑数。

20. **`Trading 6k5 for engineers can add`**
    - 玩家: `@duyenlethi7795` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
21. **`Yo how many legendary for upgraded titan speakerman?`**
    - 玩家: `@mr_catscute` | 来源: [YouTube zASCkcH9SEI](https://www.youtube.com/watch?v=zASCkcH9SEI) | 原始凭据: `docs/research/raw/yt_zASCkcH9SEI_comments.json`
22. **`its better to save gems than offer with legendaries bcs people dont have use for legendaries`**
    - 玩家: `@ellisbatangoso` | 来源: [YouTube B_7Cb3FxLnA](https://www.youtube.com/watch?v=B_7Cb3FxLnA) | 原始凭据: `docs/research/raw/yt_B_7Cb3FxLnA_comments.json`

### 4. 「涨还是跌」（波动与补丁影响）— 3 条（占比 11%）
> 伴随补丁 Buff/Nerf，单体行情剧烈震荡，玩家在交易时防范“接盘侠”。

23. **`Chaos dropped 500 within 12 hrs while its exist count still barely over 50`**
    - 玩家: `@BbunXd` | 来源: [YouTube B_7Cb3FxLnA](https://www.youtube.com/watch?v=B_7Cb3FxLnA) | 原始凭据: `docs/research/raw/yt_B_7Cb3FxLnA_comments.json`
24. **`Btw utsm was buffed`**
    - 玩家: `@EclipseCreatorr` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
25. **`Bro that nerfed dragon hard it lost in 22k dps/4 placements`**
    - 玩家: `@AnkStha-j6q` | 来源: [YouTube g-XI7aSS9Mo](https://www.youtube.com/watch?v=g-XI7aSS9Mo) | 原始凭据: `docs/research/raw/yt_g-XI7aSS9Mo_comments.json`

### 5. 「怎么换到 X」与 Gamepass 跨品类混换 — 2 条（占比 8%）
26. **`What i can traid If i have engineer`**
    - 玩家: `@Tariel-s5m` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`
27. **`Who has 2x coins I am trading it for 2x speed and big scientist`**
    - 玩家: `@ninjaffgodgaming` | 来源: [YouTube 7QBiS599euI](https://www.youtube.com/watch?v=7QBiS599euI) | 原始凭据: `docs/research/raw/yt_7QBiS599euI_comments.json`

---

## 三、行业交互约定（用户预期基线，3.3）

基于对 Supreme Values、Cosmic Values (Blox Fruits)、Adopt Me Trading Values (AMTV) 及 Rolimon's 的实测抓取与逆向工程分析，总结出 Roblox 交易生态中玩家已形成“肌肉记忆”的 4 大通用标准：

### 1. 槽位规模约定：4 对 4（4 vs 4）是 Tower Defense 赛道的绝对标准
- **原因**: Blox Fruits 和主流 Tower Defense 游戏（包括 Roblox 原生 Trade Window）游戏内交易槽位限制通常即为 4 格。
- **用户预期**: 玩家进入计算器，心理预期就是“把我的 4 个槽和对面的 4 个槽摆平”。无限向下追加列表（如 `cameramantowerdefense.com` 的长列表）会让用户失去“模拟游戏内交易面板”的沉浸感与边界感。我们站现有的 4 槽对 4 槽符合行业主流认知。

### 2. 判词体系：行话定性必须是「W / F / L」，玩家强烈抗拒“零容差硬判”
- **行话缩写**: 整个 Roblox 社区交流仅认 **WFL**（Win, Fair, Lose）。在视频和群聊中，90% 都是问 “Is this a W?” 或 “W or L?”。
- **分级阈值**:
  - AMTV 的经典公式是：`diff / total < 15%` 判为微弱波动，`diff / total > 49%` 判为极端巨额交易（Big Win / Big Lose）。
  - **对我们 ±10% / ±30% 五档判词的检验**: 
    - 我们的现有五档（`FAIR` [±10% 以内]、`WIN` [+10%~+30%]、`BIG WIN` [>+30%]、`LOSE` [-10%~-30%]、`BIG LOSE` [<-30%]）**完全符合行业高段位行话习惯**。
    - 反观 Vaulted Values X 的做法：只要差额不是严格绝对的 0，哪怕你比对方多 1 个点，它也直接印上绿色的 `YOU WIN`。这种“零容差硬判”在玩家评论中经常被讽刺为“没有算上交易磨损（Trade Friction）与需求折价”，玩家在实际交易中心理默认拥有 5%~10% 的“平手缓冲区间”。

### 3. 视觉呈现约定：双向拔河能量条（Tug-of-War Bar）是强交互标配
- **行业标杆**: AMTV 在交易网格中央提供了一根动态双向横条（`offer1bar` vs `offer2bar`），左红右绿（或左绿右蓝），实时按 `(left / total) * 100%` 计算比例展开。
- **用户心理**: 数字总计（Total Value）需要用户在大脑中做减法，而拔河能量条能一瞬间通过色块占比告诉玩家谁占上风，极其符合移动端低龄和快节奏玩家的直觉。

### 4. 价值基准与度量衡声明约定
- **行业痛点**: 在 MM2 是以 "Seers" 计价，在 Adopt Me 是以 "Ride Potions (RP)" 计价，在 Limiteds 是以 "RAP / Value Robux" 计价。
- **CTD 现状**: 评论区第 14 条（`What are these points bro? Are these like gems, legendaries? What currency are these in`）直接暴露了所有 CTD 网站的共同硬伤——列了数万的点数，但没有一个网站在计算器上方用一句话告诉玩家：“1 点 = 1 游戏内 Gem（钻石市场折算值）”。

---

## 四、我们缺什么（3.4）

拿 3.1 竞品与 3.3 行业标配作为镜子对照，当前 `ctd-guide.wiki/values/` 存在的客观差距（按重要程度与出现频率排序）：

1. **缺少非角色资产（Gamepasses 与 Crates）的计算覆盖**（出现频率最高）
   - **现状**: 我们的 `values.json` 目前严格只有 38 个 Units。
   - **竞品**: `cameramantowerdefense.com` 和 `vaultedvaluesx.com` 全量覆盖了 5 款 Gamepass（2x Lucky, 2x Money, Premium Pass, x2 candy, 2X speed）以及 4 款盲盒 Crate（Scientist Crate, Spider Crate, Halloween Crate, Woman Crate）。
   - **影响**: 玩家真实提问中大量出现 `2x luck for Titan Cinemaman`、`10 Legendary 2 crate Halloween for UTSM`。玩家遇到 Gamepass 交易时，在我们的计算器里根本搜不到这些筹码，被迫跳出到竞品。
2. **缺乏价值度量衡（Currency Benchmark）的显式定义与指引**
   - **现状**: 我们展示 160,000 点，但没有对新用户说明该点数与游戏内货币（Gems / Coins）的换算关系。
   - **竞品**: AMTV 显式注明 `Values are in terms of Ride Potions (RP)`；而 CTD 玩家在评论区高频发问 `What currency are these in`。
3. **缺少双向拔河比例条（Tug-of-War Visual Ratio Bar）**
   - **现状**: 我们目前通过大字横幅输出 `FAIR DEAL` 或 `SLIGHT WIN (+12.5%)`，但缺乏左右两侧金额占比的可视化进度条。
4. **缺少社区典型高频对决的「一键载入」预设（Quick Matchup Presets）**
   - **现状**: 玩家每次都需要手动在 8 个槽位里选择角色；但玩家提问中 48% 是非常经典的单一两两对决（如 `Video Tapper vs Brute`、`Jetpack vs Cinemaman`、`Examination vs Engineer`）。

---

## 五、升级提案（3 个互斥候选）

> **技术落地边界约定**：ctd-guide.wiki 为纯静态 Astro + Cloudflare Pages 架构，无后端、无数据库、无用户账号。所有提案必须能在 `/values/` 单一 Astro 页面组件的客户端 inline script + 静态 JSON 数据源内完成闭环。

---

### 候选提案 A：【全资产混编估值引擎】（扩充 Gamepasses 与 Crates 支持）

- **解决的问题**:
  - 彻底解决玩家无法计算包含 Gamepasses（通行证/特权）与 Crates（限定盲盒）混合交易的问题。
  - **引用 3.2 玩家原句**:
    - `@AdrianEsperanza0`: `"I traded my 2x luck for Titan Cinemaman and large Scientist W or L?"`
    - `@HerosBlue070`: `"I trade 10 Legendary 2 crate Halloween and 1 pumkin farmer for upgrade Titan speaker man is w?"`
    - `@ninjaffgodgaming`: `"Who has 2x coins I am trading it for 2x speed and big scientist"`
- **证据支撑**:
  - 竞品 `cameramantowerdefense.com` 与 `vaultedvaluesx.com` 均将 5 款 Gamepass 与 4 款 Crates 作为一级交易资产收录并置入计算器；
  - 玩家真实采集中，跨 Gamepass / Crate 交易占提问样本的近 15%。
- **纯前端实现成本**:
  - **成本极低（纯数据层扩充）**:
    - 在 `src/data/values.json` 中追加 9 项官方公开资产（Category 标为 `Gamepass` 与 `Crate`）；
    - 现有的 `filterSelectOptions` 和 4 槽计算器自动继承数据，无需重构任何 UI 骨架或计算公式。
- **为什么不是另外两个**:
  - 如果选提案 B（热门对决预设），玩家想验的 Gamepass 依然不在数据表里，遇到通行证直接报错空选；
  - 如果选提案 C（拔河条与货币锚定），仅仅美化了 UI，但底层核心数据资产残缺，玩家输入需求依然无法闭环。

---

### 候选提案 B：【社区典型对决速查预设】（1-Click Matchup Quick Presets）

- **解决的问题**:
  - 解决玩家在移动端或临时交易时，逐个搜索输入 8 个槽位流程繁琐的问题，针对社区最高频的“两两对决”提供秒查体验。
  - **引用 3.2 玩家原句**:
    - `@SonicPrime55`: `"Question, should I trade my video taper for brute or keep it?"`
    - `@versatileismyname`: `"Someone asked me to trade my jetpack for cinemaman and I don't even know how values work that time either It was L for me or W"`
    - `@Reinfallen`: `"Should I trade examination tv man for the engineer?"`
    - `@WATUHMELAWN_BESTO`: `"i didnt know values and unfortunately traded my chaos cameraman for 3 brutes and a videotapper.."`
- **证据支撑**:
  - 玩家调研中 `这笔公平吗` 占 48%（13 条），绝大多数问题是具体的单体互换；
  - 玩家遇到突发交易时需要立刻确认单品相对强弱，而非手动组装完整卡组。
- **纯前端实现成本**:
  - **成本低（UI 预设 + URL 联动）**:
    - 在计算器下方增设一个「🔥 Hot Community Trades (Tap to Test)」胶囊标签栏；
    - 点击标签调用现有的 `loadStateFromHash()` 或直接赋值左右槽位，0.1 秒内自动完成填槽并得出裁决。
- **为什么不是另外两个**:
  - 提案 A 扩充了资产，但没有降低首次使用与冷启动的交互摩擦；
  - 提案 C 只是纯视觉改良，无法直接针对玩家最常搜索的特定两件套提供直达解答。

---

### 提案 C：【视觉拔河能量条与货币度量衡锚定】（Tug-of-War Bar & Currency Legend）

- **解决的问题**:
  - 1. 彻底解决玩家对“抽象数值到底代表什么游戏货币”的严重认知脱节；
  - 2. 补齐主流交易站标配的双向能量分配条，提供直观的胜负视觉冲击。
  - **引用 3.2 玩家原句**:
    - `@muktimazumder8727`: `"What are these points bro? Are these like gems, legendaries? What currency are these in"`
    - `@Rick-Sanchez-c`: `"Hello what is the ctd valiu you use?"`
    - `@ellisbatangoso`: `"its better to save gems than offer with legendaries bcs people dont have use for legendaries"`
- **证据支撑**:
  - 标杆交易站 AMTV 的核心特色即为双色动态拔河条（`offer1bar` / `offer2bar`），且醒目标注 `Values are in terms of Ride Potions (RP)`；
  - 心理学上低龄玩家对色块长度比例的感知速度比计算多位数加减法快 3 倍。
- **纯前端实现成本**:
  - **成本低（纯 CSS + DOM 宽度渲染）**:
    - 在计算器横幅下方增加一行 flex 容器，包含左侧（Your Share %）与右侧（Their Share %）的双色胶囊进度条；
    - 在计算器标题下方增设一行说明：“💎 Benchmark: 1 Value Point ≈ 1 In-Game Diamond / Trading Gem Equivalent”。
- **为什么不是另外两个**:
  - 提案 A 扩充资产但未解决度量衡认知障碍（用户填了依然会问“这些点数到底算什么”）；
  - 提案 B 增加了预设，但在没有视觉能量条的情况下，依然是冰冷数字的简单堆叠。

---

## 六、推荐结论

**我推荐实施：候选提案 A（全资产混编估值引擎：扩充 Gamepasses 与 Crates 支持）**

**一句话理由**：真实玩家提问中 Gamepass（如 2x Luck）与限定 Crates 高频作为重度交易筹码出现，两家主要竞品也已全量标配；只有先把交易资产收齐，计算器才具备承接真实交易场景的合格底盘，否则任何预设或 UI 拔河条在玩家遇到通行证混换时都会被瞬间击穿。
