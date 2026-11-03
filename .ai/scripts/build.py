#!/usr/bin/env python3
"""AI-GMoire 轉置與比對腳本。

以 `rules/` 底下各規則資料夾的 Markdown 為單一真相源，產生：
  - chub/*.json                      SillyTavern / Chub.ai 角色卡（chara_card_v2）
  - chub/lorebooks/*.json            搭配通用規則使用的 Lorebook
  - skills/*/references/*            Skill 的補充資料（逐字複製來源）
  - skills/*/scripts/roll.py         Skill 共用的擲骰腳本（來源：.ai/skill-tools/）
  - skills/*/SKILL.md                僅更新 `gmoire:sync` 標記區塊與 frontmatter 版本號，
                                     標記區塊以外（例如「工具使用」）為手寫內容，不會被改動

用法：
  python .ai/scripts/build.py            重新產生所有衍生檔
  python .ai/scripts/build.py --check    只比對，有過期檔案時以結束碼 1 回報（不寫檔）
  python .ai/scripts/build.py --diff     比對並顯示差異
"""
import argparse
import difflib
import json
import re
import sys

from common import (ROOT, assert_in_readonly, parse_markdown, read_text, setup_console,
                    version, write_text)

RULES = ROOT / "rules"
HOG = RULES / "Hogwarts_TRPG_rules"
GEN = RULES / "general_TRPG_rules"
SRC_HOG_MAIN = HOG / "霍格華茲-主規則.md"
SRC_HOG_OPEN = HOG / "霍格華茲-開局角卡.md"
SRC_HOG_EXT = HOG / "霍格華茲-c821118擴充資料庫.md"
SRC_HOG_DB = {y: HOG / f"霍格華茲-檢索資料庫{y}.md" for y in ("1991", "1890")}
SRC_GEN_MAIN = GEN / "AI-TRPG-主規則.md"
SRC_GEN_PC = GEN / "AI-TRPG-PC角色卡.md"
FB = RULES / "FantasticBeasts_TRPG_rules"
SRC_FB_MAIN = FB / "怪獸產地-主規則.md"
SRC_FB_OPEN = FB / "怪獸產地-開局角卡.md"
SRC_FB_DB = FB / "怪獸產地-檢索資料庫.md"
# 偽隨機判定（Tethered Dice）實驗版規則，與 rules/ 同層級（TetheredDice-rules/ 下以怪獸產地為子資料夾）
EXPERIMENT_DIR = ROOT / "TetheredDice-rules" / "fantasticbeasts_trpg_gm"
# Skill 共用的工具與協定（單一來源，會複製到每個 Skill 的 scripts/ 與 references/）
SKILL_TOOLS = ROOT / ".ai" / "skill-tools"

REPO_URL = "https://github.com/c821118/AI-GMoire"
LICENSE_NAME = "MNCL-FW 1.0"

# 轉換時對來源文字做的改寫都登記在這裡，validate.py 以此判斷「來源行未逐字出現」是否合理。
ADAPTATIONS = []


def adapt(text, pairs, label):
    """逐一套用 (舊, 新) 改寫；來源若已不含舊字串就中止，避免來源改版後悄悄漏轉。"""
    for old, new in pairs:
        if old not in text:
            raise ValueError(f"[{label}] 來源已無此文字，請更新 build.py 的轉換規則：{old!r}")
        ADAPTATIONS.append((label, old, new))
        text = text.replace(old, new)
    return text


def drop_lines(text, prefixes, label):
    """移除以指定前綴開頭的整行，並登記為刻意省略。chub 版本不含任何擲骰機制，用它去掉相關欄位與說明。"""
    lines = text.split("\n")
    for prefix in prefixes:
        hits = [l for l in lines if l.startswith(prefix)]
        if len(hits) != 1:
            raise ValueError(f"[{label}] 找不到唯一以 {prefix!r} 開頭的行（找到 {len(hits)} 行）")
        ADAPTATIONS.append((label, hits[0], ""))
        lines.remove(hits[0])
    return "\n".join(lines)


# chub（SillyTavern）的擲骰工具由玩家自行安裝，AI 無法使用，所以 chub 版本不含擲骰機制
NO_DICE_BULLET = "- 【隨機與判定方式】"
NO_DICE_FIELD = "    * 隨機與判定方式："


def fence_inner(body):
    """取出程式碼區塊內的文字（去掉前後的 ``` 行）。"""
    lines = body.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


# ====================================================================== 霍格華茲

YEARS = {
    "1991": {
        "card": "chub/hogwarts_gm_1991.json",
        "lore": "chub/lorebooks/hogwarts_1991_lorebook.json",
        "name": "霍格華茲1991 TRPG AI-GMoire",
        "tagline": "GM主持1991年代霍格華茲TRPG",
        "scenario": "霍格華茲魔法與巫術學院，1991年。與哈利波特同年代入學，體驗魔法世界的冒險、友誼與成長。",
        "book_name": "霍格華茲檢索資料庫1991",
        "book_desc": "霍格華茲 TRPG 1991年世界觀資料庫",
        "lore_name": "霍格華茲1991 世界書",
        "era_label": "1991年代",
    },
    "1890": {
        "card": "chub/hogwarts_gm_1890.json",
        "lore": "chub/lorebooks/hogwarts_1890_lorebook.json",
        "name": "霍格華茲1890 TRPG AI-GMoire",
        "tagline": "GM主持1890年代霍格華茲TRPG（不含湯姆瑞斗）",
        "scenario": "霍格華茲魔法與巫術學院，1890年代。與《霍格華茲的傳承》同年代，探索古代魔法的秘密。本卡不包含湯姆瑞斗。",
        "book_name": "霍格華茲檢索資料庫1890",
        "book_desc": "霍格華茲 TRPG 1890年世界觀資料庫",
        "lore_name": "霍格華茲1890 世界書",
        "era_label": "1890年代，不包含湯姆瑞斗",
    },
}

