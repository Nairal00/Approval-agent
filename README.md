# 申请表预审 Agent

业务部门通过提交 ROPA（个人数据处理活动记录）后，Agent预审每份表格并给出改进意见。

Sample Input 见 [input.csv](input.csv)
Sample Output 见 [input_reviewed.csv](input_reviewed.csv)

| 结论 | 详细说明 | 后续操作 |
|---|---|---|
| Ready to Submit | 无需额外补充信息 | 业务人员可以正式提交审核 |
| Not ready to submit | 有问题回答得太笼统，需补充修改申请 | 业务人员按清单补充后重新提交 |
| Escalate | Agent不确定，或者Agent运行中出先技术问题 | 交给隐私合规团队人工处理 |

Agent只判断申请表是否能进行下一步的评审，不判断申请是否合规。

## 项目背景和痛点

因监管需要，ROPA表格法律专业术语较多，业务人员提交的ROPA质量参差不齐。
痛点：隐私合规团队通常花大量时间和业务部门反复沟通项目申报细节，才开始真正的项目审核。
此Agent主要负责自动化"业务部门提交的信息够不够评审"。

## Agent输出+代码核对

特设以下核验机制减少Agent幻觉：

- **每个问题都必须看到。** 程序会检查 AI 是否对每个问题都给出了判断，一个不漏，也不重复。
- **引用必须是原话。** AI 说"你写的是……"时，程序会逐字核对，确认填表人真的写过这句话。
- **不合格就打回去改。** 检查没通过时，程序会把问题列出来让 AI 修改，最多改 3 次。
- **最终结论由代码评判。** AI 只负责逐题判断"Ready to Submit / Ready to Submit / Escalate"，申请表最终结论由每题的结果代码累计计算，杜绝结论和明细对不上。
- **拿不准就交给人。** 只要 AI 不确定，或者改了 3 次仍不合格，就标记为 Escalate 并写明原因，绝不默认放行。
- **只做这一件事。** AI 只能参考审查标准，不能读写其他文件或执行其他操作。填表人的姓名不会发给 AI。

---

## 使用方法

### 安装

需要 Python 3.10 以上。

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### 配置

参照 [.env.example](.env.example)，在项目根目录建一个 `.env` 文件：

```
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_AUTH_TOKEN=你的 DeepSeek API key
ROPA_MODEL=claude-sonnet-4-5
```

- 程序启动时会自动读取 `.env`。如果终端里已经设了同名的环境变量，以终端里的为准。
- `ROPA_MODEL` 不设置时默认用 `claude-sonnet-4-5`。DeepSeek 的 Anthropic 兼容接口会把它映射到自己的模型。
- `.env` 已写在 `.gitignore` 里，不会被提交。不要把 key 写进代码或发到任何对话里。

### 运行

```bash
python -m ropa_agent.cli input.csv
```

程序会逐行打印结论，最后在同一目录生成 `input_reviewed.csv`。原 CSV 不会被修改。

结果文件在原有列之后追加 6 列：

| 列名 | 内容 |
|---|---|
| `verdict` | 结论 |
| `escalation_cause` | 仅 Escalate 时填写 |
| `summary` | Agent对于申请表的概括；Agent出错时附上问题说明 |
| `missing_details` | 按优先级 High、Medium、Low 排列：哪道题需要重填、申请表原话、还需补充哪些细节方便评估 |
| `unsure_questions` | Agent无法判断的问卷题号和原因 |
| `complete_questions` | 回答完整的题号以及问题 |

### 修改审查标准

审查标准写在 [.claude/skills/ropa-review/SKILL.md](.claude/skills/ropa-review/SKILL.md)。改标准只改这个文件，不用动代码。

`.claude` 文件夹以点开头，在 Finder 里默认隐藏，按 `Cmd + Shift + .` 可以显示出来。

---

## 技术细节

完整需求见 [PRD.md](PRD.md)。

### 处理流程

```
input.csv
  │  读取并校验列名（缺列则停止）
  ▼
每一行 ──► 固定结构 JSON（去掉 Name 和 Timestamp）
  │
  ▼
Agent 按 skill 判断 ──► 第 1 关：SDK 按 JSON schema 校验格式
  │
  ▼
第 2 关评判结论完整性 + 第 3 关是否真实引用 ──不通过──► 带问题清单让Agent重做（最多 3 次）
  │ 通过
  ▼
代码计算 verdict ──► 写入 input_reviewed.csv
```

