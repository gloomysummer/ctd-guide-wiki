# GSC Request Indexing 自动化 — 执行记忆

## 2026-11-03 16:10 CST（= 00:17 PT）
- CDP 18800 正常，Chrome/147 在线，GSC 会话有效。
- **提交 0/10**：第 1 个 URL（/values/）即 `Quota Exceeded`，脚本按设计停止。
- 已用独立探针抓弹窗原文确认是真配额，非解析误判：
  「Quota Exceeded — Sorry--we couldn't process this request because you've exceeded your daily quota. Please try submitting this again tomorrow.」
- **关键异常**：PT 00:17 时配额仍未重置。说明 GSC 配额**不是严格按太平洋时间 00:00 日切**（或重置有延迟）。下次排程若定在 CST 16:00 之后立即跑，可能连续撞墙 → 建议排程后移到 CST 18:00+。
- 覆盖状态（两次采样，间隔约 4 分钟）：
  - 已收录 3 个：/codes/、/units/、/how-to-solo-nightmare-mode/ → **本来不需要提交，清单浪费 30% 配额**
  - /values/：`Discovered` → `Crawled - currently not indexed`（**采样间隔内推进，Google 正在活跃抓取**）
  - /units/upgraded-titan-cameraman/：`URL unknown to Google` → `Discovered`（同样在推进）
  - 其余 5 个：`Discovered - currently not indexed`
- 产出：`state/gsc-index-requests-2026-11-03.json`（提交结果）、`state/gsc-coverage-2026-11-03.json`（10 个 URL 覆盖状态）
- 结论：配额是当前唯一瓶颈；清单本身需先去重已收录页，把额度集中给 `Discovered` 类页面。