HOG_PERSONALITY = ("嚴守規則的霍格華茲文字模擬器GM。依循原作世界觀編織情節，以小說體敘事，"
                   "多用陰冷、暗處、光影交錯的白描，烘托霍格華茲神祕氛圍。尊重玩家選擇，絕不代替PC做決定。")
HOG_TAGS = ["TRPG", "RPG", "Hogwarts", "Harry Potter", "GM", "霍格華茲"]

# 進度總結的匯出格式改為關鍵字觸發後，需確保週期終點時格式一定已載入：
# GM 在匯出前一回合先預告，預告文字本身（含「進度總結」）會讓下一回合的掃描命中條目。
SUMMARY_HERALD = ("- 預告機制：預計於下一回合匯出進度總結時，GM 須在本回合的【可選行動】之前加註"
                  "「（下一回合將匯出進度總結）」，以便載入世界書條目「進度總結格式」。")

MODULE_POINTER = {
    "1991": ("（轉學生與高年級開局機制、學生湯姆瑞斗穿越兩個擴充模組的詳細規則，"
             "由世界書於對應情境觸發時提供，觸發後須嚴格遵守。）"),
    "1890": ("（轉學生與高年級開局機制的詳細規則，由世界書於對應情境觸發時提供，觸發後須嚴格遵守。"
             "1890年代版不包含湯姆瑞斗，亦無學生湯姆瑞斗穿越模組。）"),
}

# 世界書條目的觸發關鍵字。keys 需出現在最近 scan_depth 則訊息中才會注入。
KEYS = {
    # v1.1.0 收窄：移除「學院」「魔杖」「探索」「靈活」等在敘事中幾乎每回合都會出現的泛用詞，
    # 魔杖相關條目改由「魔杖店」「挑選魔杖」或材質名稱觸發。
    "學院分類": ["分類帽", "葛來分多", "史萊哲林", "赫夫帕夫", "雷文克勞", "學院分"],
    "魔法學術架構": ["課程", "科目"],
    "課表規則": ["課表", "選修", "必修", "高階科目"],
    "魔杖芯": ["杖芯", "鳳凰羽毛", "龍的心弦", "獨角獸毛", "蛇怪角", "雷鳥尾羽", "魔杖店", "挑選魔杖"],
    "魔杖木材": ["木材", "冬青木", "紫杉木", "接骨木", "山楂木", "魔杖店", "挑選魔杖"],
    "魔杖彈性": ["魔杖彈性", "柔韌", "毫無彈性", "魔杖店", "挑選魔杖"],
    "地理風險": ["夜遊", "宵禁", "地窖", "塔樓", "禁忌走廊", "萬應室", "禁書區"],
    "咒語階級": ["咒語", "魔藥", "護法", "不赦咒", "阿瓦達"],
    "古代魔法": ["古代魔法", "地圖室", "共鳴"],
    "物品限制": ["飛天掃帚", "校服", "活米村"],
    "主要學生": ["賽巴斯蒂安", "薩洛", "奧米尼斯", "剛特", "安妮", "納采", "歐奈",
                 "帕比", "斯威廷", "阿米特", "塔卡爾"],
    "教職員": ["斐尼亞", "耐吉", "布萊克", "瑪蒂達", "衛斯理", "艾利沙爾", "費格", "米拉貝爾",
               "加里克", "伊索", "夏普", "黛娜", "赫卡特", "亞伯拉罕", "羅南", "瑪迪哈", "所羅門"],
    "反派": ["蘭洛克", "維克多", "羅克五"],
    "湯姆瑞斗里程碑": ["分靈體", "反噬", "黑暗里程碑", "日記本"],
    "生死豁免機制": ["死亡", "危機", "救贖", "即將死亡"],
    "轉學生開局": ["轉學", "五年級", "高年級"],
    # 「佛地魔」在 1991 年代的原作劇情中隨處可見，不當作模組觸發字
    "湯姆瑞斗規則": ["瑞斗", "湯姆", "世界線", "穿越", "反噬"],
    # 進度總結格式：只在 PC 提出或 GM 預告時載入，「進度」「總結」這類泛用詞不再觸發
    "進度總結格式": ["進度總結", "總結進度", "匯出進度", "匯出總結", "備份"],
    # 開局角卡只在開局用到：PC 填寫的角色卡必含這些欄位標題，之後離開掃描範圍就不再注入
    "開局角卡": ["故事開始年份", "入學年級", "角色創建", "確認角色卡"],
    # 搭配通用規則時，PC 填的是通用角色卡，欄位標題為「TRPG主題」
    "開局角卡_lore": ["TRPG主題", "故事開始年份", "入學年級", "角色創建", "確認角色卡"],
    "_constant": ["霍格華茲", "魔法世界"],
}

# (條目名稱, 來源章節標題, 子章節標題或 None, 是否保留標題, 適用年份)
DB_SPECS = [
    ("學院分類", "學院特質與分類帽權重", None, False, ("1991", "1890")),
    ("魔法學術架構", "魔法學術架構", None, False, ("1991", "1890")),
    ("課表規則", "霍格華茲科目與課表", None, False, ("1991", "1890")),
    ("魔杖芯", "魔杖學與巫師特質配對", "魔杖芯", True, ("1991", "1890")),
    ("魔杖木材", "魔杖學與巫師特質配對", "主要木材", True, ("1991", "1890")),
    ("魔杖彈性", "魔杖學與巫師特質配對", "魔杖彈性與靈活度", True, ("1991", "1890")),
    ("地理風險", "地理結構與風險矩陣", None, False, ("1991", "1890")),
    ("咒語階級", "魔法與魔藥階級限制", None, False, ("1991",)),
    ("咒語階級", "魔法、魔藥階級限制與古代魔法", None, False, ("1890",)),
    ("古代魔法", "古代魔法天賦與特殊地標", None, False, ("1890",)),
    ("物品限制", "物品與生活限制", None, False, ("1890",)),
    ("主要學生", "1890年代核心人物", "1. 主要學生與夥伴", True, ("1890",)),
    ("教職員", "1890年代核心人物", "2. 教職員與守護者", True, ("1890",)),
    ("反派", "1890年代核心人物", "3. 反派與敵對勢力", True, ("1890",)),
    ("湯姆瑞斗里程碑", "學生湯姆瑞斗模組資料庫", None, True, ("1991",)),
]


