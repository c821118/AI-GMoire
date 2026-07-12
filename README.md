# AI-GMoire

AI 桌上角色扮演遊戲（TRPG）的 GM 規則框架。讓 AI 扮演遊戲主持人（GM），帶領人類玩家（PC）進行文字冒險。

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
├── LICENSE                            ← MIT 授權
│
├── general_TRPG_rules/               ← [基礎prompt] 通用版 TRPG 規則
│   ├── AI-TRPG-主規則.md              ← 主規則
│   └── AI-TRPG-PC角色卡.md            ← PC 角色卡
│
├── Hogwarts_TRPG_rules/              ← [基礎prompt] 霍格華茲 TRPG 規則
│   ├── 霍格華茲-主規則.md              ← 核心規則引擎
│   ├── 霍格華茲-開局角卡.md            ← 角色創建流程與開局引導
│   ├── 霍格華茲-檢索資料庫1991.md      ← 1991年世界觀資料（哈利波特年代）
│   ├── 霍格華茲-檢索資料庫1890.md      ← 1890年世界觀資料（霍格華茲的傳承年代）
│   └── 霍格華茲-c821118擴充資料庫.md   ← c821118自訂擴充規則
│
├── skills/                          ← [SKILL格式] 適用於AI agent
│   ├── general_trpg_gm/
│   │   ├── SKILL.md                 ← 通用版 Skill 主檔案
│   │   └── references/              ← 補充資料
│   │       └── AI-TRPG-PC角色卡.md
│   └── hogwarts_trpg_gm/
│       ├── SKILL.md                 ← Skill 霍格華茲主檔案（YAML frontmatter + 規則）
│       └── references/              ← 補充資料
│           ├── 檢索資料庫1991.md
│           ├── 檢索資料庫1890.md
│           └── 開局角卡.md
│
├── chub/                            ← [Character Card格式] 適用Chub.ai跟SillyTavern
│   ├── general_TRPG_gm.json         ← 通用版 GM 角色卡
│   ├── hogwarts_gm_1991.json        ← 1991年代霍格華茲 GM 角色卡
│   └── hogwarts_gm_1890.json        ← 1890年代霍格華茲 GM 角色卡
│
└── lorebooks/                       ← [Lorebook格式] 使用通用規則時可套用的 Lorebook 主題包
    ├── hogwarts_1991_lorebook.json  ← 搭配通用規則使用的1991年霍格華茲主題包
    └── hogwarts_1890_lorebook.json  ← 搭配通用規則使用的1890年霍格華茲主題包
```

---

## 使用方式

### 方法一：AI 助手 Skill（Antigravity, Codex 等平台）

載入 `skills/` 底下任一主題或通用規則，AI 助手將自動啟用 GM 模式。

### 方法二 SillyTavern：Character Card

1. 在 SillyTavern 中匯入 `chub/` 底下的任一json（例如 `hogwarts_gm_1991.json`）。
2. 角色卡已內建完整規則，可以直接開始遊玩。

#### Chub.ai角色卡
| 網址 | Token |
| ---- | ---- |
|[通用版規則AI-GMoire](https://chub.ai/characters/c821118/ai-gmoire-bbc126490de1)|684|
| [霍格華茲1991 TRPG AI-GMoire](https://chub.ai/characters/c821118/huo-ge-hua-zi-1991-trpg-ai-gmoire-b1ff13bc2cea) | 3814 |
| [霍格華茲1890 TRPG AI-GMoire](https://chub.ai/characters/c821118/huo-ge-hua-zi-1890-trpg-ai-gmoire-9dd764b87d44) | 3812 |


### 方法三 SillyTavern：Character Card 通用規則 + Lorebook

1. 在 SillyTavern 中匯入 `chub/general_trpg_gm.json`，或將`general_TRPG_rules/AI-TRPG-主規則.md` 設為 System Prompt。
2. Lorebook載入 `lorebooks/hogwarts_1991_lorebook.json` 或其他Lorebook。
3. 開局時使用 `general_TRPG_rules/AI-TRPG-PC角色卡.md` 填寫角色設定。
4. 開始遊玩。通用主規則會在每回合自動生效，Lorebook 按關鍵字觸發。

#### Chub.ai世界書
| 網址 | Token |
| ---- | ---- |
|[霍格華茲1991 世界書] (https://chub.ai/lorebooks/c821118/huo-ge-hua-zi-1991-shi-jie-shu-799d601aa072) | 7672 |
|[霍格華茲1890 世界書](https://chub.ai/lorebooks/c821118/huo-ge-hua-zi-1890-shi-jie-shu-fd24518f05ae)|9338|


### 方法四：直接使用基礎提示詞

將 `Hogwarts_TRPG_rules/` 中的所有 `.md` 檔案提供給 AI，推薦使用筆記本。 即可開始遊玩，這是最早的使用方式，所有規則已經過測試並穩定運行。

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
| 1890 年 | 1890 年代 | 《霍格華茲的傳承》電玩 |

### 核心特色

- **選擇驅動**：每段結尾提供可選行動，玩家決定劇情走向。
- **六大敘事支柱**：校園日常、友誼培養、魔法學習、心動戀愛、隱藏劇情、家庭互動。
- **程度化變數**：禁止直接記錄數字，所有變數以文字程度（如「初學/略通/熟練/專精」）融入敘事。
- **生死豁免**：原作角色的死亡事件交由玩家抉擇，可改寫命運。
- **擴充模組**：支援學生湯姆瑞斗穿越、高年級轉學生等特殊開局。

---

## 授權

[MIT License](LICENSE)

## 作者與致謝

- 作者：[c821118](https://github.com/c821118)
- 致謝：[Threads@s6oneohfive](https://www.threads.com/@s6oneohfive/post/DZFPYmNk27g)
