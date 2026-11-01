#!/usr/bin/env bash
# supervisor-guard.sh — 攻略站建站与日常运营确定性督查门禁（Supervisor Guard Engine）
#
# 设计原则:
# 1. 纯确定性脚本校验：每项断言输出 OK/FAIL 与客观证据值，全绿才判定 PASS。
# 2. 结构合规 ≠ 内容真实：严格校验兑换码来源凭据、拒绝占位符与跨站资产污染。
# 3. 参数化开箱即用：支持环境变量配置与命令行参数，适配 Steam 与 Roblox 双平台。
#
# 用法:
#   ./supervisor-guard.sh                        # 人类可读终端表格
#   ./supervisor-guard.sh --json                 # 机器自动化采集输出
#   ./supervisor-guard.sh --repo /path/to/wiki --platform roblox --channels 8
#
set -u
export PATH=/usr/bin:/bin:/usr/local/bin:/usr/sbin:/sbin

# ==============================================================================
# 0. 参数化可配置区 (可通过环境变量或 CLI 覆盖)
# ==============================================================================
REPO="${REPO:-$(pwd)}"
SITE_KEY="${SITE_KEY:-$(basename "$REPO")}"
CONV="${CONV:-}"
PLATFORM="${PLATFORM:-roblox}"   # roblox | steam
REQUIRED_CHANNELS="${REQUIRED_CHANNELS:-8}" # roblox=8, steam=5
RESIDUE_TERMS="${RESIDUE_TERMS:-automate-flower|flower production|gk1_vs_gk2|duckov|scavland|dinoblade}"
POLLUTION_TERMS="${POLLUTION_TERMS:-zero two|no tsukaima|zero to hero|tower defense|code geass|isekai}"
EXPECTED_UNIVERSE_ID="${EXPECTED_UNIVERSE_ID:-}"

OUT_MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --conv) CONV="$2"; shift 2 ;;
    --platform) PLATFORM="$2"; shift 2 ;;
    --channels) REQUIRED_CHANNELS="$2"; shift 2 ;;
    --universe-id) EXPECTED_UNIVERSE_ID="$2"; shift 2 ;;
    --json|json) OUT_MODE="json"; shift ;;
    *) shift ;;
  esac
done

JSON=0
[ "$OUT_MODE" = "json" ] && JSON=1

declare -a RESULTS=()
FAILS=0

add() {  # add <OK|FAIL> <name> <detail>
  RESULTS+=("$1|$2|$3")
  if [ "$1" = "FAIL" ]; then FAILS=$((FAILS+1)); fi
}

# ---------- 0. 环境与仓库基线 ----------
if [ ! -d "$REPO" ]; then
  echo "VERDICT: ENV_ERROR (repo 目录不存在: $REPO)"; exit 2
fi

# ---------- 1. Git 提交回滚点审计 ----------
COMMITS=$(cd "$REPO" && git rev-list --count HEAD 2>/dev/null || echo 0)
if [ "${COMMITS:-0}" -ge 1 ]; then
  add OK git_commits "${COMMITS} commits"
else
  add FAIL git_commits "0 — 无任何 git commit 回滚点（必须分阶段提交）"
fi

# ---------- 2. channels.ts 残留与频道数审计 ----------
CH="$REPO/src/config/channels.ts"
if [ ! -f "$CH" ]; then
  add FAIL channels_exists "src/config/channels.ts 不存在"
else
  RES=$(grep -icE "$RESIDUE_TERMS" "$CH" || true); RES=${RES:-0}
  NCH=$(grep -oE 'shortTitle:[[:space:]]*"[^"]+"' "$CH" 2>/dev/null | wc -l | tr -d ' ')
  if [ "${RES:-0}" -gt 0 ]; then
    add FAIL channels_residue "$RES 处母版/他游残留词 (匹配: $RESIDUE_TERMS)"
  else
    add OK channels_residue "0"
  fi
  if [ "${NCH:-0}" -eq "$REQUIRED_CHANNELS" ]; then
    add OK channels_channels "$NCH 个一级频道 (符合 $PLATFORM 标准)"
  else
    add FAIL channels_channels "只有 $NCH 个 shortTitle（要求 $REQUIRED_CHANNELS 个）"
  fi
