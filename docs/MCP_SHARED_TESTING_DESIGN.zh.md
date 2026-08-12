# MCP 共享测试基础设施设计（Wiki 导读）

> **原文：** [Testing Design — shared test infrastructure for mcp-servers（WIP）](https://liveramp.atlassian.net/wiki/spaces/CI/pages/5720768530)  
> **状态：** proposal · **Owner：** platform · **原文更新：** 2026-08-11  
> **本文用途：** 用中文介绍该 Wiki 的核心思路、分层模型与落地方式，便于本地阅读与对照本仓库测试改进。

相关文档：

- `TESTING_IMPROVEMENT_PLAN.zh.md` — 本仓库（my-mcp）的测试改进计划
- `MCP_L2_L4_EXPLAINED.zh.md` — L2 Mock / L4 真传输速查

---

## 一句话总结

用**一套共享测试库**统一测所有 MCP Server，而不是每个 Server 各自重造轮子；测试所强制执行的 tool 契约来自 `TOOL_CONVENTIONS.md`。

---

## 1. 要解决什么问题

`servers/` 里有很多 MCP Server，构建方式分两类：

- 手写 **FastMCP**
- **OpenAPI 生成的 SDK**

当前缺口有三：

| 缺口 | 含义 |
|---|---|
| **临时拼凑** | 各 Server 自写测试，没有统一「测得好」的标准 |
| **表面无守卫** | 真实契约是 `tools/list`；改名、改类型、删除、description 撑爆 payload（见 [PR #229](https://github.com/LiveRamp/mcp-servers/pull/229)）都拦不住，也无法验证 LLM 是否用对 tools |
| **无复用** | 「怎么测 MCP」大多是协议层通用逻辑，却被每个 Server 重写；`servers/template/` 也不带测试 |

---

## 2. 能带来什么价值

- 无论怎么构建，所有 Server 共用同一质量标准
- 表面漂移 / payload 膨胀在测试里失败，而不是在生产拖垮 Agent
- 新 Server 从 `template/` 继承套件，边际成本接近零
- 失败能回溯到 `TOOL_CONVENTIONS.md`，推动设计改进，而不只是当闸门
- 除 L5 外都在本地跑、不需凭证，适合进 CI gate

---

## 3. 分层模型：L 系列 × U 系列

Server 夹在两个边界之间，测试沿两条轴展开，并在一个接缝交汇：

```
Agent / Client
      ↕  L 系列（MCP 表面）—— 本文档与共享库的重点
  MCP Server
      ↕  U 系列（上游边缘）—— 多为 per-server 内容
 Upstream APIs
```

| 轴 | 边界 | 共享程度 |
|---|---|---|
| **L 系列** | Server ↔ Agent | 协议驱动、与具体 Server 无关 → **抽进共享库** |
| **U 系列** | Server ↔ Upstream APIs | 钉死的 specs/contracts → **大多跟各 Server** |
| **接缝** | 下游错误 → MCP 原生 `ToolError` | 由 L 系列用 L2 harness 验证 |

> **本文档（及共享库）讲的是 L 系列**；U 系列另跟。唯一共享的上游件是 **U0 熔断器**（在 runtime SDK 自带单测）。

### 3.1 L / U 层速查

| Layer | 验证什么 | 进 CI gate？ |
|---|---|---|
| **L0 Smoke** | 进程启动、`tools/list`、容器 `/health` | 是 |
| **L1 Tool contract** | 合法命名（≤64）、有效 `inputSchema`、对齐 `TOOL_CONVENTIONS.md` 可机械检查部分 | 是 |
| **L1b Surface drift** | `tools/list`（+ resources/prompts）指纹 vs golden snapshot；防改名/删除/改类型/payload 膨胀 | 是 |
| **L2 Behaviour** | 在 httpx 边界构造正确上游请求；失败以结构化 `ToolError` 暴露 | 是 |
| **L2b Capability completeness** | OpenAPI operation 全映射到 tool（spec 生成 Server） | 是 |
| **L3 Permissions** | 假 `PermissionChecker`：拒绝未授权、允许已授权 | 是 |
| **L4 / L4-lite** | 协议行为（未知 tool、缺参拒绝）；ASGI：401、JSON-RPC、handshake、`/health`+`/metrics` | 是 |
| **L5 E2E** | 同一套 L1/L4-lite 指向真实环境 + 真 token | 否 |
| **L6 Agent eval** | LLM 选对 tool、多步编排、参数、恢复；答案质量（LLM judges） | 否 |
| **U0 Circuit breaker** | CLOSED→OPEN→HALF_OPEN、重试策略、并发 | 是 |
| **U1 Spec compatibility** | 手写 parser 依赖的字段仍在钉死的 OpenAPI 里 | 是 |
| **U2 Consumer contract (Pact)** | 代码依赖的精确响应形状 | 是（broker 就绪后） |
| **U3 Nightly drift** | upstream `latest` vs 钉死版本 | 否 |

---

## 4. 核心设计原则

### 4.1 机制 vs 内容

| | 含义 | 放哪里 |
|---|---|---|
| **机制** | *怎么*测（协议驱动、与 Server 无关） | 共享库，**只写一次** |
| **内容** | *测什么*（Server 特有） | 跟各自 Server |

例：「如何检查某个 tool 被选中」是共享机制；「reality-TV prompt 应选 `search_marketplace_segments`」是 `liveramp-product-mcp` 的内容。

| Layer | 共享机制 | Per-server 内容 |
|---|---|---|
| L1 | naming / schema / convention 断言 | （无） |
| L1b | fingerprint + budget 算法 | golden snapshot |
| L2 | respx stub + header 注入 | routes + fixtures |
| L3/L4 | ASGI harness + 假 PermissionChecker | tool → permission 映射 |
| L4-lite | 协议行为断言 | （无） |
| L6 | scorers + factory + stub | dataset + fixtures |

### 4.2 Adapter（硬前置）

两种入口统一成一个已连接 client，共享套件**不按 Server 类型分支**：

- **FastMCP** → `fastmcp.Client(mcp)`
- **SDK** → `mcp.shared.memory.create_connected_server_and_client_session`  
  （不要用手搓 `dispatch_mcp_method`，会绕过真实协议路径）

### 4.3 确定性后端（L2 / L6 共用）

除 L5 外不碰真实资源，三类外部依赖全部切断：

| 依赖 | 切断方式 |
|---|---|
| Upstream APIs | `respx` 在 httpx 边界拦截（真实 URL/params/body 仍构造） |
| Token / headers | monkeypatch `get_http_headers` |
| Permissions | `LRAuth(..., checker=假 PermissionChecker)` |

- **L2**：进程内跑 Server，打补丁本地 httpx 即可  
- **L6**：subprocess 启动 → mock 必须在子进程内（`stub_server.py`）

---

## 5. 落地方式（实现要点）

### 5.1 三种交付形态

1. **完全共享层（L1 / L1b / L4-lite）** → `MCPContractSuite` 基类；每个 Server 三行子类 opt-in  
2. **内容层（L2 / L3 / L6）** → 共享 helper，不是自动收集的测试；fixtures/routes/dataset 各 Server 自备  
3. **Adapter** → `mcp_client` fixture（依赖 per-server 的 `server_app`）

```python
# 共享：写一次
class MCPContractSuite:
    async def test_tool_names_follow_conventions(self, mcp_client): ...
    async def test_surface_matches_snapshot(self, mcp_client, snapshot_json): ...
    async def test_init_and_bad_calls_rejected(self, mcp_client): ...

# 各 Server：三行
from liveramp_mcp_testing.suite import MCPContractSuite
class TestContract(MCPContractSuite):
    pass
```

### 5.2 打包

独立开发包 `liveramp_mcp_testing`（与 `liveramp_mcp_sdk` / `lrauth` 并列），**不进** runtime SDK：

```
shared/testing/liveramp_mcp_testing/
  client.py    # adapter fixture
  suite.py     # MCPContractSuite（L1 + L1b + L4-lite）
  surface.py   # L1b fingerprint + budget
  stub.py      # L2 / L6 deterministic backend
  asgi.py      # L3 / L4 harness
  scorers.py   # L6（inspect 懒加载）

servers/<name>/tests/{protocol,eval}/
servers/template/tests/                  # 新 Server 脚手架
```

extras：`protocol` / `backend` / `eval`；各 Server 在自己的 `pyproject.toml` pin，升级按 Server bump，不全仓翻转。

### 5.3 分阶段（先低风险）

1. L1b 垂直切片（基类 + adapter + 打包一次验证）
2. Adapter：一个 FastMCP + 一个 SDK（如 `cleanroom-mcp`）
3. 补齐 L1、L4-lite，铺到第 2 个 Server
4. 抽出 `stub.py`（L2 / L6 共用）
5. 抽出 L6 `scorers.py`
6. 填满 `servers/template/tests/`

### 5.4 CI 边界

| | 范围 |
|---|---|
| **进 gate** | L0–L4，密封、无凭证 |
| **不进 gate** | L5（真 token）、L6（LLM key）；夜间/按需看趋势 |

### 5.5 Non-goals

- 不替代 Server 特有单测（helpers / formatters / parsers）
- 不用 L6 卡 merge
- 不在内存 client 够用时再造定制 harness
- 不把 U 系列抽进本库（除 U0 已在 runtime SDK）

---

## 6. 风险与缓解（摘要）

| 风险 | 缓解 |
|---|---|
| Adapter 泄漏 Server 类型差异 | Adapter 当前置；套件保持无分支 |
| 共享库一次搞挂所有 Server | 版本化包 + per-server pin；snapshot 也按 Server |
| Tool 名断言变脆 | 保持窄，只拦有意回归 |
| L6 harness 维护不足 | 不进 gate；长期目标 `inspect_ai` |

---

## 7. 后续：Backstage Scorecards

测试跑起来后，用 Backstage **Tech Insights**（facts → checks → scorecard）把「这个 Server 测得好不好」挂到 catalog，而不是埋在 CI 日志。

前置：先把 `mcp-servers` 注册进 catalog（一个 System + 每 Server 一个 Component）。

Scorecard 示例 checks：L1 绿、L1b snapshot 已提交、L2+L3/L4 绿、coverage 阈值、L6 通过率（仅展示）、owner + TechDocs。

> Backstage 回答 catalog 级「测得好不好」；L6 eval traces 仍看 **Langfuse**——两套表面分开。

---

## 8. 对本仓库（my-mcp）的启示

对照本仓库现状（单 Server + scripts 冒烟），Wiki 设计可直接映射为：

| Wiki 层 | 本仓库可落地动作 |
|---|---|
| L0 / L1 / L1b / L4-lite | 优先用 pytest 建协议层套件（见 `TESTING_IMPROVEMENT_PLAN.zh.md`） |
| L2 | 用 respx mock FastAPI，断言 MCP tool 打出正确 REST（见 `MCP_L2_L4_EXPLAINED.zh.md`） |
| L4 | Streamable HTTP 真传输：`initialize`、缺参/未知 tool | 
| L5 / L6 | 先不进 gate；有需要再加 E2E / Inspect eval |

不必一次建完整共享库；先把 **机制 vs 内容** 和 **L 分层** 用起来，后续再抽公共 helper。

---

## 参考

- Wiki：[Testing Design — shared test infrastructure for mcp-servers](https://liveramp.atlassian.net/wiki/spaces/CI/pages/5720768530)
- 相关 PR：[mcp-servers#229](https://github.com/LiveRamp/mcp-servers/pull/229)（description / payload 膨胀）