def db_entries(year):
    """檢索資料庫 → [(名稱, 內容)]。魔杖三條目會各自帶上父章節的說明句。"""
    text = read_text(SRC_HOG_DB[year])
    if year == "1890":
        # 1890 沒有湯姆瑞斗；來源中「賽巴斯欽」與「賽巴斯蒂安」並存，統一為後者
        text = adapt(text, [("（如瑞斗、薩洛）", "（如薩洛）"), ("賽巴斯欽", "賽巴斯蒂安")], year)
    db = parse_markdown(text)
    out = []
    for name, title, child, heading, years in DB_SPECS:
        if year not in years:
            continue
        node = db.get(title)
        if child is None:
            content = node.render(heading=heading)
        else:
            sub = node.get(child)
            content = (node.body + "\n\n" if node.body else "") + sub.render(heading=heading)
        out.append((name, content))
    return out


def summary_parts(main):
    """進度總結拆成兩段：觸發時機（常駐，很短）與後台演算＋匯出格式（約 800 token，改由世界書條目按需載入）。"""
    summary_node = main.get("進度總結匯出")
    trigger_node = summary_node.get("觸發與生成時機")
    summary_trigger = "# 進度總結匯出\n\n" + trigger_node.render() + "\n" + SUMMARY_HERALD
    summary = "\n\n".join(c.render() for c in summary_node.children if c is not trigger_node)
    return summary_trigger, summary


def hog_parts(year, target):
    """霍格華茲主規則與開局角卡拆成可重組的片段。target 為 'card' 或 'lore'。"""
    main = parse_markdown(read_text(SRC_HOG_MAIN))
    label = f"{year}/{target}"

    tier_pairs = [("[霍格華茲-檢索資料庫1991]或[霍格華茲-檢索資料庫1890]", f"[霍格華茲-檢索資料庫{year}]")]
    if year == "1890":
        tier_pairs.append(("、[學生湯姆瑞斗穿越]。", "。"))
    tier = adapt(main.get("權限級聯與優先級").render(), tier_pairs, label)
    sim = main.get("模擬器運作").render()

    death = main.get("生死豁免機制").render()
    if year == "1991":
        transfer_pairs = [("若同時以 1890 年開局，將《霍格華茲的傳承》及[霍格華茲-檢索資料庫1890]列為世界觀主要參考文本。", "")]
    else:
        transfer_pairs = [("若同時以 1890 年開局，將", "本卡以 1890 年開局，將")]
    transfer = adapt(main.get("轉學生與高年級開局機制").render(), transfer_pairs, label)
    tom = main.get("學生湯姆瑞斗穿越").render()
    if year == "1890":  # 1890 年代湯姆瑞斗尚未出生，整個模組不納入；登記為刻意省略供覆蓋率檢查略過
        ADAPTATIONS.append((label, tom, ""))
        tom = None

    guide_pairs = [
        ("[(外部資料)霍格華茲-開局角卡]", "[世界書：開局角卡]"),
        ("無法查找到該外部資料", "無法查找到該世界書條目"),
        ("請求 PC 載入該外部資料", "請求 PC 啟用該世界書條目"),
    ]
    if target == "card":
        guide_pairs.append(("2. 先直接輸出其[空白角色卡]供 PC 填寫。",
                            "2. 開場白已輸出[空白角色卡]供 PC 填寫，不需重複輸出。"))
    guide = adapt(main.get("遊戲開局引導").render(), guide_pairs, label)

    filt = main.get("GM 文本渲染過濾器").render(children=False)
    recap = main.get("每一局後台思維演算").render()
    summary_trigger, summary = summary_parts(main)
    if year == "1890":
        recap = adapt(recap, [("一九九一年", "一八九〇年")], label)
        summary = adapt(summary, [
            ("一九九一年", "一八九〇年"),
            ("\n    * （若啟用湯姆瑞斗模組，須額外紀錄當前的 [世界線偏移值]、[反噬程度] 與世界動盪簡介）", ""),
        ], label)

    # --- 開局角卡
    op = parse_markdown(read_text(SRC_HOG_OPEN)).get("霍格華茲-開局角卡")
    intro_pairs = [("\n- 如果 PC 選擇「1890年」開局，請提醒 PC 載入[霍格華茲-檢索資料庫1890]檔案。", "")]
    if year == "1890":
        intro_pairs.append(("[11歲夏天、與哈利波特同年入學（1991年）]", "[11歲夏天、於1890年代入學]"))
        intro_pairs.append(("\n- 如果 PC 選擇開啟擴充模組[學生湯姆瑞斗穿越]，請在開局時再次檢查"
                            "[故事開始年份]、[玩家入學年級]及[湯姆瑞斗的學年]。", ""))
    if target == "card":
        intro_pairs.append(("- 正式開始前，請先直接輸出[(外部資料)空白角色卡]讓 PC 填寫，不需隨意增加或減少說明。",
                            "- 開場白已輸出[空白角色卡]，不需重複輸出，也不需隨意增加或減少說明。"))
    else:
        intro_pairs.append(("[(外部資料)空白角色卡]", "[空白角色卡]"))
    intro = drop_lines(adapt(op.body, intro_pairs, label), [NO_DICE_BULLET], label)

    blank_node = op.get("空白角色卡")
    if year == "1991":
        blank_pairs = [("／1890年（與霍格華茲的傳承同年份）", "")]
    else:
        blank_pairs = [
            ("(預設)1991年（與哈利波特同年份）／1890年（與霍格華茲的傳承同年份）",
             "(預設)1890年（與霍格華茲的傳承同年份）"),
            ("(預設)1945年已發生鄧不利多與葛林戴華德的對決，使得善惡值回歸「善惡均衡」，"
             "1980年已發生佛地魔組成死食人軍團發動襲擊，世界局勢逐漸墮入「陰影籠罩」。",
             "(預設)依循《霍格華茲的傳承》原作局勢（蘭洛克的妖精叛軍與維克多·羅克五的黑巫師勢力）。"),
            ("    * 擴充模組-學生湯姆瑞斗穿越：開啟／(預設)不開啟\n"
             "        * 擴充模組-如果開啟學生湯姆瑞斗穿越，請指定湯姆·瑞斗的學年："
             "(預設)與玩家同一屆／比玩家高一屆的學長／比玩家低一屆的學弟",
             "    * 擴充模組：1890年代版不包含湯姆瑞斗（無學生湯姆瑞斗穿越模組）"),
        ]
    blank_inner = drop_lines(adapt(fence_inner(blank_node.body), blank_pairs, label), [NO_DICE_FIELD], label)
    blank_render = "## 空白角色卡\n```\n" + blank_inner + "\n```"
    routes = op.get("PC 確認角色卡後，導入以下初始劇情").render()
    opening_card = intro + "\n\n" + routes
    opening_lore = intro + "\n\n" + blank_render + "\n\n" + routes

    roles = main.get("系統角色定義與權限")
    return {
        "description": roles.body,
        "roles": roles.render(children=False),
        "tier": tier, "sim": sim, "death": death, "transfer": transfer, "tom": tom,
        "guide": guide, "filter": filt, "recap": recap,
        "summary_trigger": summary_trigger, "summary": summary,
        "first_mes": blank_inner, "opening_card": opening_card, "opening_lore": opening_lore,
    }