fi

# ---------- 3. llms.txt 残留审计 ----------
LL="$REPO/public/llms.txt"
if [ -f "$LL" ]; then
  LRES=$(grep -icE "$RESIDUE_TERMS" "$LL" || true); LRES=${LRES:-0}
  if [ "${LRES:-0}" -gt 0 ]; then
    add FAIL llms_residue "$LRES 处他游残留词 (匹配: $RESIDUE_TERMS)"
  else
    add OK llms_residue "0"
  fi
else
  add OK llms_residue "文件未生成(跳过)"
fi

# ---------- 4. dossier 事实源与占位符审计 ----------
DJ="$REPO/dossier/dossier.json"
if [ -f "$DJ" ]; then
  PH=$(grep -cE '"Community / Developers"|"Platform Host"' "$DJ" || true); PH=${PH:-0}
  SZ=$(wc -c < "$DJ" | tr -d ' ')
  if [ "${PH:-0}" -gt 0 ]; then
    add FAIL dossier_placeholder "$PH 处未替换的占位符 (Community / Developers 等)"
  else
    add OK dossier_placeholder "0 (size=${SZ}B)"
  fi
  if [ -n "$EXPECTED_UNIVERSE_ID" ]; then
    UNIV=$(grep -c "$EXPECTED_UNIVERSE_ID" "$DJ" || true); UNIV=${UNIV:-0}
    if [ "${UNIV:-0}" -ge 1 ]; then
      add OK dossier_universe "universeId 已写入 ($EXPECTED_UNIVERSE_ID)"
    else
      add FAIL dossier_universe "未包含预期的 universeId: $EXPECTED_UNIVERSE_ID"
    fi
  else
    add OK dossier_universe "未指定 universeId 校验要求(跳过)"
  fi
else
  add FAIL dossier_exists "$DJ 档案文件不存在"
fi

