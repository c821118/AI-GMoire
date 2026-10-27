# AI-GMoire

AI 桌上角色扮演遊戲（TRPG）的 GM 規則框架。讓 AI 扮演遊戲主持人（GM），帶領人類玩家（PC）進行文字冒險。

目前版本：**v1.1.0**（版本紀錄見 [CHANGELOG.md](CHANGELOG.md)）

## 簡介

AI-GMoire 是一套供 AI 閱讀的 TRPG 規則書，是AI扮演GM的魔導書（grimoire），等同於桌遊的規則手冊。
AI 讀取後即可擔任稱職的遊戲主持人，依據規則驅動敘事、管理 NPC、追蹤變數，並引導玩家做出選擇。

採用**雙層架構**：

- **引擎層**：輕量通用 TRPG 規則，定義 GM 行為準則、權限級聯、進度總結與輸出格式。
- **內容層**：特定世界觀的 Lorebook，以關鍵字觸發方式按需載入，節省 token。

---

## 檔案結構

```
AI-GMoire/
├── README.md                          ← 本文件
├── CHANGELOG.md                       ← 版本紀錄
├── VERSION                            ← 專案版本號（所有衍生檔的版本號來源）
├── LICENSE                            ← MNCL-FW 1.0（非商業、相同方式分享）
│
├── rules/                            ← [玩法一｜rules] 規則原始檔，適用 NotebookLM 這類可上傳檔案、但不具備工具的 AI 介面
│   ├── general_TRPG_rules/           ← [唯讀來源] 通用版 TRPG 規則
│   │   ├── AI-TRPG-主規則.md          ← 主規則
│   │   └── AI-TRPG-PC角色卡.md        ← PC 角色卡
│   ├── Hogwarts_TRPG_rules/          ← [唯讀來源] 霍格華茲 TRPG 規則
│   │   ├── 霍格華茲-主規則.md          ← 核心規則引擎
│   │   ├── 霍格華茲-開局角卡.md        ← 角色創建流程與開局引導
│   │   ├── 霍格華茲-檢索資料庫1991.md  ← 1991年世界觀資料（哈利波特年代）
│   │   ├── 霍格華茲-檢索資料庫1890.md  ← 1890年世界觀資料（霍格華茲的傳承年代）
│   │   └── 霍格華茲-c821118擴充資料庫.md ← c821118自訂擴充規則
│   └── FantasticBeasts_TRPG_rules/   ← 怪獸產地 TRPG 規則（成年職業巫師，以電影三部曲為基礎）
│       ├── 怪獸產地-主規則.md          ← 核心規則引擎
│       ├── 怪獸產地-開局角卡.md        ← 角色創建流程與 1926／1927／1932 年開局引導
│       └── 怪獸產地-檢索資料庫.md      ← 時間線、勢力、職業、咒語、生物、人物資料
│
├── skills/                          ← [玩法三｜skills] 適用於可載入 AI Skill 的 AI agent（唯一附有擲骰工具）
│   ├── general_trpg_gm/
│   │   ├── SKILL.md                 ← 通用版 Skill 主檔案（含選用的工具使用規則）
│   │   └── references/
│   │       └── AI-TRPG-PC角色卡.md
│   ├── hogwarts_trpg_gm/
│   │   ├── SKILL.md                 ← 霍格華茲 Skill 主檔案（含選用的工具使用規則）
│   │   └── references/
│   │       ├── 檢索資料庫1991.md
│   │       ├── 檢索資料庫1890.md
│   │       ├── 開局角卡.md
│   │       └── c821118擴充資料庫.md
│   └── fantasticbeasts_trpg_gm/
│       ├── SKILL.md                 ← 怪獸產地 Skill 主檔案（含選用的工具使用規則）
│       └── references/
│           ├── 檢索資料庫.md
│           └── 開局角卡.md
│   （每個 Skill 另有 scripts/roll.py 與 references/隨機與判定協定.md，由 .ai/skill-tools/ 複製而來）
│
├── chub/                            ← [玩法二｜chub] Character Card 與 Lorebook，適用 SillyTavern 與 Chub.ai（無擲骰機制）
│   ├── general_TRPG_gm.json         ← 通用版 GM 角色卡
│   ├── hogwarts_gm_1991.json        ← 1991年代霍格華茲 GM 角色卡
│   ├── hogwarts_gm_1890.json        ← 1890年代霍格華茲 GM 角色卡
│   ├── fantasticbeasts_gm.json      ← 怪獸產地 GM 角色卡（1926／1927／1932 於開局時選擇）
│   └── lorebooks/                   ← [Lorebook格式] 使用通用規則時可套用的主題包
│       ├── hogwarts_1991_lorebook.json
│       ├── hogwarts_1890_lorebook.json
│       └── fantasticbeasts_lorebook.json
│
└── .ai/
    ├── scripts/                     ← 維護用腳本（轉置、比對、驗證）
    │   ├── build.py
    │   ├── validate.py
    │   ├── tokens.py
    │   └── common.py
    └── skill-tools/                 ← Skill 共用的擲骰腳本與隨機協定（單一來源，由 build.py 複製到各 Skill）
        ├── roll.py
        └── 隨機與判定協定.md
```

