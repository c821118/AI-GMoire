#!/usr/bin/env python3
"""AI-GMoire 驗證腳本：確認衍生檔與來源規則一致、結構正確、版本號統一。

用法：python .ai/scripts/validate.py
檢查項目：
  1. 衍生檔是否與 Markdown 來源同步（等同 build.py --check）
  2. JSON 結構（chara_card_v2 必填欄位、Lorebook 條目欄位、id 不重複）
  3. 來源覆蓋率：來源規則的每一行是否都出現在對應的角色卡 / Lorebook / Skill
  4. 年份一致性：1991 版不含 1890 專屬內容，反之亦然；不殘留「(外部資料)」
  5. 版本號：VERSION、角色卡、Lorebook、SKILL.md、CHANGELOG、README
  6. 唯讀來源資料夾未被修改
  7. Skill 擲骰腳本可執行，alloc 結果符合限制
  8. Token 估算（僅供參考）
有任何錯誤時結束碼為 1。
"""
import json
import re
import subprocess
import sys

import build
from common import (READ_ONLY_DIRS, ROOT, body_lines, estimate_tokens, read_text, setup_console,
                    version)

errors = []
warnings = []


def err(msg):
    errors.append(msg)
    print(f"  ✗ {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  ! {msg}")


def ok(msg):
    print(f"  ✓ {msg}")


def section(title):
    print(f"\n[{title}]")


def card_texts(card):
    """角色卡所有文字欄位（含內嵌 Lorebook 條目）串成一個字串，供覆蓋率與關鍵字檢查。"""
    data = card["data"]
    parts = [v for v in data.values() if isinstance(v, str)]
    for entry in data.get("character_book", {}).get("entries", []):
        parts.append(entry["content"])
    return "\n".join(parts)


def lore_texts(lore):
    return "\n".join(e["content"] for e in lore["entries"].values())


def check_drift(expected):
    section("1. 衍生檔與來源同步")
    stale = [p for p, text in expected.items() if not p.exists() or read_text(p) != text]
    for p in stale:
        err(f"{p.relative_to(ROOT).as_posix()} 已過期，請執行 python .ai/scripts/build.py")
    if not stale:
        ok(f"{len(expected)} 個衍生檔皆與來源一致")


def check_json_structure(cards, lores):
    start = len(errors)
    section("2. JSON 結構")
    required = ["name", "description", "personality", "scenario", "first_mes", "system_prompt",
                "post_history_instructions", "creator", "character_version", "tags", "tagline"]
    for name, card in cards.items():
        if card.get("spec") != "chara_card_v2" or card.get("spec_version") != "2.0":
            err(f"{name}: spec 應為 chara_card_v2 / 2.0")
        data = card["data"]
        for key in required:
            if not data.get(key):
                err(f"{name}: data.{key} 為空")
        entries = data.get("character_book", {}).get("entries", [])
        check_entries(name, entries)
    for name, lore in lores.items():
        entries = list(lore["entries"].values())
        if sorted(lore["entries"], key=int) != [str(i) for i in range(len(entries))]:
            err(f"{name}: entries 的鍵應為連續編號")
        check_entries(name, entries)
    # 進度總結格式改為關鍵字觸發：預告文字必須含有觸發字，否則週期終點時格式不會被載入
    for name, books in (("角色卡", {k: v["data"].get("character_book", {}).get("entries", []) for k, v in cards.items()}),
                        ("Lorebook", {k: list(v["entries"].values()) for k, v in lores.items()})):
        for year, entries in books.items():
            for e in entries:
                if e["name"] == "進度總結格式" and not any(k in build.SUMMARY_HERALD for k in e["keys"]):
                    err(f"{name} {year}: 進度總結預告文字不含任何觸發關鍵字 {e['keys']}")
    if len(errors) == start:
        ok("必填欄位、條目欄位與 id 皆正確")


def check_entries(name, entries):
    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)):
        err(f"{name}: 條目 id 重複")
    for e in entries:
        if not e["content"].strip():
            err(f"{name}: 條目「{e['name']}」內容為空")
        if not e["keys"]:
            err(f"{name}: 條目「{e['name']}」沒有關鍵字")
        if e["name"] != e["comment"]:
            err(f"{name}: 條目「{e['name']}」的 name 與 comment 不一致")


def missing_lines(source_text, haystack):
    """回傳來源中沒有逐字出現在 haystack 的行；轉換規則登記過的改寫不算遺漏。"""
    out = []
    for line in body_lines(source_text):
        if line in haystack:
            continue
        if any(old in line or line in old for _, old, _ in build.ADAPTATIONS if old):
            continue
        out.append(line)
    return out


