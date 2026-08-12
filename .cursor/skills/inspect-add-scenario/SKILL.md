---
name: inspect-add-scenario
description: >-
  Add Inspect AI evaluation scenarios to the my-mcp repo (evals/, MCP tools,
  Gemini runner). Use when the user asks to add Inspect scenarios, eval tasks,
  bill/user MCP test flows, or extend inspect evals for this repository.
---

# 为本仓库添加 Inspect 场景

面向 `my-mcp`：用 Inspect + 本仓库 Streamable HTTP MCP（`:3001/mcp`）新增评测任务。

## 必读现状

先读这些再改：

- `evals/_common.py` — `agent_task` / `unique_user` / tool 列表
- `evals/bill_mcp_scenarios.py`、`evals/user_mcp_smoke.py` — 现有 `@task` 范例
- `mcp_server/server.py` 或 `tests/mcp/surface.golden.json` — 可用 tool 名
- `docs/INSPECT_MCP.zh.md` — 运行方式
- `scripts/run_inspect_gemini.sh` — `suite` 列表是否要更新

架构硬约束：

```
Inspect Agent → MCP :3001 → REST API :8000 → SQLite
```

- Inspect **不会**自动起 API/MCP；评测会**真实写库**。
- 只用 MCP **Tools**（本仓库 Inspect 路径不测 Resources/Prompts）。

## 工作流

复制并跟踪：

```
- [ ] 1. 选定场景与通过标记（如 FOO_OK）
- [ ] 2. 确认所需 tool 名（对照 surface.golden.json）
- [ ] 3. 新建或扩展 evals/*.py
- [ ] 4. sys.path 引导 + from evals._common import ...
- [ ] 5. 用 agent_task(...) 组装 Task
- [ ] 6. 如需进 suite，更新 run_inspect_gemini.sh
- [ ] 7. 更新 docs/INSPECT_MCP.zh.md 场景表
- [ ] 8. 本地 load 校验（见下方）
```

### 1. 场景设计

每个 `@task` 应：

- **一个主目标**（CRUD / 分享 / 点赞 / 资料…）
- **确定性通过标记**（大写 `XXX_OK`），用 `includes()` 判分
- Prompt 里写清分步 +「失败则不要写 XXX_OK」
- 用户名用 `unique_user("prefix")`，避免撞库
- 多用户场景（如分享）在 prompt 中明确 **token 不要混用**

### 2. 落盘位置

| 类型 | 放哪里 |
|------|--------|
| 用户冒烟/资料 | `evals/user_*.py` |
| 账单流程 | `evals/bill_mcp_scenarios.py`（优先追加）或新文件 `evals/bill_*.py` |
| 跨域新能力 | 新文件 `evals/<domain>_scenarios.py` |

同一文件可多个 `@task`；`inspect eval file.py` 会跑该文件全部 task。

### 3. 文件模板（必须）

每个 eval 文件顶部必须有 path bootstrap（Inspect 按路径加载时否则 `No module named 'evals'`）：

```python
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from inspect_ai import Task, task
from evals._common import ALL_AUTH_BILL_TOOLS, agent_task, unique_user
```

完整样例见 [template.md](template.md)。

优先复用：

```python
agent_task(
    prompt=prompt,
    target="FOO_OK",
    tools=ALL_AUTH_BILL_TOOLS,  # 或 USER_TOOLS / 显式 list
    metadata={"scenario": "foo_flow"},
    attempts=3,  # 多步可 4–5
)
```

**不要**手写第二套 `mcp_server_http`/`react`，除非 `_common.agent_task` 不够用。

### 4. Tool 选择

- 最小权限：只列出场景需要的 tools
- 账单类默认可用 `ALL_AUTH_BILL_TOOLS`（含注册登录）
- 新 MCP tool 先加到 `mcp_server/server.py` 并更新 `surface.golden.json`，再写 eval

### 5. 接入 suite / 文档

若希望 `./scripts/run_inspect_gemini.sh ... suite` 包含新文件，在 `scripts/run_inspect_gemini.sh` 的 `suite` 分支追加路径。

同步改 `docs/INSPECT_MCP.zh.md` 场景表一行。

### 6. 校验（不强制真跑 Gemini）

```bash
source .venv/bin/activate
python - <<'PY'
from inspect_ai._eval.loader import load_tasks
tasks = load_tasks(["evals/YOUR_FILE.py"], {})
print([t.name for t in tasks])
PY
```

真跑（需 Key + SSL 脚本约定）：

```bash
export GOOGLE_API_KEY='...'
./scripts/run_inspect_gemini.sh google/gemini-3.6-flash evals/YOUR_FILE.py
# 或单 task：
./scripts/run_inspect_gemini.sh google/gemini-3.6-flash evals/YOUR_FILE.py@your_task_name
inspect view
```

## 常见坑

| 症状 | 处理 |
|------|------|
| `No module named 'evals'` | 文件头 path bootstrap；脚本已设 `PYTHONPATH` |
| `ConnectError` / streamablehttp | API:8000 + MCP:3001 未起 → `./scripts/start_services.sh` |
| `ClientConnectorCertificateError` | Netskope：用 `run_inspect_gemini.sh`（组合 CA） |
| Agent 乱调无关 tool | `mcp_tools(..., tools=[...])` 收窄 |
| 评分总失败 | 确认最终 `submit` 答案含精确标记（大小写一致） |

## 完成标准

- [ ] 新 `@task` 可被 `load_tasks` 解析
- [ ] Prompt / target / tools / metadata.scenario 齐全
- [ ] 文档或 suite（若适用）已更新
- [ ] 未把 API Key 写入仓库文件
