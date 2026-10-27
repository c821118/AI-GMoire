#!/usr/bin/env python3
"""Tethered Dice（偽隨機判定）數值試算。

從 `偽隨機判定-rules/怪獸產地-主規則.md` 的判定協定表格讀出 DC、修正值，計算各等第在各難度的成功率，
並檢查「AI 傾向擲出最大值」時，規則還能不能守住底線。調整規則裡的數字後，執行本腳本確認結果。

用法：
  python .ai/scripts/tethered_sim.py              印出行動判定與社交判定的成功率表與檢查結果
  python .ai/scripts/tethered_sim.py 路徑.md      改讀指定的規則檔

名詞：
  公平骰    每顆骰子都照實擲出
  全擲最大  AI 為了討好玩家，每顆骰子都擲出最大值（最壞情況的討好偏差）
  暴露格    公平成功率低於門檻，但「全擲最大」卻會成功的格子，數量越少越好
"""
import re
import sys
from collections import Counter

from common import ROOT, read_text, setup_console

DEFAULT_PATH = ROOT / "偽隨機判定-rules" / "怪獸產地-主規則.md"
LEVELS = ["未涉獵", "入門", "初學", "略通", "熟練", "專精", "精通"]
ACTION_DC = ["簡單", "中階", "困難", "傳奇"]
SOCIAL_DC = ["日常邀約", "涉入麻煩", "挺身冒險"]
AFFINITY = ["死敵", "厭惡", "疏離", "中立", "友善", "信任", "摯友"]
_ROW = re.compile(r"^\|\s*([^|\s]+)\s*\|\s*(-?\d+)\s*\|")


def read_table(text, names):
    """依第一欄名稱取出整數：| 名稱 | 數字 | ... |。名稱缺漏或重複都視為錯誤。"""
    found = {}
    for line in text.split("\n"):
        m = _ROW.match(line)
        if m and m.group(1) in names:
            if m.group(1) in found:
                raise ValueError(f"表格列重複：{m.group(1)}")
            found[m.group(1)] = int(m.group(2))
    missing = [n for n in names if n not in found]
    if missing:
        raise ValueError(f"找不到表格列：{missing}")
    return [found[n] for n in names]


def load(path=DEFAULT_PATH):
    text = read_text(path)
    return {
        "action_dc": read_table(text, ACTION_DC),
        "skill_mod": read_table(text, LEVELS),
        "social_dc": read_table(text, SOCIAL_DC),
        "affinity_mod": read_table(text, AFFINITY),
    }


def dist(faces):
    """多顆骰子的總和分布。faces 為各顆骰子的面數。"""
    c = Counter({0: 1})
    for s in faces:
        nxt = Counter()
        for total, ways in c.items():
            for f in range(1, s + 1):
                nxt[total + f] += ways
        c = nxt
    n = sum(c.values())
    return {k: v / n for k, v in c.items()}


def success(faces, mod, dc):
    return sum(p for total, p in dist(faces).items() if total + mod >= dc)


def action_faces(special):
    return [6] + [4] * special


def social_faces(bonds):
    return [12, 12, 12] + [12] * bonds


def action_table(params, special):
    return {lv: [success(action_faces(special), m, dc) for dc in params["action_dc"]]
            for lv, m in zip(LEVELS, params["skill_mod"])}


def social_table(params, bonds):
    return {a: [success(social_faces(bonds), m, dc) for dc in params["social_dc"]]
            for a, m in zip(AFFINITY, params["affinity_mod"])}


def exposure(params, kind, threshold=0.20, extra=(0, 1)):
    """列出『公平成功率 < 門檻，但全擲最大會成功』的格子。"""
    cells = []
    if kind == "action":
        rows, dcs, names, dc_names = params["skill_mod"], params["action_dc"], LEVELS, ACTION_DC
        faces_of = action_faces
    else:
        rows, dcs, names, dc_names = params["affinity_mod"], params["social_dc"], AFFINITY, SOCIAL_DC
        faces_of = social_faces
    for n in extra:
        faces = faces_of(n)
        for name, m in zip(names, rows):
            for dc, dn in zip(dcs, dc_names):
                fair = success(faces, m, dc)
                if fair < threshold and m + sum(faces) >= dc:
                    cells.append((n, name, dn, fair))
    return cells


