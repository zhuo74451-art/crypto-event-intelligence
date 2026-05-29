# Cursor 交接提示词

## 当前任务

我们正在做 Crypto Event Intelligence v0.6。

目标不是交易，也不是生成买卖信号。当前目标是提高事件准入质量：

```text
raw candidates -> entity enrichment -> deduplication -> relevance scoring -> review queues
```

## 当前重点文件

```text
data/entity_dictionary.csv
data/event_candidates_v06_relevance_scored.csv
data/event_candidates_v06_publish_review_queue.csv
data/event_candidates_v06_other_review_queue.csv
data/event_candidates_v06_discard_audit_sample.csv
results/v061_review_queue_report.md
```

## Cursor 需要帮忙做什么

1. 查看 `data/event_candidates_v06_publish_review_queue.csv`。
2. 找出 `auto_publish` 和 `human_review` 里的误判。
3. 如果方便，可以填写这些人工列：
   - `manual_decision`
   - `manual_event_type_l1`
   - `manual_event_type_l2`
   - `manual_primary_asset_symbol`
   - `manual_notes`
4. 查看 `data/event_candidates_v06_other_review_queue.csv`。
5. 找出反复出现、值得补进实体词典或 L1/L2 分类规则的模式。
6. 只有当实体反复出现且对交易研究有意义时，才补进 `data/entity_dictionary.csv`。

## 不要做

- 不要接 TG 发布。
- 不要加入买入、卖出、做多、做空、入场、止损、止盈这类语言。
- 不要用 24h/72h 后验收益影响实时发布评分。
- 不要覆盖 v0.4 / v0.5 的结果文件。
- 不要把 `other_review` 直接变成可发布类型。

## 直接复制给 Cursor 的中文提示词

```text
你正在协助修改一个本地 Web3 事件情报项目，项目目录是：
C:\Users\PC\Desktop\事件情报系统

当前阶段是 v0.6，目标是“事件准入质量层”，不是交易系统，不是喊单，不接自动下单。

请重点查看这些文件：

1. data/event_candidates_v06_publish_review_queue.csv
2. data/event_candidates_v06_other_review_queue.csv
3. data/event_candidates_v06_discard_audit_sample.csv
4. data/entity_dictionary.csv
5. scripts/enrich_event_entities.py
6. scripts/filter_research_relevant_events.py

你要做的事情：

1. 检查 publish_review_queue 里的 auto_publish / human_review，找出明显误判。
2. 检查 other_review_queue，找出反复出现但被漏识别的 Web3 实体或事件类型。
3. 检查 discard_audit_sample，找出是否有被误杀的高价值事件。
4. 给出应该补进 entity_dictionary.csv 的实体、别名或项目名。
5. 给出应该改进的 L1 / L2 taxonomy 规则。
6. 如果你直接改文件，请保持改动小，每条规则都要能解释。

不要做：

1. 不要接 TG。
2. 不要做网页。
3. 不要做自动交易。
4. 不要生成买入/卖出/做多/做空建议。
5. 不要用 post-event 24h/72h abnormal return 去影响 realtime scoring。
6. 不要覆盖历史结果文件。

输出要求：

1. 列出 human_review 中最明显的误判样本 candidate_id 和原因。
2. 列出 other_review 中值得补字典/规则的模式。
3. 列出 discard 中可能被误杀的样本。
4. 给出建议修改点，最好按文件分组。
5. 如果改了代码或 CSV，说明改了什么，以及为什么。
```
