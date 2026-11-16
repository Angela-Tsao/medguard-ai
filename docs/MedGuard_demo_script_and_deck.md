# MedGuard AI — 5 分鐘 Demo 講稿 + Deck 大綱（草稿，2026-11-15）

> 課堂原型，不是醫療建議。報告與投影片上要保留免責聲明和「拿去問藥師」的寫法。
> 日期未確認：提案寫 dry run 2026-11-21、Demo Day 2026-12-05、deck／model card／app 連結 2026-12-04 交，
> 但提案自己也寫要去 Canvas 確認——先確認日期再排練。
> 副作用 33 條（kb_side_effects.csv）已逐條對過 FDA label（DailyMed，見 Side_effects_verification.md）：
> 33/33 有依據，不用刪改；修正版 kb_side_effects_VERIFIED.csv 已備好，換進原型後才能在講稿裡說「已驗證」。
> 知識庫至此 62/62 全部核對完（Beers 19＋交互作用 8＋群組規則 2＋副作用 33）。
> 商業成本數字已補好（見 MedGuard_business_cost_figures.md，附引用），deck 第 2 頁可直接用。
> Beers 19 條已核對完（見 Beers_2023_verification.md）：18/19 在 Table 2，oxybutynin 應改引 Table 7；
> 換不換兩個修正版 csv（Beers＋副作用）進原型，等使用者決定，換完要重跑 5 個 demo 輸入。

## 5 分鐘分配（照 Team Guide）

| 段落 | 時間 | 講者（建議） |
|---|---|---|
| 問題 | 0:30 | 產品／商業案例 |
| 方法 | 0:30 | 資料／模型 |
| Live demo | 2:00 | Demo／Build |
| 結果與風險 | 1:00 | 評估／風險 |
| 影響與下一步 | 0:30 | 產品／商業案例 |
| Q&A | 之後 2:00 | 全員 |

每人都要講一段，不要一個人講完全部。總字數約 950–1,050 字中文，語速約每分鐘 200 字，
排練時用手機計時，超時先砍「影響」段，不要砍 demo。

---

## 講稿全文（按段計時）

### 1. 問題（0:30）

「65 歲以上、同時吃很多種藥的長者，最怕的不是忘記吃藥，是藥跟藥打架。
他可能早上吃 warfarin 抗凝血，下午頭痛又吃一顆 Advil——這兩個加在一起，
胃腸出血的風險會明顯上升，但他自己不會知道。
現在的做法，是靠他自己記、靠家人問、靠回診時才被發現。
MedGuard AI 就是給他在家用的第一道檢查：把藥單打進來，先看一遍有沒有危險組合，
再拿著報告去問藥師。我們不建議停藥、換藥、改劑量，只幫他問對問題。」

> 成本數字已補好，可講（見 MedGuard_business_cost_figures.md）：「美國 65 歲以上長者 43% 同時吃 5 種以上的藥；
> 每年約 10 萬人次因為藥物不良反應被緊急送醫住院，其中三分之一跟 warfarin 有關——就是我們 demo 裡那個組合。
> 這些住院加起來，美國一年大約花 300 億美元。」來源：CDC（43%）、Budnitz NEJM 2011（99,600 次）、
> Age & Ageing 系統回顧 2025（高達 30% 住院、約 $30bn）。不要再報其他成本數字，也不要說 MedGuard 能省多少錢——沒量過。

### 2. 方法（0:30）

「做法分兩層，一定要分清楚。第一層是機器學習，只負責一件事：從自然語言裡認出藥名，
Advil 要認成 ibuprofen，拼錯的 warfrin 也要認得出來。
第二層不是模型猜的，是查表：認出來的藥名去對我們整理好的規則表，
查交互作用、查 AGS Beers Criteria 2023、查副作用，再出一頁白話報告。
使用者要先勾選確認藥名，系統才出報告；每個警示都附來源。」

### 3. Live demo（2:00）

**主 demo——先打這句（約 1:00）：**

> `I take warfarin, lisinopril, and sometimes Advil.`

「系統認出三種藥：warfarin、lisinopril、ibuprofen——Advil 已經對到 ibuprofen。
跳出 6 個警示，第一個就是最重要的：ibuprofen 加 warfarin，嚴重出血交互作用。
下面還有 ibuprofen 的 Beers 提醒，和 lisinopril 常見的頭暈。報告是白話寫的，
每一條都寫『這是什麼意思、來源是什麼、可以問藥師什麼』。」