def check_coverage(cards, lores):
    start = len(errors)
    section("3. 來源覆蓋率")
    for year in build.YEARS:
        sources = {
            "主規則": read_text(build.SRC_HOG_MAIN),
            "開局角卡": read_text(build.SRC_HOG_OPEN),
            f"檢索資料庫{year}": read_text(build.SRC_HOG_DB[year]),
        }
        targets = {
            f"角色卡 {year}": card_texts(cards[year]),
            f"Lorebook {year}": lore_texts(lores[year]),
        }
        for tname, hay in targets.items():
            for sname, text in sources.items():
                miss = missing_lines(text, hay)
                if miss:
                    err(f"{tname} 缺少「{sname}」的 {len(miss)} 行，例如：{miss[0][:40]}")
    fb_sources = {"主規則": read_text(build.SRC_FB_MAIN), "開局角卡": read_text(build.SRC_FB_OPEN),
                  "檢索資料庫": read_text(build.SRC_FB_DB)}
    for tname, hay in (("角色卡 怪獸產地", card_texts(cards["fb"])), ("Lorebook 怪獸產地", lore_texts(lores["fb"]))):
        for sname, text in fb_sources.items():
            miss = missing_lines(text, hay)
            if miss:
                err(f"{tname} 缺少「{sname}」的 {len(miss)} 行，例如：{miss[0][:40]}")
    gen_hay = card_texts(cards["general"])
    for sname, path in (("通用主規則", build.SRC_GEN_MAIN), ("通用PC角色卡", build.SRC_GEN_PC)):
        miss = missing_lines(read_text(path), gen_hay)
        if miss:
            err(f"通用角色卡缺少「{sname}」的 {len(miss)} 行，例如：{miss[0][:40]}")
    for skill, srcs in (("general_trpg_gm", [build.SRC_GEN_MAIN]), ("hogwarts_trpg_gm", [build.SRC_HOG_MAIN]),
                        ("fantasticbeasts_trpg_gm", [build.SRC_FB_MAIN])):
        text = read_text(ROOT / "skills" / skill / "SKILL.md")
        for src in srcs:
            miss = [l for l in body_lines(read_text(src)) if l not in text]
            if miss:
                err(f"skills/{skill}/SKILL.md 缺少來源 {src.name} 的 {len(miss)} 行")
    if len(errors) == start:
        ok("所有來源行皆已涵蓋（登記過的改寫除外）")
    print(f"    （已登記 {len(build.ADAPTATIONS)} 筆轉換改寫，詳見 build.py 的 adapt() 呼叫）")


def check_years(cards, lores):
    start = len(errors)
    section("4. 年份一致性與殘留外部參照")
    forbidden = {
        "1991": ["1890", "檢索資料庫1890", "一八九〇"],
        "1890": ["一九九一", "檢索資料庫1991", "與哈利波特同年份", "1945年"],
    }
    for year, words in forbidden.items():
        for label, text in ((f"角色卡 {year}", card_texts(cards[year])), (f"Lorebook {year}", lore_texts(lores[year]))):
            for w in words:
                if w in text:
                    err(f"{label} 不應出現「{w}」")
    # 1890 不含湯姆瑞斗：除了「不包含／不含湯姆瑞斗」的聲明行，不應再出現瑞斗、湯姆；人名也需統一
    for label, text in ((f"角色卡 1890", card_texts(cards["1890"])), (f"Lorebook 1890", lore_texts(lores["1890"]))):
        for line in text.split("\n"):
            if "不包含湯姆瑞斗" in line or "不含湯姆瑞斗" in line:
                continue
            for w in ("瑞斗", "湯姆", "賽巴斯欽"):
                if w in line:
                    err(f"{label} 不應出現「{w}」：{line[:40]}")
    for field in ("scenario", "tagline", "creator_notes"):
        if "湯姆瑞斗" not in cards["1890"]["data"][field] and field != "creator_notes":
            err(f"角色卡 1890 的 {field} 缺少「不包含湯姆瑞斗」註記")
    if "不包含湯姆瑞斗" not in cards["1890"]["data"]["creator_notes"]:
        err("角色卡 1890 的 creator_notes 缺少「不包含湯姆瑞斗」註記")
    # 怪獸產地統一使用台灣譯名；中國譯名或舊寫法不得出現在來源與任何衍生檔
    banned = ["格林戴華德", "格林德沃", "阿各", "戈德里克", "門鑰", "夜騏", "俯衝邪靈", "鐵甲咒", "霍格莫德",
              "德姆斯特朗", "德蘭姆", "布斯巴頓", "馬霍卡達", "卡斯特羅布魯", "普克伍吉", "普克奇", "斯庫林"]
    fb_texts = {"角色卡 怪獸產地": card_texts(cards["fb"]), "Lorebook 怪獸產地": lore_texts(lores["fb"])}
    for label, path in (("主規則", build.SRC_FB_MAIN), ("開局角卡", build.SRC_FB_OPEN), ("檢索資料庫", build.SRC_FB_DB)):
        fb_texts[f"來源 怪獸產地-{label}"] = read_text(path)
    for name in ("怪獸產地-主規則.md", "怪獸產地-開局角卡.md"):
        fb_texts[f"偽隨機判定-rules/{name}"] = read_text(build.EXPERIMENT_DIR / name)
    for label, text in fb_texts.items():
        for line in text.splitlines():
            if line.startswith("- 統一用語："):  # 檢索資料庫刻意列出被取代的舊寫法
                continue
            for w in banned:
                if w in line:
                    err(f"{label} 不應出現「{w}」：{line[:40]}")
    everything = {**{f"角色卡 {k}": card_texts(v) for k, v in cards.items()},
                  **{f"Lorebook {k}": lore_texts(v) for k, v in lores.items()}}
    for label, text in everything.items():
        # chub 版本不含任何擲骰機制（擲骰工具僅限 Skill 版）
        for w in ("(外部資料)", "擲骰", "隨機與判定方式", "roll.py"):
            if w in text:
                err(f"{label} 殘留「{w}」")
    if len(errors) == start:
        ok("各版本內容與年份相符，沒有殘留外部資料參照")


