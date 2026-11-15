# ROPA 预审 Agent

业务部门通过 Google Form 提交 ROPA（个人数据处理活动记录）。这个工具会在 privacy 团队审核之前，先帮忙看一遍每份提交：信息够不够完整，缺了什么，用平实的英文告诉填表人该补充哪些内容。

## 它解决什么问题

提交的填写质量参差不齐。以前 privacy 团队要先花时间和业务部门来回沟通，把缺的细节补齐，才能开始真正的审核。这个工具把"信息够不够"这一步提前做掉：填表人能更早知道要补什么，privacy 团队也能把时间留给真正需要判断的案子。

它只判断信息是否足够，不判断这项数据处理是否合规。

## 你会得到什么

每份提交会得到三种结论之一：

| 结论 | 意思 | 下一步 |
|---|---|---|
| Ready to Submit | 每个问题都回答得足够清楚 | 填表人可以正式提交审核 |
| Not ready to submit | 有问题回答得太笼统或没填 | 填表人按清单补充后重新提交 |
| Escalate | 工具拿不准，或者运行中出了问题 | 交给 privacy 团队人工处理 |

对于没准备好的提交，工具会列出缺了什么，按重要程度排好序，并引用填表人的原话，比如：

> [High] 11. How long will personal information will be retained? - You wrote: "as long as needed". Please state a specific period, for example 2 years after the contract ends.

## 它怎么保证结果可靠

AI 有时会不稳定：可能漏看某个问题，可能编造填表人没说过的话，也可能前后矛盾。这个工具不完全依赖 AI 自觉，而是在它周围加了几道由程序把关的检查：

- **每个问题都必须看到。** 程序会检查 AI 是否对每个问题都给出了判断，一个不漏，也不重复。
- **引用必须是原话。** AI 说"你写的是……"时，程序会逐字核对，确认填表人真的写过这句话。
- **不合格就打回去改。** 检查没通过时，程序会把问题列出来让 AI 修改，最多改 3 次。
- **结论由固定规则得出。** AI 只负责逐题判断"够 / 不够 / 拿不准"，最终结论按固定规则计算，不会出现结论和明细对不上的情况。
- **拿不准就交给人。** 只要 AI 不确定，或者改了 3 次仍不合格，就标记为 Escalate 并写明原因，绝不默认放行。
- **只做这一件事。** AI 只能参考审查标准，不能读写其他文件或执行其他操作。填表人的姓名不会发给 AI。

这些检查能保证结果格式完整、引用真实、结论前后一致。但 AI 对"回答够不够清楚"的判断本身是否准确，还需要拿人工审核的结论对比来评估，这是下一阶段的工作。

---

## 使用方法

### 安装

需要 Python 3.10 以上。系统自带的 Python 3.9 版本不够。

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
| `summary` | 总体总结；出错时附上问题说明 |
| `missing_details` | 按优先级 High、Medium、Low 排列：哪道题、填表人原话、请补充什么 |
| `unsure_questions` | 拿不准的题目和原因 |
| `complete_questions` | 回答完整的题目 |

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
第 2 关完整性 + 第 3 关引用 ──不通过──► 带问题清单 resume 重做（最多 3 次）
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
| 2. 完整性 | `validators.check_completeness` | 11 个 `question_id` 各出现一次；`incomplete` 填了 `missing_detail` 和 `priority`；`unsure` 填了 `unsure_reason`；`submission_id` 与输入一致 | 让 agent 重做 |
| 3. 引用真实性 | `validators.check_quotes` | `quoted_answer` 是该题原始回答的子串，比对时忽略空白和大小写；原回答为空时引用也必须为空 | 让 agent 重做 |

第 3 关取代了 citations 功能。Agent SDK 没有 citations，Claude API 的 citations 也不能和结构化输出同时使用，所以改由模型写出原话、代码核对。

### 重做机制

第 2、3 关的问题合并成一张清单，一次性作为新消息发给 agent，并设置 `resume=<上次的 session_id>` 接着同一次对话。agent 看得到原始表单和自己上次的回答，只改被指出的地方。两关合计最多重做 3 次（`MAX_REDOS`）。

### 结论和升级原因

`verdict.compute_verdict` 只根据各题 `status` 计算：有 `unsure` 则 Escalate，否则有 `incomplete` 则 Not ready，否则 Ready。

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