# ---------- 5. 跨站资产隔离与哈希防污染审计 ----------
HITS=$(python3 - "$REPO" <<'PY'
import hashlib, os, glob, sys
base = os.path.join(sys.argv[1], 'public')
if not os.path.isdir(base):
    print(0); sys.exit(0)
exts = ('.jpg', '.jpeg', '.png', '.webp', '.svg', '.ico', '.gif')
parent_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
others = [d for d in glob.glob(os.path.join(parent_dir, '*/public')) if sys.argv[1] not in d]

def get_hash(p):
    try:
        with open(p, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()
    except Exception: return None

m = {}
for o in others:
    for r, _, fs in os.walk(o):
        for fn in fs:
            if fn.lower().endswith(exts):
                fp = os.path.join(r, fn)
                h = get_hash(fp)
                if h: m.setdefault(h, []).append(fp)

hit = 0
for r, _, fs in os.walk(base):
    for fn in fs:
        if fn.lower().endswith(exts):
            h = get_hash(os.path.join(r, fn))
            if h and h in m: hit += 1
print(hit)
PY
)
if [ "${HITS:-1}" -eq 0 ]; then
  add OK asset_isolation "跨站图片哈希 0 命中"
else
  add FAIL asset_isolation "$HITS 个图片资产与存量站同 SHA-256 (违反资产独占原则)"
fi

# ---------- 6. 泛词/别家作品关键词污染 ----------
POLL=0
if [ -n "$POLLUTION_TERMS" ]; then
  POLL=$(grep -ilE "$POLLUTION_TERMS" "$CH" "$LL" "$DJ" 2>/dev/null | wc -l | tr -d ' ')
fi
if [ "${POLL:-0}" -eq 0 ]; then
  add OK keyword_pollution "0 个文件命中负面泛词"
else
  add FAIL keyword_pollution "$POLL 个文件命中泛词/别家作品词 (匹配: $POLLUTION_TERMS)"
fi

# ---------- 7. Codes 真实性与页面覆盖审计 (Roblox 专属) ----------
if [ "$PLATFORM" = "roblox" ]; then
  VC="$REPO/src/data/verified-codes.json"
  if [ ! -f "$VC" ]; then
    add FAIL codes_source_of_truth "src/data/verified-codes.json 不存在 (Roblox 站必建 Codes 单一真相源)"
  else
    N=$(python3 -c "
import json
try:
    d = json.load(open('$VC'))
    c = d.get('codes') or []
    bad = [x for x in c if not x.get('sourceUrl') or not x.get('lastVerified')]
    print(f'{len(c)}|{len(bad)}')
except Exception as e:
    print(f'ERR|{e}')
" 2>/dev/null)
    NC=$(printf '%s' "$N" | cut -d'|' -f1); NBAD=$(printf '%s' "$N" | cut -d'|' -f2)
    if [ "$NC" = "ERR" ]; then
      add FAIL codes_source_of_truth "verified-codes.json 解析失败: $NBAD"
    elif [ "${NC:-0}" -eq 0 ]; then
      add FAIL codes_source_of_truth "codes 数组为空 — 页面无真实兑换码"
    elif [ "${NBAD:-0}" -gt 0 ]; then
      add FAIL codes_source_of_truth "$NBAD 个码缺少 sourceUrl 或 lastVerified"
    else
      add OK codes_source_of_truth "${NC} 个码，均带来源与核实日期"
    fi

    # 检查 active 码在构建产物中的覆盖率
    if [ -f "$REPO/dist/codes/index.html" ] && [ "$NC" != "ERR" ] && [ "${NC:-0}" -gt 0 ]; then
      MISS=$(python3 -c "
import json, re, html
d = json.load(open('$VC'))
page = open('$REPO/dist/codes/index.html', encoding='utf-8', errors='ignore').read()
ptxt = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>', '', page, flags=re.S))).upper()
act = [c['code'].upper() for c in d.get('codes', []) if (c.get('status') or 'active') == 'active']
miss = [c for c in act if c not in ptxt]
print(len(miss))
" 2>/dev/null)
      if [ "${MISS:-1}" -eq 0 ]; then
        add OK codes_coverage "页面覆盖全部 active 码"
      else
        add FAIL codes_coverage "$MISS 个 active 码未出现在 dist/codes/index.html"
      fi
    else
      add OK codes_coverage "dist/codes/index.html 待编译"
    fi
  fi
fi

# ---------- 8. 会话活跃度超时审计 (可选) ----------
if [ -n "$CONV" ]; then
  TRANSCRIPT="$HOME/.gemini/antigravity/brain/$CONV/.system_generated/logs/transcript_full.jsonl"
  if [ -f "$TRANSCRIPT" ]; then
    NOW=$(date +%s)
    MT=$(stat -f %m "$TRANSCRIPT" 2>/dev/null || echo "$NOW")
    IDLE=$(( (NOW - MT) / 60 ))
    if [ "$IDLE" -gt 240 ]; then
      add FAIL session_idle "transcript 已 ${IDLE} 分钟无写入 (>240m，会话可能挂起)"
    else
      add OK session_idle "最近 ${IDLE} 分钟有活跃写入"
    fi
  else
    add FAIL session_idle "会话日志不存在: $TRANSCRIPT"
  fi
fi

# ==============================================================================
# 9. 输出与退出码研判
# ==============================================================================
if [ "$JSON" = "1" ]; then
  printf '{"verdict":"%s","fails":%d,"checks":[' "$([ "$FAILS" -eq 0 ] && echo PASS || echo FAIL)" "$FAILS"
  first=1
  for r in "${RESULTS[@]}"; do
    s=${r%%|*}; rest=${r#*|}; n=${rest%%|*}; d=${rest#*|}
    [ $first -eq 0 ] && printf ','
    first=0
    printf '{"status":"%s","name":"%s","detail":"%s"}' "$s" "$n" "$(printf '%s' "$d" | sed 's/"/\\"/g')"
  done
  printf ']}\n'
else
  echo "=== $SITE_KEY 建站与运营确定性督查门禁 $(date '+%Y-%m-%d %H:%M:%S') ==="
  for r in "${RESULTS[@]}"; do
    s=${r%%|*}; rest=${r#*|}; n=${rest%%|*}; d=${rest#*|}
    printf '  %-4s %-24s %s\n' "$s" "$n" "$d"
  done
  echo "VERDICT: $([ "$FAILS" -eq 0 ] && echo PASS || echo FAIL) (FAIL $FAILS 项)"
fi

[ "$FAILS" -eq 0 ] && exit 0 || exit 1