def check_versions(cards, lores):
    start = len(errors)
    section("5. 版本號")
    ver = version()
    if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        err(f"VERSION 格式錯誤：{ver!r}")
    for name, card in cards.items():
        if card["data"]["character_version"] != ver:
            err(f"角色卡 {name}: character_version 與 VERSION 不一致")
    for name, lore in lores.items():
        if f"v{ver}" not in lore.get("description", ""):
            err(f"Lorebook {name}: description 未標記 v{ver}")
    for skill in ("general_trpg_gm", "hogwarts_trpg_gm", "fantasticbeasts_trpg_gm"):
        text = read_text(ROOT / "skills" / skill / "SKILL.md")
        m = re.search(r'(?m)^  version: "([^"]*)"', text)
        if not m or m.group(1) != ver:
            err(f"skills/{skill}/SKILL.md: metadata.version 與 VERSION 不一致")
        if not re.match(r"---\nname: [\w-]+\ndescription: ", text):
            err(f"skills/{skill}/SKILL.md: frontmatter 格式異常")
    changelog = ROOT / "CHANGELOG.md"
    if changelog.exists():
        m = re.search(r"(?m)^## v?(\d+\.\d+\.\d+)", read_text(changelog))
        if not m or m.group(1) != ver:
            err(f"CHANGELOG.md 最新版本（{m.group(1) if m else '無'}）與 VERSION 不一致")
    else:
        warn("找不到 CHANGELOG.md")
    if f"v{ver}" not in read_text(ROOT / "README.md"):
        warn(f"README.md 尚未標記 v{ver}")
    if len(errors) == start:
        ok(f"版本號統一為 {ver}")


def check_readonly():
    section("6. 唯讀來源資料夾")
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", *READ_ONLY_DIRS],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        warn("無法執行 git，略過唯讀檢查")
        return
    if out.strip():
        warn("唯讀來源資料夾有未提交的變更（腳本不會寫入；若是你自行修改來源，請提交後重新產生）：\n      " + out.strip().replace("\n", "\n      "))
    else:
        ok("rules/Hogwarts_TRPG_rules/ 與 rules/general_TRPG_rules/ 與 git 紀錄一致")


def check_experiment():
    """偽隨機判定-rules（Tethered Dice 實驗版）：數值底線、與 rules 版的差異、必要章節。"""
    section("偽隨機判定-rules（實驗版）")
    start = len(errors)
    import tethered_sim
    main_path = build.EXPERIMENT_DIR / "怪獸產地-主規則.md"
    try:
        params = tethered_sim.load(main_path)
    except ValueError as e:
        err(f"判定協定表格讀取失敗：{e}")
        return
    sim_errors, info = tethered_sim.check(params)
    for line in sim_errors:
        err(line)
    for line in info:
        print(f"    {line}")
    bad = tethered_sim.deterministic_ok(params)
    if bad:
        err(f"確定性判定（期望值）與公平成功率過半不一致的格子有 {len(bad)} 個")
    text = read_text(main_path)
    for need in ("## 判定協定（Tethered Dice）", "### 骰值來源", "### 行動判定", "### 社交判定", "[判定協定]"):
        if need not in text:
            err(f"實驗版主規則缺少「{need}」")
    if "工具擲骰" in text or "roll.py" in text:
        err("實驗版是 rules（沒有工具），不應含有工具擲骰")
    # 與 rules 版主規則、開局角卡的差異應只在判定相關處，行數過多代表來源更新後沒有同步
    for name, src in (("怪獸產地-主規則.md", build.SRC_FB_MAIN), ("怪獸產地-開局角卡.md", build.SRC_FB_OPEN)):
        fork = read_text(build.EXPERIMENT_DIR / name)
        missing = [l for l in body_lines(read_text(src)) if l not in fork]
        print(f"    與 rules 版 {name} 不同的來源行：{len(missing)} 行")
        if len(missing) > 8:
            warn(f"{name} 與 rules 版差異較多（{len(missing)} 行），可能需要同步分支：{missing[0][:30]}")
    if len(errors) == start:
        ok("數值底線、必要章節與分支差異皆通過")