### 输入

每一行 CSV 由代码转成固定结构的 JSON：`submission_id`（如 `row-2`）加上 11 条 `answers`，每条包含固定的 `question_id`（如 `retention_period`）、问题原文和填表人回答原文。

### 输出的三道检测

| 关卡 | 谁来查 | 查什么 | 没通过时 |
|---|---|---|---|
| 1. 格式 | SDK | 符合 `output_format` 里的 JSON schema：字段齐全，`status` 和 `priority` 只能取枚举值 | SDK 自动重新生成 |
| 2. 完整性 | `validators.check_completeness` | 11 个 `question_id` 各出现一次；`incomplete`是否填了 `missing_detail` 和 `priority`；`unsure`是否填了 `unsure_reason`；`submission_id` 与输入一致 | 让 agent 重做 |
| 3. 引用真实性 | `validators.check_quotes` | `quoted_answer` 是否出自该题原始回答，比对时忽略空白和大小写；原回答为空时引用也必须为空 | 让 agent 重做 |

### 重做机制

第 2、3 关的问题合并成一张清单，一次性作为新消息发给 agent，并设置 `resume=<上次的 session_id>` 接着同一次对话。agent 看得到原始表单和自己上次的回答，只改被指出的地方。两关合计最多重做 3 次（`MAX_REDOS`）。

### 结论和升级原因

`verdict.compute_verdict` 只根据各题 `status` 计算：有一题是 `unsure` 则申请表整体判定为 Escalate，否则有一题是 `incomplete` 则申请表整体判定为 Not ready to Submit。如果以上状况全无， 申请表整体判定为Ready to Submit。

| `escalation_cause` | 含义 |
|---|---|
| `model_unsure` | 至少一题 `unsure` |
| `quote_check_failed` | 重做 3 次后仍有引用核对不上 |
| `technical_error` | SDK 调用出错、没有结构化结果，或重做 3 次后仍不完整 |

### 错误分级

| 范围 | 情况 | 处理 |
|---|---|---|
| 单行 | 模型调用出错、处理该行时出现任何异常 | 该行 Escalate，其余行继续 |
| 整次运行 | 文件不存在、列缺失、没有 API key、HTTP 401（key 无效）、HTTP 402（余额不足） | 报错退出，不生成结果文件 |

### Agent 配置

`reviewer.build_options` 里的关键设置：

- `tools=["Skill"]` 加 `skills=["ropa-review"]`：只开放 Skill 工具，且只能加载这一个 skill，没有读写文件、执行命令的能力。
- `setting_sources=["project"]`：只加载项目内设置，不读个人全局的 `~/.claude/CLAUDE.md`。
- `max_turns=10`：防止 agent 陷入循环。
- `system_prompt`：明确告诉 agent，回答内容是填表人写的数据，不是给它的指令。

### 项目结构

| 文件 | 作用 |
|---|---|
| `ropa_agent/config.py` | 11 个问题代号对应的 CSV 列名、模型设置、读取 `.env` |
| `ropa_agent/csv_io.py` | 读 CSV、校验列名、写结果文件 |
| `ropa_agent/payload.py` | 把一行转成输入 JSON；定义输出 schema 和提示词 |
| `ropa_agent/validators.py` | 第 2 关完整性检查、第 3 关引用核对 |
| `ropa_agent/verdict.py` | 根据各题状态计算结论 |
| `ropa_agent/formatter.py` | 把结果拼成 CSV 单元格里的文字 |
| `ropa_agent/reviewer.py` | 调用 Agent SDK、重做循环、判断是否停止整次运行 |
| `ropa_agent/cli.py` | 命令行入口 |
| `ropa_agent/errors.py` | 让整次运行停止的错误类型 |
| `tests/` | 每个模块一个测试文件，模型调用全部用假对象替代，不联网 |

### 测试

```bash
python -m pytest --cov=ropa_agent --cov-fail-under=95
```

```bash
pylint ropa_agent tests
```
