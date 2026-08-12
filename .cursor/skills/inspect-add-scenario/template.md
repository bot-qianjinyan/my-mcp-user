# Inspect 场景模板

复制到 `evals/<name>_scenarios.py` 后改名与步骤。

```python
"""<一句话说明场景>。

运行：
    ./scripts/run_inspect_gemini.sh google/gemini-3.6-flash evals/<name>_scenarios.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from inspect_ai import Task, task

from evals._common import ALL_AUTH_BILL_TOOLS, agent_task, unique_user


@task
def example_flow() -> Task:
    """<任务 docstring>。"""
    username, email, password = unique_user("ex")
    prompt = f"""你只能通过提供的 MCP tools 完成任务，不要编造结果。

步骤：
1. register_user：username={username}, email={email}, password={password}
2. login_user：获取 access_token
3. <用真实 tool 名写清参数与校验点>
4. 一句话总结；最终答案必须原样包含：EXAMPLE_OK

任一步失败则说明原因，且不要写 EXAMPLE_OK。
"""
    return agent_task(
        prompt=prompt,
        target="EXAMPLE_OK",
        tools=ALL_AUTH_BILL_TOOLS,
        metadata={"username": username, "scenario": "example_flow"},
        attempts=3,
    )
```

## 双用户模板要点

- 两次 `unique_user("owner")` / `unique_user("peer")`
- Prompt 中分别记下 `owner_token` / `peer_token`
- 写明「切换用户时必须使用对应用户的 access_token」
- `attempts` 建议 ≥ 5