def book_entry(idx, name, keys, content, constant=False, priority=10):
    return {
        "keys": keys, "content": content, "enabled": True, "insertion_order": 100,
        "case_sensitive": False, "priority": priority, "id": idx, "comment": name,
        "selective": False, "secondary_keys": [], "constant": constant,
        "position": "before_char", "selectiveLogic": 0, "extensions": {}, "name": name,
    }


def build_entries(specs):
    """specs: [(名稱, 內容, 關鍵字, constant, priority)] → 依序編號的條目清單。"""
    return [book_entry(i, n, k, c, const, p) for i, (n, c, k, const, p) in enumerate(specs)]


def creator_notes(label):
    return (f"{label}。詳見 {REPO_URL}\n"
            f"版本 v{version()}｜授權 {LICENSE_NAME}（非商業、相同方式分享），詳見專案 LICENSE。")


def hog_card(year):
    cfg = YEARS[year]
    p = hog_parts(year, "card")
    system_prompt = "\n\n".join([
        p["tier"], p["sim"],
        "# 擴充模組\n\n" + p["death"] + "\n\n" + MODULE_POINTER[year],
        p["guide"], p["filter"],
    ])
    specs = [(n, c, KEYS[n], False, 10) for n, c in db_entries(year)]
    specs.append(("轉學生開局", p["transfer"], KEYS["轉學生開局"], False, 5))
    if p["tom"]:
        specs.append(("湯姆瑞斗規則", p["tom"], KEYS["湯姆瑞斗規則"], False, 5))
    specs.append(("進度總結格式", p["summary"], KEYS["進度總結格式"], False, 6))
    specs.append(("開局角卡", p["opening_card"], KEYS["開局角卡"], False, 6))
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": cfg["name"],
            "description": p["description"],
            "personality": HOG_PERSONALITY,
            "scenario": cfg["scenario"],
            "first_mes": p["first_mes"],
            "mes_example": "",
            "creator_notes": creator_notes(f"霍格華茲 TRPG 遊戲主持人角色卡（{cfg['era_label']}）"),
            "system_prompt": system_prompt,
            "post_history_instructions": p["recap"] + "\n\n" + p["summary_trigger"],
            "alternate_greetings": [],
            "character_book": {
                "name": cfg["book_name"],
                "description": cfg["book_desc"],
                "scan_depth": 5,
                "token_budget": 2000,
                "recursive_scanning": False,
                "extensions": {},
                "entries": build_entries(specs),
            },
            "tags": HOG_TAGS,
            "creator": "c821118",
            "character_version": version(),
            "extensions": {},
            "tagline": cfg["tagline"],
        },
    }


def hog_lorebook(year):
    cfg = YEARS[year]
    p = hog_parts(year, "lore")
    c = KEYS["_constant"]
    specs = [(n, content, KEYS[n], False, 10) for n, content in db_entries(year)]
    specs += [
        ("霍格華茲核心規則", "\n\n".join([p["roles"], p["tier"], p["sim"], p["guide"]]), c, True, 1),
        ("霍格華茲輸出格式", p["recap"] + "\n\n" + p["summary_trigger"], c, True, 2),
        ("霍格華茲文本過濾器", p["filter"], c, True, 3),
        ("生死豁免機制", p["death"], KEYS["生死豁免機制"], True, 4),
        ("轉學生開局", p["transfer"], KEYS["轉學生開局"], False, 5),
        ("進度總結格式", p["summary"], KEYS["進度總結格式"], False, 6),
        ("開局角卡", p["opening_lore"], KEYS["開局角卡_lore"], False, 6),
    ]
    if p["tom"]:
        specs.insert(-2, ("湯姆瑞斗規則", p["tom"], KEYS["湯姆瑞斗規則"], False, 5))
    entries = build_entries(specs)
    return {
        "name": cfg["lore_name"],
        "description": (f"{cfg['book_desc']}（搭配通用規則使用）｜AI-GMoire v{version()}｜"
                        f"授權 {LICENSE_NAME}｜{REPO_URL}"),
        "entries": {str(e["id"]): e for e in entries},
    }


# ====================================================================== 怪獸產地