**Limitation demo——再打這句（約 0:45）：**

> `I take my heart pill and something for sleep.`

「這句系統認不出來，它不會硬猜、不會硬出報告，而是說『認不出來，請確認』。
這就是我們的 guardrail：認不出來，比認錯更安全。
如果現場網路或 Streamlit 出問題，改播 60 秒備份錄影，不要現場修程式。」

> 備份錄影 60 秒內、demo 用的兩個輸入，dry run 前一定要錄好、存在本機。

### 4. 結果與風險（1:00）

「我們比了 7 種方法。選的是 logistic regression：合成測試集 1,000 句、1,323 個藥名，
precision 92.2%、recall 99.7%、F1 0.958，誤報 112 個、漏掉 4 個。
Baseline 的 exact match 雖然 precision 100%，但 recall 只有 60.6%，拼錯的幾乎全漏；
fuzzy match recall 99.6%，但誤報 465 個，連 morning 都會被當成藥。
Random forest 在合成集上其實更高，F1 0.997，但我們看了 test 才換模型就是 leakage，
所以沒換，留了一個 sealed test set 當公平決勝點。
整條流程另外測了 30 張合成藥單、212 個預期警示，全部找到，0 個錯報。

風險要老實講：Beers 的警示是有條件的，不是禁令。
例如 aspirin 只是『避免為了初級預防而開始用』，二級預防本來就該用；
warfarin 只是『有 DOAC 可用時避免開始用』，長期控制得好的使用者可以繼續。
我們的 app 現在還不知道適應症、劑量和療程，所以警示寫的是條件本身，
請評審不要把它當成個人化建議。副作用那 33 條已逐條對過 FDA label（DailyMed），
33/33 有依據、內容不用改——但講稿裡說「已驗證」之前，要先把 kb_side_effects_VERIFIED.csv 換進原型。
小提醒：講 lorazepam／alprazolam／diazepam 時說「嗜睡、頭暈，會提高跌倒風險」，不要把跌倒說成 label 上的直接副作用；
hydroxyzine 和 gabapentin 兩條 dry run 前再 spot-check 一次 label。

### 5. 影響與下一步（0:30）

「如果這個原型能用，長者在家輸入一次藥單，就能在回診前先發現 warfarin 加 NSAID
這種組合，帶著具體問題去問藥師，而不是等到出事。
下一步是三件事：換成 RxNorm 的藥名表、
用每個人各寫 15 到 20 句的 sealed test set 再評一次模型、錄好 60 秒備份 demo。謝謝。」

---

## Q&A 準備（2 分鐘，最可能被問的三題）

1. **「為什麼不用 random forest？它分數比較高。」**
   「因為那是在看過 test 結果之後才會想換，本身就是 leakage。
   我們留了一個 sealed test set，只評一次，如果那邊 random forest 還是贏，我們就換。」

2. **「Beers 標了就不能吃嗎？」**
   「Beers flags are conditional, not bans. 我們的 app 只會 flag 藥並寫出條件，
   例如 aspirin 只寫『避免為了初級預防而開始用』，因為 app 不知道病人的適應症、劑量或療程。
   每個警示都請使用者去問藥師，我們不建議停藥。」

3. **「你們的數字是真的嗎？副作用都查過了嗎？」**
   「Beers 19 條、交互作用 8 條、群組規則 2 條，已經逐條對過 Beers Criteria 2023 原文，
   18/19 在 Table 2，oxybutynin 的引用要改成 Table 7。
   副作用 33 條也已逐條對過 FDA label（DailyMed），33/33 有依據，內容不用改。
   知識庫 62 條全部核對完。商業成本數字也有引用：65 歲以上 43% 吃 5 種以上藥（CDC）、
   每年約 99,600 次 ADE 緊急住院（Budnitz NEJM 2011）、ADR 佔長者住院高達 30%、美國一年約 $30bn
   （Age & Ageing 系統回顧 2025）。」

---

## Deck 大綱（7 頁，Guide 要求 5–8 頁）

