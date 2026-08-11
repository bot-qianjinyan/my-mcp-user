# Inspect + MCP 怎么配合用

**一句话：** Inspect 跑评测时，把 MCP Server 当成「工具源」接给 Agent；模型在评测循环里调用的 tools，可以来自本仓库的 `user-mcp`（`http://127.0.0.1:3001/mcp`），而不必全用 Inspect 内置工具。

官方文档：[Model Context Protocol – Inspect](https://inspect.aisi.org.uk/tools-mcp.html)

## 分工

| 角色 | 做什么 |
|------|--------|
| **MCP Server**（本仓库 `:3001/mcp`） | 暴露 tools（也可有 resources / prompts；Inspect 主要用 tools） |
| **Inspect** | 出题 → Agent 推理并调工具 → 打分 → 记日志 |
| **模型** | 在 Agent 循环里决定何时调用哪些 MCP tools |

```
Dataset 出题
    ↓
Inspect Agent（如 react）
    ↓ 需要工具时
MCP Server（stdio / http / sandbox）
    ↓ 返回结果
Scorer 打分 → inspect view 看 transcript
```

同一份 MCP Server 可以同时服务 Cursor（交互）和 Inspect（评测）：**协议复用，场景不同**。

## Inspect 如何连接 MCP

Inspect 把 MCP Server 封装成 `ToolSource`，可直接传给 `tools=[...]`：

| 函数 | 场景 |
|------|------|
| `mcp_server_stdio()` | 本地起进程 |
| `mcp_server_http()` | 已部署的 HTTP / Streamable HTTP MCP（本仓库用这个） |
| `mcp_server_sandbox()` | MCP 跑在 Docker 等沙箱里 |

常用配套：

- `mcp_tools(server, tools=[...])` — 只暴露部分 tools，评测更可控  
- `mcp_connection(...)` — 有状态 Server 保持连接；`react()` 会自动处理  

## 与本仓库的对接

本仓库 MCP 端点：`http://127.0.0.1:3001/mcp`（Streamable HTTP）。

最小示例任务见：[`evals/user_mcp_smoke.py`](../evals/user_mcp_smoke.py)

前置：

1. 终端 1：`uvicorn app.main:app --host 127.0.0.1 --port 8000`  
2. 终端 2：`python -m mcp_server`（监听 `3001`）  
3. 安装：`pip install -r requirements-inspect.txt`，并配置模型 API Key  

运行：

```bash
source .venv/bin/activate
inspect eval evals/user_mcp_smoke.py --model openai/gpt-4o
inspect view
```

若当前环境没有模型 API Key，可用 mockllm 本地验证 Inspect→MCP 接线（不调用真实模型）：

```bash
python scripts/run_inspect_user_mcp_smoke_mock.py
```

## 心智对照

| 场景 | MCP 的角色 |
|------|------------|
| Cursor | 给 IDE Agent 用工具 |
| Inspect | 给评测 Agent 用工具，并记录、打分、对比模型 |

## 注意

- Inspect 主要消费 **Tools**；只有 tools 的 MCP Server 完全够用（见 `MCP_TOOLS_ONLY_SERVER.zh.md`）。  
- 评测前务必先起 API + MCP，否则 `mcp_server_http` 连不上。  
- 用 `mcp_tools` 收窄工具面，避免模型调用与题意无关的接口。  
- 需要模型 API Key；没有模型时无法真正跑通 Agent 评测。  
