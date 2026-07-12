# GM-Prompt-Toolkit Progress

最後更新：2026-07-12

---

## 工作流總覽

| # | 工作流 | 狀態 | 說明 |
|:---:|---|:---:|---|
| 0 | Bug 修正 | ⏳ 待執行 | 原始檔案的翻譯不一致與語法錯誤 |
| 1 | 霍格華茲 → Skill | ⏳ 待執行 | 轉換為 Antigravity Skill 格式 |
| 2 | 霍格華茲 → Character Card | ⏳ 待執行 | 轉換為 chub.ai V2 Character Card |
| 3 | 霍格華茲 → Lorebook | ⏳ 待執行 | 轉換為通用規則可用的 Lorebook |
| 4 | 通用規則改進 | ⏳ 待執行 | 精簡措辭、修正語法、控制 token |
| 5 | README.md | ⏳ 待執行 | 撰寫 GitHub 首頁說明 |

---

## 工作流 0：Bug 修正

> 原始檔案為唯讀，Bug 修正需確認處理方式。

| 項目 | 檔案 | 問題 | 處理方式 |
|---|---|---|---|
| `[x]` | `general_TRPG_skill/AI TRPG規則.md` L18 | 缺右括號 `)` | 已在通用規則v2中修正 |
| `[x]` | `Hogwarts_TRPG_rules/霍格華茲-檢索資料庫1890.md` L81 | 「福靈劑」應為「福來福喜」 | 已在生成的JSON中修正 (原始檔原已正) |
| `[x]` | `Hogwarts_TRPG_rules/霍格華茲-檢索資料庫1991.md` L1 | 標題缺年份 | 已在生成的JSON中修正 (原始檔原已正) |

---

## 工作流 1：霍格華茲 → Skill

| 項目 | 狀態 |
|---|---|
| `[x]` 建立 `skills/hogwarts_trpg_gm/SKILL.md` | 已完成 |
| `[x]` 建立 `skills/hogwarts_trpg_gm/references/` 目錄與檔案 | 已完成 |
| `[x]` 驗證 YAML frontmatter 格式 | 已完成 |

---

## 工作流 2：霍格華茲 → Character Card

| 項目 | 狀態 |
|---|---|
| `[x]` 拆分主規則為 `system_prompt` 與其他欄位 | 已完成 |
| `[x]` 拆分檢索資料庫為 Lorebook entries | 已完成 |
| `[x]` 建立 `chub/hogwarts_gm_1991.json` | 已完成 |
| `[x]` 建立 `chub/hogwarts_gm_1890.json` | 已完成 |
| `[x]` JSON Schema 驗證 `chara_card_v2` 格式 | 已完成 |
| `[x]` 計算各欄位 token 數 | 已完成 |

---

## 工作流 3：霍格華茲 → Lorebook

| 項目 | 狀態 |
|---|---|
| `[x]` 設計 Lorebook entry 拆分方案 | 已完成 |
| `[x]` 將「主規則 + 檢索資料庫 + 開局角卡」整合為 Lorebook | 已完成 |
| `[x]` 建立 `lorebooks/hogwarts_1991_lorebook.json` | 已完成 |
| `[x]` 建立 `lorebooks/hogwarts_1890_lorebook.json` | 已完成 |
| `[x]` 驗證 Lorebook 與通用規則的相容性 | 已完成 |

---

## 工作流 4：通用規則改進

| 項目 | 狀態 |
|---|---|
| `[x]` 精簡主規則措辭（目標 ≤ 800 token） | 已完成 |
| `[x]` 增加「嚴禁GM代替PC做決定」 | 已完成 |
| `[x]` PC 角色卡選項加入「隨機」 | 已完成 |
| `[x]` 修正 L18 括號錯誤 | 已完成 |
| `[x]` Token 計數驗證 | 已完成 |

---

## 工作流 5：README.md

| 項目 | 狀態 |
|---|---|
| `[x]` 撰寫專案介紹 | 已完成 |
| `[x]` 說明各資料夾用途 | 已完成 |
| `[x]` 說明使用方式 | 已完成 |
| `[x]` 說明授權條款 | 已完成 |