1. **標題／問題** — MedGuard AI，一句話：長者多重用藥，藥跟藥打架沒人先提醒。
   副標：給 65 歲以上長者在家用的藥單檢查，拿著報告去問藥師。
2. **誰用、現在要花多少成本** — 主使用者只鎖一個：65 歲以上、多重用藥的長者本人。
   成本數字（附引用，可直接用）：43% 的 65 歲以上長者吃 5+ 種藥（CDC）；每年約 99,600 次 ADE 緊急住院，
   warfarin 佔 33%（Budnitz NEJM 2011）；ADR/ADE 佔長者住院高達 30%，美國一年約 $30bn
   （Age & Ageing 系統回顧 2025）。不要寫 MedGuard 能省多少錢——沒量過。
3. **方法** — 兩層圖：NLP 認藥名 → 使用者確認 → 規則查表（交互作用／Beers／副作用）→ 白話報告。
   強調：警示是查表來的，不是模型猜的；ML 只負責認藥名。
4. **Live demo** — 兩個輸入截圖／流程：主 demo（warfarin + Advil，6 個警示）；
   limitation demo（認不出來就不硬出報告）。註明 60 秒備份錄影已備妥。
5. **結果** — 模型比較表：exact（P 100%／R 60.6%）、fuzzy（P 73.9%／R 99.6%）、
   logistic regression（P 92.2%／R 99.7%／F1 0.958）、random forest（F1 0.997，未選，原因見 Q&A）。
   End-to-end：30 張藥單、212 個預期警示，全找到、0 錯報。
   註：測試集是合成句＋手寫小集（50 句、69 個藥名、一人寫），不能當真實世界準確率。
6. **風險、限制與 guardrail** — Beers 是有條件的警示（舉 aspirin／warfarin 兩例）；
   限制：英文限定、只認單字藥名、無 OCR、藥名表尚未換 RxNorm；
   知識庫 62 條已全部核對完（Beers／交互作用／群組規則／副作用），但要先把兩個修正版 csv 換進原型才算數。
   Guardrail：使用者確認藥名、每條警示附來源、免責聲明、不建議停藥／換藥／改劑量。
7. **影響與下一步** — 影響：回診前先發現危險組合，帶著問題問藥師。
   下一步：RxNorm 藥名表、sealed test set 再評一次、真人測試 5–8 位。
   最後一頁放免責聲明：課堂原型，不是醫療建議。

---

## Dry run 前檢查清單（提案日期：2026-11-21，未確認）

- [ ] 上 Canvas 確認 dry run／Demo Day／交件日期（dry run 2026-11-21 是星期六，注意你當天 08:00–12:00 有課）
- [ ] 決定是否把 kb_beers_pim_VERIFIED.csv 和 kb_side_effects_VERIFIED.csv 一起換進原型（先備份原檔，換完重跑 5 個 demo 輸入）
- [x] 核對副作用 33 條（openFDA／DailyMed）——33/33 有依據，修正版 csv 已備好；hydroxyzine、gabapentin 兩條 dry run 前再 spot-check 一次 label
- [x] 補商業成本數字（附引用）——見 MedGuard_business_cost_figures.md，deck 第 2 頁可直接用
- [ ] 每位組員各寫 15–20 句 sealed test set，只評一次
- [ ] 錄 60 秒備份 demo，存在本機；教室設定上計時排練一次
- [ ] 補團隊角色表的名字
- [ ] Deck、model card、app 連結於交件日前一天備妥
- [ ] Deck、model card、app 連結於交件日前一天備妥

## 來源

- Team Guide 與 ML project 文件：`~/workspace/user/files/Final_Project___Demo_Day___Team_Guide__2___1.docx`、
  `~/workspace/user/files/ML_project__1.docx`（5 分鐘分配、40 分評分、角色分工）
- 原型提案與結果：`~/workspace/user/files/MedGuard_AI_Proposal_and_Results.docx`、
  `~/workspace/user/files/MedGuard_AI_prototype.zip`（101 種藥／200 個名字、模型數字、end-to-end 結果）
- Beers 核對：`workspace/goals/medguard-ai-final-project/files/Beers_2023_verification.md`、
  `kb_beers_pim_VERIFIED.csv`（AGS Beers Criteria 2023, J Am Geriatr Soc 2023;71:2052–2081）