> `rules/Hogwarts_TRPG_rules/` 與 `rules/general_TRPG_rules/` 是整個專案的**唯讀來源**。
> `chub/` 底下的 JSON 與 `skills/*/references/` 由 `.ai/scripts/build.py` 從 `rules/` 轉置而來，請勿手動修改。

---

## 使用方式

本專案提供**三種玩法**，分別針對不同的平台設計，**擇一使用**即可，不需要同時使用：

| 玩法 | 資料夾 | 適用平台 | 擲骰工具 |
| ---- | ---- | ---- | ---- |
| **rules** | `rules/` | 可以上傳檔案作為來源、但**不具備工具**的 AI 介面，例如 NotebookLM | 無 |
| **chub** | `chub/` | SillyTavern 與 Chub.ai | 無（SillyTavern 的擲骰工具由玩家自行安裝，AI 無法使用，因此角色卡不含擲骰機制） |
| **skills** | `skills/` | 可載入 AI Skill 的 AI agent，例如 Claude Code、Codex、Antigravity | **只有這個版本**附有擲骰工具，且為選用 |

三種玩法使用同一套規則，只是封裝方式不同。`rules/` 是規則的原始檔，`chub/` 與 `skills/` 都由它轉置而來。

### 玩法一：rules（NotebookLM 這類上傳檔案的 AI 介面）

1. 選擇一個主題資料夾：`rules/Hogwarts_TRPG_rules/`（霍格華茲）、`rules/FantasticBeasts_TRPG_rules/`（怪獸產地）或 `rules/general_TRPG_rules/`（通用）。
2. 將資料夾中的所有 `.md` 檔案作為來源上傳，推薦使用 NotebookLM，即可開始遊玩。這是最早的使用方式，規則已經過測試並穩定運行。

這些平台沒有工具，因此規則中**不使用機率**，判定一律依能力與難度直接決定結果。空白角色卡中的「隨機與判定方式」欄位，「工具擲骰」選項在這個玩法無法使用（沒有工具），請選預設的確定性判定，或自行擲骰後回報。

### 玩法二：chub（SillyTavern / Chub.ai）

**單張角色卡**：在 SillyTavern 匯入 `chub/` 底下的任一 json（例如 `hogwarts_gm_1991.json`），角色卡已內建完整規則，可以直接開始遊玩。