FB_CFG = {
    "card": "chub/fantasticbeasts_gm.json",
    "lore": "chub/lorebooks/fantasticbeasts_lorebook.json",
    "name": "怪獸產地 TRPG AI-GMoire",
    "tagline": "GM主持《怪獸與牠們的產地》系列的成年巫師職場TRPG",
    "scenario": ("1926 至 1932 年，紐約、巴黎、倫敦與歐亞各地。你是已從魔法學校畢業的成年巫師，"
                 "在職場與日常中，與葛林戴華德的黑巫師集團交錯碰撞。"),
    "book_name": "怪獸產地檢索資料庫",
    "book_desc": "怪獸產地 TRPG 世界觀資料庫",
    "lore_name": "怪獸產地 世界書",
    "era_label": "1926 至 1932 年",
}
FB_PERSONALITY = ("嚴守規則的怪獸產地文字模擬器GM。依循電影三部曲的世界觀編織情節，以小說體敘事，"
                  "多用爵士年代都會的明暗、禁酒令下的煙霧與低語，烘托黑巫師陰影逼近的不安。"
                  "尊重玩家選擇，絕不代替PC做決定。")
FB_TAGS = ["TRPG", "RPG", "Fantastic Beasts", "Harry Potter", "GM", "怪獸產地"]

# 世界書條目的關鍵字。人名類條目另由 bold_names() 從資料表自動擷取。
FB_KEYS = {
    "譯名與用語": ["譯名"],  # 常駐條目，關鍵字僅為結構完整
    "國際魔法機構與勢力": ["魔法國會", "魔法部", "國際巫師聯合會", "MACUSA", "古靈閣", "聖蒙果", "正氣師"],
    "葛林戴華德集團": ["葛林戴華德", "黑巫師", "死亡聖器", "藍色火焰", "集團", "追隨者"],
    "地點-1926": ["紐約", "盲豬", "新賽倫", "伍爾沃斯"],
    "地點-1927": ["巴黎", "倫敦", "法國魔法部", "阿卡納斯", "馬戲團", "紐蒙迦德"],
    "地點-1932": ["桂林", "活米村", "柏林", "不丹", "厄克斯塔格"],
    "魔法學校與畢業成績": ["畢業", "學校", "伊法魔尼", "德姆蘭", "波巴洞", "瓦加度", "卡斯特羅布舍", "マホウトコロ", "魔法所"],
    "魔法專業科目": ["專業", "科目", "黑魔法"],
    "魔杖學": ["魔杖：", "魔杖芯", "魔杖木材", "魔杖彈性", "杖芯", "魔杖店", "挑選魔杖", "奧利凡德",
               "鳳凰羽毛", "龍的心弦", "獨角獸毛", "蛇怪角", "騎士墜鬼馬尾毛", "長角水蛇角", "雷鳥尾羽",
               "迷拉頭髮", "冬青木", "紫杉木", "接骨木", "山楂木", "黑胡桃木", "黑檀木"],
    "職業表": ["職業", "就職", "年資", "初次衝突", "鉤子"],
    "魔法與咒語階級": ["咒語", "魔藥", "不赦咒", "索命咒", "酷刑咒", "蠻橫咒", "護法", "破心護",
                       "開鎖咒", "招魂術", "不可破誓咒", "血盟"],
    "魔法暴露與保密法規": ["保密", "遺忘咒", "魔杖許可", "旅行限制", "暴露", "通婚", "結交禁令", "獵巫"],
    "魔法生物": ["奇獸", "魔法生物"],
    "魔法物品與生活限制": ["皮箱", "銀蛋殼", "港口鑰", "血盟墜瓶", "愛情魔咒", "禁酒令", "貨幣", "加隆"],
    "神聖二十八姓": ["神聖二十八姓", "姓氏", "純血"],
    "進度總結格式": ["進度總結", "總結進度", "匯出進度", "匯出總結", "備份"],
    "開局角卡": ["故事開始年份", "畢業學校", "畢業成績", "角色創建", "確認角色卡"],
    "開局角卡_lore": ["TRPG主題", "故事開始年份", "畢業學校", "畢業成績", "角色創建", "確認角色卡"],
    "_constant": ["怪獸產地", "魔法世界"],
}
FB_ERA_KEYS = {"1926": ["1926", "一九二六"], "1927": ["1927", "一九二七"], "1932": ["1932", "一九三二"]}


def bold_names(text):
    """擷取資料表中的粗體人名，拆成全名與各段（長度 2 以上）作為關鍵字。"""
    keys = []
    for m in re.finditer(r"\*\*(.+?)\*\*", text):
        for part in m.group(1).split("／"):
            pieces = [p.strip("「」\"“” ") for p in part.split("・")]
            for k in [part.strip("「」\"“” ")] + pieces:
                if len(k) >= 2 and k not in keys:
                    keys.append(k)
    return keys


def first_column(text, split=False):
    """擷取 Markdown 資料表第一欄（略過表頭），去掉括號與標記。"""
    out = []
    for line in text.split("\n"):
        if not line.startswith("|") or line.startswith("| :--") or line.startswith("| 編號"):
            continue
        cell = line.split("|")[1].strip()
        cell = re.sub(r"[（(].*?[）)]|【.*?】|\*\*", "", cell).strip()
        for k in (cell.split("、") if split else [cell]):
            k = k.strip()
            if 2 <= len(k) <= 8 and k not in out and k not in ("人物姓名", "地點", "生物", "機構", "職業", "學校"):
                out.append(k)
    return out


def fb_anchor_entries(db):
    """主線錨點時間線依年代拆成三個條目，只有對應年代的敘事才會載入。"""
    node = db.get("原作時間線與主線錨點")
    lines = node.body.split("\n")
    head = [l for l in lines if not l.startswith("|")]
    table = [l for l in lines if l.startswith("|")]
    header, rows = table[:2], table[2:]
    groups = {"1926": [], "1927": [], "1932": []}
    for row in rows:
        tag = row.split("|")[1].strip()[0]  # A / B / C / D
        groups[{"A": "1926", "B": "1927", "C": "1932", "D": "1932"}[tag]].append(row)
    out = []
    for era, era_rows in groups.items():
        content = ("## 原作時間線與主線錨點\n" + "\n".join(head).strip() + "\n\n" + "\n".join(header + era_rows))
        out.append((f"主線錨點-{era}", content, FB_ERA_KEYS[era]))
    return out


