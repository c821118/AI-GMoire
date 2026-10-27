#!/usr/bin/env python3
"""列出 chub/ 各檔案的 Token 明細（逐欄位、逐條目）。

用法：python .ai/scripts/tokens.py
Token 為粗估值（見 common.estimate_tokens），以「相對大小」判斷哪裡佔用最多即可。
常駐＝每回合都會送出；觸發＝只有關鍵字命中時才送出。
"""
import json
import sys

from common import ROOT, estimate_tokens, read_text, setup_console

FIELDS = ["description", "personality", "scenario", "first_mes", "mes_example",
          "system_prompt", "post_history_instructions"]


def load(rel):
    return json.loads(read_text(ROOT / rel))


def show_card(rel):
    data = load(rel)["data"]
    print(f"\n== {rel}")
    total = 0
    for field in FIELDS:
        t = estimate_tokens(data.get(field, ""))
        total += t
        if t:
            note = "（僅第 1 則訊息，之後留在歷史中）" if field == "first_mes" else ""
            print(f"  {field:<28}{t:>6}  常駐{note}")
    print(f"  {'常駐合計':<28}{total:>6}")
    entries = data.get("character_book", {}).get("entries", [])
    if entries:
        print("  -- 內嵌世界書（觸發才送出）")
        for e in sorted(entries, key=lambda x: -estimate_tokens(x["content"])):
            print(f"  {e['name']:<28}{estimate_tokens(e['content']):>6}  {'常駐' if e['constant'] else '觸發'}")
        print(f"  {'世界書合計':<28}{sum(estimate_tokens(e['content']) for e in entries):>6}")


def show_lore(rel):
    lore = load(rel)
    entries = list(lore["entries"].values())
    print(f"\n== {rel}")
    for e in sorted(entries, key=lambda x: -estimate_tokens(x["content"])):
        print(f"  {e['name']:<28}{estimate_tokens(e['content']):>6}  {'常駐' if e['constant'] else '觸發'}")
    const = sum(estimate_tokens(e["content"]) for e in entries if e["constant"])
    print(f"  {'常駐合計':<28}{const:>6}")
    print(f"  {'全部合計':<28}{sum(estimate_tokens(e['content']) for e in entries):>6}")


def main():
    setup_console()
    for rel in ("chub/general_TRPG_gm.json", "chub/hogwarts_gm_1991.json", "chub/hogwarts_gm_1890.json",
                "chub/fantasticbeasts_gm.json"):
        show_card(rel)
    for rel in ("chub/lorebooks/hogwarts_1991_lorebook.json", "chub/lorebooks/hogwarts_1890_lorebook.json",
                "chub/lorebooks/fantasticbeasts_lorebook.json"):
        show_lore(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
