#!/usr/bin/env python3
"""AI-GMoire Skill 擲骰與隨機分配工具（只用標準函式庫，以 secrets 取得系統隨機數）。

給具備程式碼執行能力的 AI-agent 使用。沒有執行環境時請改用「隨機與判定協定」的其他來源，
不要憑空編造輸出。

用法（以 Skill 資料夾為工作目錄）：
  python scripts/roll.py dice 1d20                    擲骰，支援 NdM±K，例：2d6+1
  python scripts/roll.py check --dc 12 --mod 2        d20 判定：d20＋修正對照難度
                              [--mode adv|dis]         順勢（2d20 取高）／逆勢（2d20 取低）
  python scripts/roll.py pick 選項A 選項B 選項C       從選項抽 1 個；--count 2 抽 2 個不重複
  python scripts/roll.py alloc --items 項目1,項目2,… --cap 略通 --min-low 3
                                                       在上限內隨機分配等第（見下）
  加上 --json 輸出 JSON，--quiet 只輸出結果行。

check 的結果分級：被採用的那顆 d20 天然 20＝大成功、天然 1＝大失敗（不論修正值與難度）；
其餘依差（總和－難度）：差 0 以上＝成功；差 -1 至 -3＝部分成功；差 -4 以下＝失敗。

alloc 參數：
  --items       以逗號分隔的項目（例如魔法專業科目）
  --levels      由低到高的等第，預設 未涉獵,入門,初學,略通,熟練,專精,精通
  --cap         每一項的等第上限（含）
  --min-low     至少要有幾項落在 --low 指定的等第內，預設 0
  --low         視為「低等第」的名稱，預設 未涉獵,入門
  --max-at-cap  至多幾項可達到上限，預設不限
  --floor       最低等第，預設為 levels 的第一個
"""
import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone

DEFAULT_LEVELS = "未涉獵,入門,初學,略通,熟練,專精,精通"
_rng = secrets.SystemRandom()


def stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def parse_dice(expr):
    m = re.fullmatch(r"(\d*)d(\d+)([+-]\d+)?", expr.strip().lower())
    if not m:
        raise SystemExit(f"骰式格式錯誤：{expr!r}，範例：1d20、2d6+1")
    n = int(m.group(1) or 1)
    sides = int(m.group(2))
    mod = int(m.group(3) or 0)
    if not (1 <= n <= 100 and 2 <= sides <= 1000):
        raise SystemExit("骰數需為 1 至 100，面數需為 2 至 1000")
    return n, sides, mod


def cmd_dice(args):
    n, sides, mod = parse_dice(args.expr)
    rolls = [_rng.randrange(1, sides + 1) for _ in range(n)]
    total = sum(rolls) + mod
    line = f"{args.expr} = {rolls}" + (f" {mod:+d}" if mod else "") + f" = {total}"
    return line, {"expr": args.expr, "rolls": rolls, "modifier": mod, "total": total}


def grade(margin, natural=None):
    """天然 20／1（單顆 d20）優先，不論修正值與難度；其餘依差值（總和 - 難度）分三級。"""
    if natural == 20:
        return "大成功"
    if natural == 1:
        return "大失敗"
    if margin >= 0:
        return "成功"
    if margin >= -3:
        return "部分成功"
    return "失敗"


MODE_LABEL = {"normal": "", "adv": "2d20 取高", "dis": "2d20 取低"}


def cmd_check(args):
    if args.mode == "normal":
        dice = [_rng.randrange(1, 21)]
        die = dice[0]
    else:
        dice = [_rng.randrange(1, 21), _rng.randrange(1, 21)]
        die = max(dice) if args.mode == "adv" else min(dice)
    total = die + args.mod
    margin = total - args.dc
    result = grade(margin, die)
    shown = f"{die}（{MODE_LABEL[args.mode]}：{dice[0]}、{dice[1]}）" if len(dice) == 2 else str(die)
    line = (f"d20 = {shown}，修正 = {args.mod:+d}，總和 = {total}，難度 = {args.dc}，"
            f"差 = {margin:+d}，等級 = {result}")
    natural = die if die in (1, 20) else None
    if natural:
        line += f"（天然 {natural}）"
    return line, {"d20": die, "rolled": dice, "mode": args.mode, "natural": natural, "modifier": args.mod,
                  "total": total, "dc": args.dc, "margin": margin, "result": result}


def cmd_pick(args):
    if not 1 <= args.count <= len(args.options):
        raise SystemExit("--count 需介於 1 與選項數之間")
    chosen = _rng.sample(args.options, args.count)
    return "抽中：" + "、".join(chosen), {"options": args.options, "chosen": chosen}


def cmd_alloc(args):
    items = [s.strip() for s in args.items.split(",") if s.strip()]
    levels = [s.strip() for s in args.levels.split(",") if s.strip()]
    low = {s.strip() for s in args.low.split(",") if s.strip()}
    for name, value in (("--cap", args.cap), ("--floor", args.floor or levels[0])):
        if value not in levels:
            raise SystemExit(f"{name} 的 {value!r} 不在等第清單 {levels} 內")
    lo, hi = levels.index(args.floor or levels[0]), levels.index(args.cap)
    if lo > hi:
        raise SystemExit("--floor 不得高於 --cap")
    if args.min_low > len(items):
        raise SystemExit("--min-low 大於項目數")
    for _ in range(100000):
        picked = {it: levels[_rng.randrange(lo, hi + 1)] for it in items}
        if sum(1 for v in picked.values() if v in low) < args.min_low:
            continue
        if args.max_at_cap is not None and sum(1 for v in picked.values() if v == args.cap) > args.max_at_cap:
            continue
        break
    else:
        raise SystemExit("在限制內找不到可行分配，請放寬 --min-low 或 --max-at-cap")
    line = "；".join(f"{k}：{v}" for k, v in picked.items())
    return line, {"allocation": picked, "levels": levels, "cap": args.cap}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="以 JSON 輸出")
    ap.add_argument("--quiet", action="store_true", help="只輸出結果行，不附工具與時間標記")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("dice")
    p.add_argument("expr")
    p.set_defaults(fn=cmd_dice)

    p = sub.add_parser("check")
    p.add_argument("--dc", type=int, required=True, help="難度")
    p.add_argument("--mod", type=int, default=0, help="修正值")
    p.add_argument("--mode", choices=["normal", "adv", "dis"], default="normal",
                   help="normal＝1d20；adv＝順勢（2d20 取高）；dis＝逆勢（2d20 取低）")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("pick")
    p.add_argument("options", nargs="+")
    p.add_argument("--count", type=int, default=1)
    p.set_defaults(fn=cmd_pick)

    p = sub.add_parser("alloc")
    p.add_argument("--items", required=True)
    p.add_argument("--levels", default=DEFAULT_LEVELS)
    p.add_argument("--cap", required=True)
    p.add_argument("--floor")
    p.add_argument("--low", default="未涉獵,入門")
    p.add_argument("--min-low", type=int, default=0)
    p.add_argument("--max-at-cap", type=int)
    p.set_defaults(fn=cmd_alloc)

    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    line, data = args.fn(args)
    if args.json:
        data.update({"tool": "roll.py", "source": "secrets.SystemRandom", "time": stamp()})
        print(json.dumps(data, ensure_ascii=False))
    elif args.quiet:
        print(line)
    else:
        print(f"[roll.py · secrets · {stamp()}] {line}")


if __name__ == "__main__":
    main()