def fb_db_entries():
    """怪獸產地檢索資料庫 → [(名稱, 內容, 關鍵字)]。"""
    db = parse_markdown(read_text(SRC_FB_DB))
    K = FB_KEYS

    def sec(title, name=None, extra=None, heading=True):
        node = db.get(title)
        text = node.render(heading=heading)
        return (name or title, text, (extra or []) + K.get(name or title, []))

    people = {y: db.get(f"{y} 年核心人物").render() for y in ("1926", "1927", "1932")}
    loc = db.get("地點")
    locs = {
        "1926": loc.get("1926 年・紐約").render(),
        "1927": loc.get("1927 年・巴黎與倫敦").render(),
        "1932": loc.get("1932 年・歐亞").render(),
    }
    group = db.get("葛林戴華德集團")
    out = [sec("譯名與用語說明", "譯名與用語")]
    out += fb_anchor_entries(db)
    out += [
        sec("國際魔法機構與勢力"),
        ("葛林戴華德集團", group.render(), K["葛林戴華德集團"] + bold_names(group.render())),
    ]
    seen = set()  # 不同年代共用的地名（如紐約）只算在最早出現的年代，避免跨年代誤觸發
    for era in ("1926", "1927", "1932"):
        keys = [k for k in K[f"地點-{era}"] + first_column(locs[era]) if k not in seen]
        seen.update(keys)
        out.append((f"地點-{era}", "## 地點\n" + locs[era], keys))
    out += [
        sec("魔法學校與畢業成績"),
        sec("魔法專業科目"),
        sec("魔杖學與巫師特質配對", "魔杖學"),
        sec("職業表"),
        sec("魔法與咒語階級"),
        sec("魔法暴露與保密法規"),
        ("魔法生物", db.get("魔法生物").render(), K["魔法生物"] + [k for k in first_column(db.get("魔法生物").render()) if k != "鳳凰"]),  # 鳳凰會誤觸杖芯「鳳凰羽毛」
        sec("魔法物品與生活限制"),
        sec("神聖二十八姓"),
    ]
    for era in ("1926", "1927", "1932"):
        out.append((f"{era} 年核心人物", people[era], FB_ERA_KEYS[era] + bold_names(people[era])))
    return out


def fb_parts(target):
    """怪獸產地主規則與開局角卡拆成可重組的片段。target 為 'card' 或 'lore'。"""
    main = parse_markdown(read_text(SRC_FB_MAIN))
    label = f"fb/{target}"
    tier = main.get("權限級聯與優先級").render()
    sim = main.get("模擬器運作").render()
    # 初次衝突只在第一回合用到，隨開局角卡條目載入，不放進每回合都送的欄位
    modules = "\n\n".join(main.get(t).render() for t in ("生死豁免機制", "主線錨點機制"))
    first_conflict = main.get("初次衝突機制").render()

    guide_pairs = [
        ("[(外部資料)怪獸產地-開局角卡]", "[世界書：開局角卡]"),
        ("無法查找到該外部資料", "無法查找到該世界書條目"),
        ("請求 PC 載入該外部資料", "請求 PC 啟用該世界書條目"),
    ]
    if target == "card":
        guide_pairs.append(("2. 先直接輸出其[空白角色卡]供 PC 填寫。",
                            "2. 開場白已輸出[空白角色卡]供 PC 填寫，不需重複輸出。"))
    guide = adapt(main.get("遊戲開局引導").render(), guide_pairs, label)

    filt = main.get("GM 文本渲染過濾器").render(children=False)
    recap = main.get("每一局後台思維演算").render()
    summary_trigger, summary = summary_parts(main)

    op = parse_markdown(read_text(SRC_FB_OPEN)).get("怪獸產地-開局角卡")
    if target == "card":
        intro_pairs = [("- 正式開始前，請先直接輸出[(外部資料)空白角色卡]讓 PC 填寫，不需隨意增加或減少說明。",
                        "- 開場白已輸出[空白角色卡]，不需重複輸出，也不需隨意增加或減少說明。")]
    else:
        intro_pairs = [("[(外部資料)空白角色卡]", "[空白角色卡]")]
    intro_pairs.append(("，結果依[隨機與判定方式]取得：工具擲骰時由工具抽取，玩家自行擲骰時由 PC 提供數字，確定性判定時由 GM 依職業與性格配置並向 PC 說明依據。",
                        "，並向 PC 說明配置依據。"))
    intro = drop_lines(adapt(op.body, intro_pairs, label), [NO_DICE_BULLET], label)
    blank_inner = drop_lines(fence_inner(op.get("空白角色卡").body), [NO_DICE_FIELD], label)
    blank_render = "## 空白角色卡\n```\n" + blank_inner + "\n```"
    routes = op.get("PC 確認角色卡後，導入以下初始劇情").render()

    roles = main.get("系統角色定義與權限")
    return {
        "description": roles.body, "roles": roles.render(children=False),
        "tier": tier, "sim": sim, "modules": modules, "guide": guide, "filter": filt, "recap": recap,
        "summary_trigger": summary_trigger, "summary": summary,
        "first_mes": blank_inner,
        "opening_card": intro + "\n\n" + first_conflict + "\n\n" + routes,
        "opening_lore": intro + "\n\n" + blank_render + "\n\n" + first_conflict + "\n\n" + routes,
    }


def fb_card():
    cfg = FB_CFG
    p = fb_parts("card")
    system_prompt = "\n\n".join([p["tier"], p["sim"], "# 擴充模組\n\n" + p["modules"], p["guide"], p["filter"]])
    specs = [(n, c, k, n == "譯名與用語", 1 if n == "譯名與用語" else 10) for n, c, k in fb_db_entries()]
    specs.append(("進度總結格式", p["summary"], FB_KEYS["進度總結格式"], False, 6))
    specs.append(("開局角卡", p["opening_card"], FB_KEYS["開局角卡"], False, 6))
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": cfg["name"],
            "description": p["description"],
            "personality": FB_PERSONALITY,
            "scenario": cfg["scenario"],
            "first_mes": p["first_mes"],
            "mes_example": "",
            "creator_notes": creator_notes(f"怪獸產地 TRPG 遊戲主持人角色卡（{cfg['era_label']}）"),
            "system_prompt": system_prompt,
            "post_history_instructions": p["recap"] + "\n\n" + p["summary_trigger"],
            "alternate_greetings": [],
            "character_book": {
                "name": cfg["book_name"],
                "description": cfg["book_desc"],
                "scan_depth": 5,
                "token_budget": 2500,
                "recursive_scanning": False,
                "extensions": {},
                "entries": build_entries(specs),
            },
            "tags": FB_TAGS,
            "creator": "c821118",
            "character_version": version(),
            "extensions": {},
            "tagline": cfg["tagline"],
        },
    }


