# ROPA 预审 Agent：MVP 产品需求文档

## 1. 背景

业务部门用 Google Form 提交 ROPA。填写质量参差不齐，privacy 团队要花时间和业务部门来回沟通缺失的细节，让他们补充信息后才能开始审核。

## 2. 目标

在进入 privacy 审核前，自动预审每份提交的信息是否足够。只判断信息够不够，不判断处理活动本身是否合规。

## 3. 用户

- 运行者：privacy 团队成员。
- 结果的主要读者：填表人，非法律背景。
- privacy 团队看结果只为两件事：评估 agent 运行得怎么样，以及处理结果为 Escalate 的提交。

## 4. MVP 范围

- 包含：命令行脚本、读取 CSV、逐行审查、输出带结果列的新 CSV、用 Claude Agent SDK 运行、criteria 做成 SDK 原生加载的 skill、每条引用经过代码核对。
- 不包含：直连 Google Form 或 Sheets、自动通知填表人、网页界面、合规性判断。结果由 privacy 团队手动转给填表人。
- 出错处理分三层：

| 层级 | 情况 | 处理 |
|---|---|---|
| 让 agent 重做 | 输出没通过完整性检查或引用核对 | 接着同一次对话让 agent 修改，最多重做 3 次，仍不通过则判 Escalate |
| 该行判 Escalate | 调用模型或处理该行时出错，包括临时性错误 | 不额外重试，其余行继续 |
| 整次运行停止 | 文件不存在、列缺失、API key 无效、余额不足 | 报错退出，不生成结果文件 |

- 永远不修改填表人的回答内容。空白回答不算错误，按信息不足处理。

## 5. 输入

来源文件是 Google Form 导出的 CSV，共 13 列。脚本启动时先校验列名是否齐全。实际列名以样例 CSV 为准。

代码把每一行转成固定结构的 JSON 再交给 agent：

| 字段 | 类型 | 内容 |
|---|---|---|
| `submission_id` | 文字 | 用 CSV 行号生成，例如 `row-2`，用于把结果对回原行 |
| `answers` | 列表 | 11 个问题的回答，每个问题一条记录 |

`answers` 里每条记录：

| 字段 | 类型 | 内容 |
|---|---|---|
| `question_id` | 文字 | 问题的固定代号 |
| `question_text` | 文字 | 问卷上的原始问题 |
| `answer` | 文字 | 填表人的回答原文，一字不改，没填则为空 |

11 个问题的代号：

| `question_id` | 对应的 CSV 列 |
|---|---|
| `business_department` | 2. Business Department |
| `purpose_of_processing` | 3. Purpose of processing |
| `reason_for_using_personal_data` | 4. Why do you use personal data? |
| `markets` | 6. Markets to launch this project |
| `data_subjects` | 5. Who do you hold information about? |
| `data_categories` | 6. What specific information do you hold about individuals? |
| `data_sources` | 7. Where do you get the data? |
| `data_recipients` | 8. Who do you share the data with? |
| `sharing_reason` | 9. Why do you need to share this data with this recipient? |
| `retention_period` | 10. How long will personal information will be retained? |
| `security_measures` | 11. How do you keep it safe? |

`1. Name` 和 `Timestamp` 两列不发给模型，只保留在输出 CSV 里。自由文本答案里出现的人名，MVP 不做额外过滤。

一份输入的样子，实际会有 11 条，这里只展示一条：

```json
{
  "submission_id": "row-2",
  "answers": [
    {
      "question_id": "retention_period",
      "question_text": "How long will personal information will be retained?",
      "answer": "as long as needed"
    }
  ]
}
```

## 6. 输出

模型返回的 JSON，实际会有 11 条，这里只展示一条：

```json
{
  "submission_id": "row-2",
  "summary": "Most questions are answered clearly. The retention period needs a specific timeframe.",
  "questions": [
    {
      "question_id": "retention_period",
      "status": "incomplete",
      "quoted_answer": "as long as needed",
      "missing_detail": "Please state a specific period, for example 2 years after the contract ends.",
      "priority": "High",
      "unsure_reason": ""
    }
  ]
}
```

| 字段 | 内容 |
|---|---|
| `question_id` | 只能是 11 个代号之一 |
| `status` | `complete`、`incomplete`、`unsure` 三选一 |
| `quoted_answer` | 填表人原话引用 |
| `missing_detail` | 缺什么细节，仅 `incomplete` 时填 |
| `priority` | High、Medium、Low，仅 `incomplete` 时填 |
| `unsure_reason` | 为什么拿不准，仅 `unsure` 时填 |

输出的三道检测：