| Chub.ai 角色卡 | Token（v1.1.0 估算） |
| ---- | ---- |
| [通用版規則AI-GMoire](https://chub.ai/characters/c821118/ai-gmoire-bbc126490de1) | 約 1,000 |
| [霍格華茲1991 TRPG AI-GMoire](https://chub.ai/characters/c821118/huo-ge-hua-zi-1991-trpg-ai-gmoire-b1ff13bc2cea) | 約 4,000 |
| [霍格華茲1890 TRPG AI-GMoire](https://chub.ai/characters/c821118/huo-ge-hua-zi-1890-trpg-ai-gmoire-9dd764b87d44) | 約 3,900 |

> Token 為腳本粗估的常駐量，Chub 顯示值會略有出入。Chub 上的角色卡需要重新上傳才會更新為 v1.1.0。怪獸產地的角色卡尚未上傳 Chub，常駐約 4,900 token（含常駐的譯名條目約 5,200）。

**通用規則 + 世界書**：

1. 匯入 `chub/general_TRPG_gm.json`，或將 `rules/general_TRPG_rules/AI-TRPG-主規則.md` 設為 System Prompt。
2. 世界書載入 `chub/lorebooks/` 底下的檔案，例如 `hogwarts_1991_lorebook.json`。
3. 開局時使用 `rules/general_TRPG_rules/AI-TRPG-PC角色卡.md` 填寫角色設定。
4. 開始遊玩。通用主規則每回合自動生效，世界書按關鍵字觸發。

| Chub.ai 世界書 | Token（v1.1.0 估算） |
| ---- | ---- |
| [霍格華茲1991 世界書](https://chub.ai/lorebooks/c821118/huo-ge-hua-zi-1991-shi-jie-shu-799d601aa072) | 約 8,500 |
| [霍格華茲1890 世界書](https://chub.ai/lorebooks/c821118/huo-ge-hua-zi-1890-shi-jie-shu-fd24518f05ae) | 約 9,100 |

chub 版本不含任何擲骰機制。之後會另外補充 SillyTavern 的 Preset。

### 玩法三：skills（可載入 Skill 的 AI agent）

載入 `skills/` 底下任一主題（`hogwarts_trpg_gm`、`fantasticbeasts_trpg_gm`、`general_trpg_gm`），AI agent 將自動啟用 GM 模式。

Skill 內另附**選用的工具使用規則**：若 AI agent 能使用工具，GM 可以用真實隨機來源擲骰與判定、
以 `gm_notes.md` 記錄後台資訊、以 `saves/` 存檔與讀檔。**擲骰工具只在 Skill 版提供。**

**沒有內建工具的 AI 怎麼辦？** 語言模型自己「想一個隨機數」並不隨機，會傾向給出討好玩家的結果，而且它不知道自己在編造。
所以由玩家在空白角色卡的「隨機與判定方式」欄位選定，而不是讓 AI 自行判斷有沒有工具
（詳見[隨機與判定協定](.ai/skill-tools/隨機與判定協定.md)）：

1. **確定性判定（預設）**：完全不使用機率，依能力與難度的高低直接決定結果，等同 rules 版的作法。
2. **玩家自行擲骰**：GM 先宣告難度與後果，玩家用實體骰或任何骰子 App 擲出並回報。
3. **工具擲骰**：玩家明確選擇才使用；執行 Skill 內附的 `scripts/roll.py`（只用 Python 標準函式庫），或讀取 random.org 的純文字隨機數。工具不可用時，GM 必須明說並請玩家改選，不得假裝擲骰。

判定只用於「結果不確定、失敗有意義，而且影響劇情走向」的行動，每個時間切片至多一次。
角色卡原本的「隨機」選項已改為「AI推薦」：GM 依其他欄位推薦合理選項供玩家確認，不使用機率。

---

## 怪獸產地 TRPG 規則

以電影《怪獸與牠們的產地》三部曲（1926 紐約、1927 巴黎、1932 歐亞）為基礎，與霍格華茲版的差異如下：

- **主角是已畢業的成年巫師**：魔法程度取決於畢業成績；玩家自選兩項魔法專業，其餘由 GM 在上限內分配，不偏袒玩家。
- **職業取代學業**：涵蓋魔法部門、自營業、教育、銀行與醫療、其他產業。可提供現實職業，由 GM 對照或自創。
- **血統與家庭不影響玩家**，基礎資產由職業決定；唯一例外是姓氏屬神聖二十八姓時，英歐社交場合的初遇好感度略高。
- **主線是與葛林戴華德集團的交錯碰撞**：第一回合 GM 必須依職業編造初次衝突；原作事件為「主線錨點」，PC 與原作角色交會而不取代。
- **黑魔法**不可當作魔法專業，開局職業不得為黑巫師；除德姆蘭學院畢業生外，最早五年級之後才能接觸黑魔法。
- 已提供三種玩法：`rules/FantasticBeasts_TRPG_rules/`、角色卡與世界書（`chub/fantasticbeasts_gm.json`、`chub/lorebooks/fantasticbeasts_lorebook.json`）、Skill（`skills/fantasticbeasts_trpg_gm/`）。標示「待核」的譯名與細節尚未逐項核對。

---

## 通用 TRPG 規則

以「通用」、「輕量」、「低 token 消耗」為設計原則的 TRPG 引擎。

### 設計理念

- **主規則**每回合由 AI 讀取，必須極度精簡（≤ 800 token）。
- **PC 角色卡**僅在開局第 1 回合讀取，後續依賴「進度總結」延續遊戲狀態。
- **Lorebook**按關鍵字觸發，僅在相關場景注入，節省 token。
- 整套規則（主規則 + PC 角色卡）合計不超過 1,500 token。

---

## 霍格華茲 TRPG 規則

以 J.K. 羅琳的哈利波特系列為世界觀基礎，所有中文名詞遵循台灣「皇冠出版社」繁體中文翻譯。

### 支援的時空

| 時空 | 年代 | 世界觀參考 |
|---|---|---|
| 1991 年 | 1991–1998 | 哈利波特小說系列 |
| 1890 年 | 1890 年代 | 《霍格華茲的傳承》電玩（不包含湯姆瑞斗） |

### 核心特色

- **選擇驅動**：每段結尾提供可選行動，玩家決定劇情走向。
- **六大敘事支柱**：校園日常、友誼培養、魔法學習、心動戀愛、隱藏劇情、家庭互動。
- **程度化變數**：禁止直接記錄數字，所有變數以文字程度（如「初學/略通/熟練/專精」）融入敘事。
- **生死豁免**：原作角色的死亡事件交由玩家抉擇，可改寫命運。
- **擴充模組**：支援高年級轉學生與學生湯姆瑞斗穿越（僅 1991 年代；1890 年代不包含湯姆瑞斗）等特殊開局。

---

## 維護者指南

Markdown 是單一真相源，JSON 與 Skill 的補充資料都由腳本轉置，只需要 Python 3（不需安裝套件）。

```
python .ai/scripts/build.py            # 從 Markdown 重新產生 chub/、skills/ 的衍生檔
python .ai/scripts/build.py --check    # 只比對，有過期檔案時結束碼為 1
python .ai/scripts/build.py --diff     # 比對並顯示差異
python .ai/scripts/validate.py         # 驗證同步、JSON 結構、來源覆蓋率、年份與版本一致性、Token 估算
python .ai/scripts/tokens.py           # chub/ 逐欄位、逐條目的 Token 明細
```

- 修改規則：只改 `rules/` 底下的 Markdown（`Hogwarts_TRPG_rules/`、`general_TRPG_rules/` 為唯讀來源，需作者同意後才修改），再執行 `build.py`。
- 修改工具使用規則：直接編輯 `skills/*/SKILL.md` 中 `<!-- gmoire:end -->` 之後的手寫區段，`build.py` 不會覆蓋。
- 修改擲骰腳本或隨機協定：只改 `.ai/skill-tools/`，`build.py` 會複製到每個 Skill 的 `scripts/` 與 `references/`。
- 升版：修改根目錄的 `VERSION` 與 `CHANGELOG.md`，再執行 `build.py`，版本號會同步寫入角色卡、Lorebook 與 SKILL.md。

---

## 授權

本專案自 v1.1.0 起採用 [MNCL-FW 1.0](LICENSE)（AI-GMoire 同人作品非商業 Copyleft 授權，改寫自 MNCL 1.0），重點如下：

- **可以**：免費使用、研究、修改、分享；搭配任何 AI 模型或服務遊玩（包含自己付費的訂閱）；自由分享遊玩產生的故事。
- **必須**：保留署名與授權；散布修改版時以相同授權公開，並附可讀的原始提示詞；尊重原作權利人與所用平台的規範。
- **不可以**：販售、設付費牆或以贊助層級鎖定內容、捆綁收費產品、營利使用；隱藏或鎖定提示詞內容；冒充官方；違法或違反平台規範。
- 規則、設定與敘事文字，亦可依您的選擇改用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hant)。
- v1.0.0 及更早的版本以 MIT 授權釋出，已取得的副本仍適用 MIT。

此授權條款**尚未經律師審閱**；它不是 OSI 認可的開源授權。

### 同人作品聲明

本專案是非官方的同人作品，與《哈利波特》系列的權利人（J.K. 羅琳、華納兄弟等）以及《霍格華茲的傳承》（Hogwarts Legacy）的開發與發行方無任何關聯，也未獲其背書。
相關名稱、角色與設定的權利歸原權利人所有；授權條款僅涵蓋本專案的原創內容。

## 作者與致謝

- 作者：[c821118](https://github.com/c821118)
- 致謝：[Threads@s6oneohfive](https://www.threads.com/@s6oneohfive/post/DZFPYmNk27g)