def check_roll_tool():
    section("7. 擲骰腳本（skills/*/scripts/roll.py）")
    start = len(errors)
    for skill_dir in build.SKILL_DIRS.values():
        script = skill_dir / "scripts" / "roll.py"
        name = skill_dir.name
        runs = [["check", "--dc", "12", "--mod", "2"], ["dice", "2d6+1"], ["pick", "甲", "乙", "丙"],
                ["alloc", "--items", "a,b,c,d,e,f,g,h,i,j,k,l", "--cap", "熟練", "--max-at-cap", "1", "--min-low", "3"]]
        for argv in runs:
            r = subprocess.run([sys.executable, "-I", str(script), "--json", *argv], capture_output=True,
                               text=True, encoding="utf-8")
            if r.returncode != 0:
                err(f"{name}: roll.py {' '.join(argv[:1])} 執行失敗：{r.stderr.strip()[:80]}")
                continue
            data = json.loads(r.stdout)
            if argv[0] == "alloc":
                vals = list(data["allocation"].values())
                if sum(v in ("未涉獵", "入門") for v in vals) < 3 or vals.count("熟練") > 1 or any(
                        data["levels"].index(v) > data["levels"].index("熟練") for v in vals):
                    err(f"{name}: roll.py alloc 的結果違反限制：{vals}")
    if len(errors) == start:
        ok("三個 Skill 的 roll.py 皆可執行，alloc 結果符合限制")


def tokens_of(text):
    return estimate_tokens(text)


def report_tokens(cards, lores):
    section("8. Token 估算（粗估，Chub 顯示值會略有出入）")
    for name, card in cards.items():
        d = card["data"]
        permanent = "".join(d[k] for k in ("description", "personality", "scenario", "first_mes",
                                            "mes_example", "system_prompt", "post_history_instructions"))
        entries = d.get("character_book", {}).get("entries", [])
        book = sum(tokens_of(e["content"]) for e in entries)
        extra = f"，內嵌世界書全部觸發約 {book}" if entries else ""
        print(f"    角色卡 {name}: 常駐約 {tokens_of(permanent)}{extra}")
    for name, lore in lores.items():
        entries = list(lore["entries"].values())
        const = sum(tokens_of(e["content"]) for e in entries if e["constant"])
        total = sum(tokens_of(e["content"]) for e in entries)
        print(f"    Lorebook {name}: 常駐約 {const}，全部約 {total}")
    main_t = tokens_of(read_text(build.SRC_GEN_MAIN))
    pc_t = tokens_of(read_text(build.SRC_GEN_PC))
    print(f"    通用規則: 主規則約 {main_t}，加 PC 角色卡約 {main_t + pc_t}")
    if main_t > 800:
        warn("通用主規則超過規格書的 800 token 目標")
    if main_t + pc_t > 1500:
        warn("通用規則（主規則＋PC 角色卡）超過規格書的 1,500 token 上限")


def main():
    setup_console()
    expected = build.generate()
    cards = {y: json.loads(read_text(ROOT / c["card"])) for y, c in build.YEARS.items()}
    cards["general"] = json.loads(read_text(ROOT / "chub" / "general_TRPG_gm.json"))
    lores = {y: json.loads(read_text(ROOT / c["lore"])) for y, c in build.YEARS.items()}
    cards["fb"] = json.loads(read_text(ROOT / build.FB_CFG["card"]))
    lores["fb"] = json.loads(read_text(ROOT / build.FB_CFG["lore"]))

    check_drift(expected)
    check_json_structure(cards, lores)
    check_coverage(cards, lores)
    check_years(cards, lores)
    check_versions(cards, lores)
    check_readonly()
    check_roll_tool()
    check_experiment()
    report_tokens(cards, lores)

    print(f"\n結果：{len(errors)} 個錯誤，{len(warnings)} 個警告。")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