def fb_lorebook():
    cfg = FB_CFG
    p = fb_parts("lore")
    c = FB_KEYS["_constant"]
    specs = [(n, content, k, n == "譯名與用語", 1 if n == "譯名與用語" else 10) for n, content, k in fb_db_entries()]
    specs += [
        ("怪獸產地核心規則", "\n\n".join([p["roles"], p["tier"], p["sim"], p["guide"]]), c, True, 1),
        ("怪獸產地輸出格式", p["recap"] + "\n\n" + p["summary_trigger"], c, True, 2),
        ("怪獸產地文本過濾器", p["filter"], c, True, 3),
        ("怪獸產地擴充模組", p["modules"], c, True, 4),
        ("進度總結格式", p["summary"], FB_KEYS["進度總結格式"], False, 6),
        ("開局角卡", p["opening_lore"], FB_KEYS["開局角卡_lore"], False, 6),
    ]
    entries = build_entries(specs)
    return {
        "name": cfg["lore_name"],
        "description": (f"{cfg['book_desc']}（搭配通用規則使用）｜AI-GMoire v{version()}｜"
                        f"授權 {LICENSE_NAME}｜{REPO_URL}"),
        "entries": {str(e["id"]): e for e in entries},
    }


# ====================================================================== 通用版

GEN_GREETING = "歡迎來到 AI TRPG。\n\n在冒險開始之前，請先填寫你的角色設定。你可以多選，也可以選擇「隨機」：\n\n"


def general_card():
    rules = parse_markdown(read_text(SRC_GEN_MAIN)).get("AI TRPG規則").body
    cut = rules.index("\n6. ") + 1
    sys_rules, post_rules = rules[:cut].rstrip("\n"), rules[cut:]

    pc = parse_markdown(read_text(SRC_GEN_PC)).get("AI TRPG-PC角色卡").body
    cut = pc.index("\n* ") + 1
    pc_rules, pc_fields = pc[:cut].rstrip("\n"), pc[cut:]
    pc_rules = drop_lines(pc_rules, ["5. 隨機與判定方式"], "general")
    pc_fields = drop_lines(pc_fields, ["* 隨機與判定方式："], "general")

    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": "GMoire",
            "description": "通用型 AI TRPG 遊戲主持人。負責引導開局、推進劇情與管理進度總結。",
            "personality": "遵守規則的通用型 GM，會依照玩家設定的主題、風格與態度進行動態調整。嚴禁代替PC做決定。",
            "scenario": "由玩家自訂的任何世界觀與主題。",
            "first_mes": GEN_GREETING + pc_fields,
            "mes_example": "",
            "creator_notes": creator_notes("通用型 AI TRPG 遊戲主持人角色卡"),
            "system_prompt": sys_rules + "\n\n# AI TRPG-PC角色卡\n" + pc_rules,
            "post_history_instructions": post_rules,
            "alternate_greetings": [],
            "tags": ["TRPG", "RPG", "GM", "Universal"],
            "creator": "c821118",
            "character_version": version(),
            "extensions": {},
            "tagline": "GM主持通用TRPG",
        },
    }


# ====================================================================== Skills

SKILL_DIRS = {
    "general": ROOT / "skills" / "general_trpg_gm",
    "hogwarts": ROOT / "skills" / "hogwarts_trpg_gm",
    "fantasticbeasts": ROOT / "skills" / "fantasticbeasts_trpg_gm",
}
SKILL_REFERENCES = [
    (SKILL_DIRS["hogwarts"] / "references" / "檢索資料庫1991.md", SRC_HOG_DB["1991"]),
    (SKILL_DIRS["hogwarts"] / "references" / "檢索資料庫1890.md", SRC_HOG_DB["1890"]),
    (SKILL_DIRS["hogwarts"] / "references" / "c821118擴充資料庫.md", SRC_HOG_EXT),
    (SKILL_DIRS["fantasticbeasts"] / "references" / "檢索資料庫.md", SRC_FB_DB),
]

# 「擲骰結果回報」只有 Skill 版有工具可談，來源（rules/）是唯讀且不含工具細節，所以只在轉成 Skill 時加入。
# 加入的是 PC 可選的欄位，與一條規則：選了「回報」，GM 每回有判定時要在情節之前列出擲骰與公式計算。
REPORT_FIELD_TEXT = "擲骰結果回報：(預設)不回報／回報（僅選「工具擲骰」時填寫）"
REPORT_RULE_TEXT = (
    "選「工具擲骰」者須同時選定GM是否回報擲骰結果，確認後不得由GM更改。"
    "選「回報」時，GM每回輸出若有判定，須在情節敘事之前列出【擲骰回報】："
    "判定事項與難度、工具的原始輸出、公式計算（骰值加修正值對照難度）與結果等第，格式見 `references/隨機與判定協定.md` 第五節；"
    "未列出者視為尚未擲骰，不得直接寫出判定後的情節。選「不回報」時，以敘事呈現結果，PC要求時再公開。"
)
# general 版沒有預設變數（維持輕便），創角時由 PC 與 GM 自訂；規則細節在 general SKILL.md 的「主題變數」。
VARIABLE_FIELD_TEXT = "主題變數：(預設)無／自訂（至少可加3個；格式：七級正數／七級正負數／單一標籤；變數越多，上下文越長）"
VARIABLE_RULE_TEXT = (
    "填寫「主題變數」時，GM依主題建議可追蹤的變數，至少可加3個、不設上限，PC也可以不加。"
    "每個變數選一種格式：七級正數（1至7）、七級正負數（-3至+3）、單一標籤（一句文字，無等級）。"
    "GM須提醒PC：變數越多，每回要處理的上下文越長，建議從少量開始。確認後視為PC設定，運用規則見 SKILL.md 的「主題變數」。"
)
_RULES_END = "的觸發都不判定。"
_FIELD_TOOL = "工具擲骰（需AI環境實際執行工具，可從介面確認）"