def check(params):
    """回傳 (錯誤清單, 資訊清單)。這些是規則設計的底線，調整數字時不應被破壞。"""
    errors, info = [], []
    a0 = action_table(params, 0)
    # 1. 單調性：等第越高、難度越低，成功率不會變差
    for i, lv in enumerate(LEVELS):
        row = a0[lv]
        if any(row[j] < row[j + 1] - 1e-9 for j in range(len(row) - 1)):
            errors.append(f"行動判定：{lv} 的成功率不隨難度遞減")
        if i and any(a0[LEVELS[i - 1]][j] > row[j] + 1e-9 for j in range(len(row))):
            errors.append(f"行動判定：{lv} 的成功率低於前一個等第")
    # 2. 未涉獵：沒有特殊骰時不可能成功（成功只能靠奇蹟）
    if any(p > 0 for p in a0[LEVELS[0]]):
        errors.append("行動判定：未涉獵在沒有特殊骰時應為 0%")
    # 3. 奇蹟階梯：未涉獵在簡單難度，1 顆特殊骰應有機會但低於 15%，3 顆應過半
    m0, dc0 = params["skill_mod"][0], params["action_dc"][0]
    ladder = [success(action_faces(n), m0, dc0) for n in range(4)]
    info.append("未涉獵@簡單 的奇蹟階梯（特殊骰 0/1/2/3 顆）：" + " / ".join(f"{p:.0%}" for p in ladder))
    if not (0 < ladder[1] < 0.15 and ladder[3] > 0.5):
        errors.append("行動判定：未涉獵@簡單 的奇蹟階梯不在預期範圍（1 顆需 0%~15%、3 顆需過半）")
    # 4. 討好偏差：沒有特殊骰時，暴露格不超過 2 個
    ex = exposure(params, "action", extra=(0,))
    info.append(f"行動判定 暴露格（無特殊骰）：{len(ex)} 個 " + "、".join(f"{lv}@{dn}({p:.0%})" for _, lv, dn, p in ex))
    if len(ex) > 2:
        errors.append("行動判定：全擲最大即可成功的低機率格子過多")
    ex = exposure(params, "social", threshold=0.15, extra=(0, 1))
    info.append(f"社交判定 暴露格（0~1 顆羈絆骰）：{len(ex)} 個 "
                + "、".join(f"{a}@{dn}[羈絆{n}]({p:.0%})" for n, a, dn, p in ex))
    if len(ex) > 4:
        errors.append("社交判定：全擲最大即可成功的低機率格子過多")
    # 5. 社交：死敵在日常邀約不應輕易答應（公平 < 5%）
    s0 = social_table(params, 0)
    if s0[AFFINITY[0]][0] > 0.05:
        errors.append("社交判定：死敵對日常邀約的成功率過高")
    return errors, info


def deterministic_ok(params):
    """確定性判定（骰子取期望值）的結果，應與『公平成功率過半』大致一致。回傳不一致的格子。"""
    bad = []
    for n in (0, 1, 2):
        for lv, m in zip(LEVELS, params["skill_mod"]):
            for dc, dn in zip(params["action_dc"], ACTION_DC):
                expect = m + 3.5 + 2.5 * n >= dc
                fair = success(action_faces(n), m, dc)
                if expect and fair < 0.45 or (not expect) and fair > 0.70:
                    bad.append((n, lv, dn, fair, expect))
    return bad


def main():
    setup_console()
    path = DEFAULT_PATH if len(sys.argv) < 2 else sys.argv[1]
    params = load(path)
    print("行動判定  DC", dict(zip(ACTION_DC, params["action_dc"])), " 修正", dict(zip(LEVELS, params["skill_mod"])))
    for n in range(4):
        print(f"\n[行動判定] 1D6 + 修正 + {n} 顆特殊 D4（公平骰成功率）")
        print("        " + "  ".join(f"{d:>4}" for d in ACTION_DC))
        for lv, row in action_table(params, n).items():
            print(f"  {lv:<4}  " + "  ".join(f"{p:4.0%}" for p in row))
    print("\n社交判定  DC", dict(zip(SOCIAL_DC, params["social_dc"])), " 修正", dict(zip(AFFINITY, params["affinity_mod"])))
    for n in range(4):
        print(f"\n[社交判定] 3D12 + 修正 + {n} 顆羈絆 D12（公平骰成功率）")
        print("        " + "  ".join(f"{d:>4}" for d in SOCIAL_DC))
        for a, row in social_table(params, n).items():
            print(f"  {a:<4}  " + "  ".join(f"{p:4.0%}" for p in row))
    errors, info = check(params)
    print("\n[檢查]")
    for line in info:
        print("  ·", line)
    bad = deterministic_ok(params)
    print(f"  · 確定性判定（期望值）與公平成功率過半不一致的格子：{len(bad)} 個")
    for line in errors:
        print("  ✗", line)
    if not errors:
        print("  ✓ 所有設計底線皆通過")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