| 关卡 | 谁来查 | 查什么 | 没通过时 | 仍失败的 `escalation_cause` |
|---|---|---|---|---|
| 1. 格式 | SDK | 字段齐全、类型和枚举值正确 | SDK 自动重新生成 | `technical_error` |
| 2. 完整性 | 代码 | 11 个代号各出现一次；`incomplete` 填了 `missing_detail` 和 `priority`；`unsure` 填了 `unsure_reason`；`submission_id` 与输入一致 | 告诉 agent 哪里不全，最多重做 3 次 | `technical_error` |
| 3. 引用真实性 | 代码 | 每条 `quoted_answer` 能在该问题的原始回答里找到；原回答为空时引用也为空。比对时忽略空格、换行和大小写差异 | 告诉 agent 哪条引用找不到，最多重做 3 次 | `quote_check_failed` |

第 2、3 关发现的所有问题会收集成一张清单，一次全部反馈给 agent。两关的重做次数合并计算，总共不超过 3 次。3 次后如果还剩引用问题，原因记为 `quote_check_failed`；只剩完整性问题则记为 `technical_error`。

这三道检测能保证输出结构完整、引用是真的。它们查不出模型的判断本身对不对，这要靠下一阶段拿人工结论来对比。

写进 CSV 的列，追加在原有列之后：

| 列名 | 内容 |
|---|---|
| `verdict` | 代码算出的结论 |
| `escalation_cause` | 仅 Escalate 时填写 |
| `summary` | 总体总结 |
| `missing_details` | 按优先级从高到低列出：哪个问题、原话引用、缺什么 |
| `unsure_questions` | 模型拿不准的问题和原因 |
| `complete_questions` | 回答完整的问题列表 |

所有文字用非法律背景的人能看懂的平实英文，直接说请补充什么。输出另存为新文件，不覆盖原 CSV。

## 7. 三种结果的定义

结论由代码根据各问题的状态计算，不由模型直接给出。

| 结果 | 触发条件 | 谁来处理 |
|---|---|---|
| Ready to Submit | 11 个问题全部 `complete` | 填表人提交给 privacy 审核 |
| Not ready to submit | 没有 `unsure`，至少一个 `incomplete` | 填表人按 `missing_details` 补充后重新提交 |
| Escalate | 见下表 | privacy 团队 |

| `escalation_cause` | 含义 |
|---|---|
| `model_unsure` | 至少一个问题模型拿不准。同时有明确缺细节的问题时也算这一类 |
| `quote_check_failed` | 引用在原文里找不到，重做后仍如此 |
| `technical_error` | 调用模型或处理该行时出错，或输出重做后仍不完整 |

整次运行级别的错误不属于这三种结果，程序直接停止并报错。

## 8. Criteria skill

- 位置：项目内的 `.claude/skills/ropa-review/SKILL.md`，由 Agent SDK 原生加载。
- 内容分四部分：
  - 每个问题的通过标准和正反例。
  - 什么时候该说 `unsure`：回答模糊到无法判断、回答之间自相矛盾、criteria 没覆盖到。
  - 优先级 High、Medium、Low 的含义。
  - 写作要求：平实英文，不用术语。
- 通过标准来自现成的 criteria 文档。文档到位前先放占位内容。
- 改 criteria 只改这个文件，不改代码。

## 9. 技术方案

- 语言和库：Python 3.10 以上，`claude-agent-sdk`。
- 每行单独开一次全新的对话，行与行互不影响。
- 输入方式：单条消息输入，不用 streaming input。每次调用把完整的 JSON 一次性交给 agent。
- 重做方式：由我们自己的代码发起，不用 hook。重做时用 SDK 的 `resume` 接着同一次对话继续，agent 看得到原始表单和自己上次的回答，只改被指出的地方。最多重做 3 次。
- 引用：不用 citations 功能。Agent SDK 没有这个功能，Claude API 的 citations 也不能和结构化输出同时使用。改由模型写出原话、代码核对。
- 结构化输出：用 SDK 的 `output_format` 传入 JSON schema。
- agent 的权限：只允许使用 skill，不给读写文件和执行命令的权限。
- 模型：DeepSeek，通过它兼容 Anthropic 格式的接口接入。模型名称和接口地址做成配置项。
- 密钥：从环境变量读取，不写进代码。

## 10. 质量要求

- 代码符合 PEP8，用 Pylint 检查。
- 测试用 PyUnit 写法，由 pytest 运行，覆盖率达到 95%。
- 测试里对模型的调用全部用假对象替代，不联网。
- 密钥不提交到版本库。原始 CSV 不被修改。

## 11. 成功标准

- 用样例 CSV 运行脚本，能从头跑到尾。
- 每一行都有一个结论，且 Escalate 的行都填了 `escalation_cause`。
- 输出的列和格式符合第 6 条。
- 测试全部通过，覆盖率达到 95%，Pylint 无报错。
- 判断的准确率不在 MVP 验收范围内，留到下一阶段评估。

## 待提供的材料

- 样例 CSV，放进项目目录。
- criteria 文档。
- DeepSeek 的 API key、接口地址和模型名称，设成环境变量。