def skill_card(src, label, numbered):
    """回傳加入擲骰回報欄位與規則的角色卡。numbered=True 為通用版（編號規則、頂格欄位），否則為開局角卡（項目符號、縮排欄位）。"""
    text = read_text(src)
    field_line = next(l for l in text.split("\n") if _FIELD_TOOL in l)
    indent = field_line[:len(field_line) - len(field_line.lstrip())]
    pairs = [(field_line, field_line + "\n" + indent + "* " + REPORT_FIELD_TEXT)]
    if numbered:
        pairs.append(("嚴禁未呼叫工具卻宣稱已擲骰。",
                      "嚴禁未呼叫工具卻宣稱已擲骰。\n6. " + REPORT_RULE_TEXT + "\n7. " + VARIABLE_RULE_TEXT))
        pairs.append(("* PC對TRPG的期待：", "* " + VARIABLE_FIELD_TEXT + "\n* PC對TRPG的期待："))
    else:
        pairs.append((_RULES_END, _RULES_END + "\n- 【擲骰回報】：" + REPORT_RULE_TEXT))
    return adapt(text, pairs, label)


SKILL_CARDS = [
    (SKILL_DIRS["general"] / "references" / "AI-TRPG-PC角色卡.md", SRC_GEN_PC, True),
    (SKILL_DIRS["hogwarts"] / "references" / "開局角卡.md", SRC_HOG_OPEN, False),
    (SKILL_DIRS["fantasticbeasts"] / "references" / "開局角卡.md", SRC_FB_OPEN, False),
]
# 每個 Skill 都附上同一份擲骰腳本與隨機協定（Skill 需能獨立搬移，所以複製而非引用）
SKILL_REFERENCES += [(d / "scripts" / "roll.py", SKILL_TOOLS / "roll.py") for d in SKILL_DIRS.values()]
SKILL_REFERENCES += [(d / "references" / "隨機與判定協定.md", SKILL_TOOLS / "隨機與判定協定.md")
                     for d in SKILL_DIRS.values()]

_SYNC = re.compile(r'(<!-- gmoire:sync src="(?P<src>[^"]+)" -->\n)(?P<body>.*?)(\n<!-- gmoire:end -->)', re.S)
_SKILL_VERSION = re.compile(r'(?m)^(  version: )"[^"]*"')


def sync_skill(path):
    """更新 SKILL.md 中 gmoire:sync 標記區塊（逐字帶入來源規則）與 frontmatter 版本號。"""
    text = read_text(path)
    count = len(_SYNC.findall(text))
    if count == 0:
        raise ValueError(f"{path.relative_to(ROOT)} 缺少 <!-- gmoire:sync src=\"...\" --> 標記區塊")
    text = _SYNC.sub(lambda m: m.group(1) + read_text(ROOT / m.group("src")).strip("\n") + m.group(4), text)
    text, n = _SKILL_VERSION.subn(lambda m: f'{m.group(1)}"{version()}"', text, count=1)
    if n == 0:
        raise ValueError(f'{path.relative_to(ROOT)} frontmatter 缺少 metadata 下的 version: "..."')
    return text


# ====================================================================== 入口

def dump_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def generate():
    """回傳 {絕對路徑: 預期內容}。同時重設並填入 ADAPTATIONS。"""
    ADAPTATIONS.clear()
    out = {}
    for year, cfg in YEARS.items():
        out[ROOT / cfg["card"]] = dump_json(hog_card(year))
        out[ROOT / cfg["lore"]] = dump_json(hog_lorebook(year))
    out[ROOT / "chub" / "general_TRPG_gm.json"] = dump_json(general_card())
    out[ROOT / FB_CFG["card"]] = dump_json(fb_card())
    out[ROOT / FB_CFG["lore"]] = dump_json(fb_lorebook())
    # TetheredDice-rules（實驗版）的主規則與開局角卡是手動維護的分支；檢索資料庫與 rules 版完全相同，由腳本複製
    out[EXPERIMENT_DIR / SRC_FB_DB.name] = read_text(SRC_FB_DB)
    for dest, src in SKILL_REFERENCES:
        out[dest] = read_text(src)
    for dest, src, numbered in SKILL_CARDS:
        out[dest] = skill_card(src, f"skill:{dest.parent.parent.name}", numbered)
    for skill_dir in SKILL_DIRS.values():
        out[skill_dir / "SKILL.md"] = sync_skill(skill_dir / "SKILL.md")
    return out


def main():
    setup_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="只比對，不寫檔；有差異時結束碼為 1")
    ap.add_argument("--diff", action="store_true", help="比對並顯示差異（隱含 --check）")
    args = ap.parse_args()

    expected = generate()
    stale = []
    for path, text in expected.items():
        assert_in_readonly(path)
        current = read_text(path) if path.exists() else None
        if current != text:
            stale.append(path)
            if args.diff:
                a = (current or "").splitlines()
                b = text.splitlines()
                rel = path.relative_to(ROOT).as_posix()
                sys.stdout.writelines(difflib.unified_diff(
                    [l + "\n" for l in a], [l + "\n" for l in b], f"a/{rel}", f"b/{rel}", n=1))

    check_only = args.check or args.diff
    for path in expected:
        mark = "過期" if path in stale else "最新"
        print(f"[{mark}] {path.relative_to(ROOT).as_posix()}")
    if check_only:
        print(f"\n共 {len(expected)} 個衍生檔，{len(stale)} 個與來源不一致。")
        return 1 if stale else 0
    for path in stale:
        write_text(path, expected[path])
    print(f"\n共 {len(expected)} 個衍生檔，已更新 {len(stale)} 個。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
