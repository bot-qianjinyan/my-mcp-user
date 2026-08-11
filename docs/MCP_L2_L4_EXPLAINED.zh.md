# MCP 测试分层速查：L2 Mock 与 L4 真传输

> 用途：以后忘记「L2 / L4 到底在测什么」时回来看。  
> 范围：结合本仓库 `my-mcp`（FastAPI + Streamable HTTP MCP）举例。  
> 相关文档：`TESTING_IMPROVEMENT_PLAN.zh.md`（整体改进计划）

---

## 0. 先记住一条调用链

```
MCP Client  ──① 协议/传输──▶  MCP Server (tools/resources/prompts)
                                    │
                                    │ ② httpx 调业务 API
                                    ▼
                              FastAPI :8000  (/api/users, /api/bills)
```

| 编号 | 含义 | 对应测试关注点 |
|---|---|---|
| ① | Client 怎么连上 MCP（stdio / Streamable HTTP、`initialize`） | **L4 真传输** |
| ② | MCP tool 怎么转发到你们的 REST | **L2 Mock** |
| 业务本身 | 注册、记账、分享、点赞对不对 | `tests/api/` 或 scripts E2E |

**一句话：**

- **L2 Mock** = 验证「MCP 有没有正确调用 FastAPI」  
- **L4 真传输** = 验证「外面能不能通过 `http://...:3001/mcp` 按 MCP 协议连上 Server」

---

## 1. L2 Mock（行为层）是什么？

### 1.1 要回答的问题

`create_bill` 调用“成功”了，就一定打对了 `POST /api/bills` 吗？

**不一定。** 可能：

- path 写成了 `/api/bill`（少了 s）
- 忘了带 `Authorization: Bearer ...`
- JSON 字段名错了（`name` 而不是 `title`）

如果测试只断言「返回了 ok」，这些接线错误可能漏掉。

### 1.2 做法

**不启动真实 API**，用 Mock（如 `httpx.MockTransport` / `respx`）假装成 API，  
只检查 MCP 发出去的 HTTP **方法 / URL / Header / Body** 是否正确。

### 1.3 本仓库例子（示意）

真实 tool 逻辑大致是：

```text
create_bill(access_token, title, amount, ...)
  → POST http://127.0.0.1:8000/api/bills
  → Header: Authorization: Bearer <access_token>
  → JSON: {"title": "...", "amount": ...}
```

L2 测试想确认的是：

```text
给定 call_tool("create_bill", {access_token: "fake-token", title: "咖啡", amount: 18.5})

Mock 应记录到：
  method = POST
  url    = http://127.0.0.1:8000/api/bills
  headers["Authorization"] = "Bearer fake-token"
  json["title"] == "咖啡"
  json["amount"] == 18.5（或等价小数）
```

### 1.4 生活类比

| 测试 | 类比 |
|---|---|
| API 单测 (`tests/api/`) | 厨房自己会不会做菜 |
| **L2 Mock** | 店员有没有把**正确菜单单**递给厨房窗口（先不真开火） |
| E2E / scripts | 顾客进店点单，最终能不能喝到咖啡 |

### 1.5 L2 测什么 / 不测什么

| 测 | 不测（留给别处） |
|---|---|
| tool → REST 的 method/path/headers/body | 账单分享权限等业务规则（`tests/api/`） |
| 错误状态码如何被包装成 tool 结果 | Streamable HTTP 握手（那是 L4） |

### 1.6 当前仓库状态

- **已实现**：`tests/mcp/test_tool_http_wiring.py`（`httpx.MockTransport`）  
- 手工 E2E（`scripts/test_mcp_*_client.py`）仍打真 API，作整链路补充

---

## 2. L4 真传输（传输层）是什么？

### 2.1 要回答的问题

内存里的 `Client(mcp)` 能 `list_tools` / `call_tool`，  
就代表 Cursor 连 `http://127.0.0.1:3001/mcp` 也一定能用吗？

**不一定。** 可能：

- 端口错了、路径不是 `/mcp`
- 没有正确完成 MCP `initialize`（版本/能力协商）
- Content-Type / Session / Streamable HTTP 细节不兼容

内存客户端往往**绕过真实 HTTP 传输**，所以测不到这些问题。

### 2.2 做法

真的用 **HTTP** 访问 MCP 端点，走完整协议握手，例如：

```python
# 不是：Client(mcp)          ← 内存直连，几乎无真实传输
# 而是：Client("http://127.0.0.1:3001/mcp")  ← 真 HTTP / Streamable HTTP

async with Client("http://127.0.0.1:3001/mcp") as client:
    # 内部会先 initialize
    tools = await client.list_tools()
    assert "create_bill" in [t.name for t in tools.tools]
```

### 2.3 还可以测的场景

| 场景 | 期望 |
|---|---|
| 合法 `initialize` + `tools/list` | 成功，返回工具列表 |
| 访问错误路径 `/` 或 `/api` | 不是合法 MCP 会话 |
| 畸形 JSON-RPC body | 协议错误，进程不应直接崩溃 |

### 2.4 生活类比

| 方式 | 类比 |
|---|---|
| `Client(mcp)` 内存 | 两个人在同一间屋里直接说话 |
| **L4 真传输** | 打电话到 `3001` 分机：先接通、报身份，再点菜 |

### 2.5 L4 测什么 / 不测什么

| 测 | 不测（留给别处） |
|---|---|
| `/mcp` 能否握手、列工具 | tool 是否打对 `/api/bills`（那是 L2） |
| 传输/会话是否可用 | 分享/点赞业务规则（`tests/api/`） |

### 2.6 当前仓库状态

- **L4 已落地**：`tests/mcp/test_streamable_http_transport.py`
  - fixture 在随机端口拉起 `mcp.streamable_http_app()`
  - 用 `Client("http://127.0.0.1:<port>/mcp")` 做握手 + `tools/list` / `call_tool`
  - 校验错误路径 `/` 不是 MCP 端点
- 标记：`@pytest.mark.e2e`；`make test` / `make test-mcp` 会跑；也可 `make test-e2e` 只跑传输层
- **L2 Mock 已落地**：`tests/mcp/test_tool_http_wiring.py`（不起真实 API）
- 手工脚本 `scripts/test_mcp_*_client.py` 仍可连本机 `:3001` 做完整业务 E2E

本仓库本地手工 MCP 端点默认：

```text
http://127.0.0.1:3001/mcp
```

启动：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000   # 业务 API（tool 会回调它）
python -m mcp_server                                 # MCP :3001
```

---

## 3. 和本仓库其他测试层怎么排

```text
便宜、快、默认进 make test
─────────────────────────────────
L1 / L1b / L4-lite / L1c   协议表面与规矩（已有 tests/mcp/）
tests/api/                 REST 业务（已有）
L2 Mock                    tool→REST 接线（已有）
L4 真传输                  fixture 自启 HTTP /mcp（已有）
─────────────────────────────────
更重、常要起服务
L5 / scripts E2E           真 API + 真 MCP 整链路（已有 scripts/）
```

对照表：

| 层级 | 一句话 | 本仓库位置 | 状态 |
|---|---|---|---|
| L1 工具契约 | 菜单字段/schema 合法 | `tests/mcp/test_tool_contract.py` | 已有 |
| L1b 表面指纹 | 工具名集合别乱改 | `tests/mcp/surface.golden.json` | 已有 |
| L4-lite 协议行为 | 未知 tool / 缺参应失败 | `tests/mcp/test_protocol_behavior.py` | 已有 |
| L1c Resource/Prompt | read / get_prompt 能返回 | `tests/mcp/test_resources_prompts.py` | 已有 |
| **L2 Mock** | tool 是否打对 REST | `tests/mcp/test_tool_http_wiring.py` | **已有** |
| **L4 真传输** | `/mcp` HTTP 握手 | `tests/mcp/test_streamable_http_transport.py` | **已有** |
| API | 用户/账单业务 | `tests/api/` | 已有 |
| scripts E2E | 手工整链路 | `scripts/test_*_client.py` | 已有 |

---

## 4. 常见混淆

### 「我们不是已经有 MCP 脚本了吗？为什么还要 L2/L4？」

脚本 E2E = **整条链路通不通**（粗粒度、真实、慢、依赖起服务）。

- **L2** 更精准：专门钉死「发出的 HTTP 请求长什么样」  
- **L4** 更精准：专门钉死「传输与握手」  
失败时更好定位是接线错了还是协议/端口错了。

### 「L4-lite 和 L4 是一回事吗？」

**不是。**

- **L4-lite**：协议*行为*（未知工具、缺参）——可用内存 Client  
- **L4**：协议*传输*（真 HTTP `/mcp`、`initialize`）

### 「L2 要不要起 FastAPI？」

标准 L2 Mock：**不起**真实 API，用 Mock 挡在 httpx 边界。  
若用真 API 断言请求，那就更像集成/E2E，而不是典型 L2 Mock。

---

## 5. 以后若要补齐，最小落地建议

### L2（**已完成**，默认进 `make test`）

文件：`tests/mcp/test_tool_http_wiring.py`

用 `httpx.MockTransport` 拦截 `mcp_server.server.httpx.Client`，覆盖代表 tool：

- `login_user` → `POST /api/users/login`
- `get_current_user` → `GET /api/users/me` + Bearer
- `create_bill` → `POST /api/bills` + Bearer + body
- `list_my_bills` → `GET /api/bills` + Bearer
- `share_bill` → `POST /api/bills/{id}/share` + Bearer

### L4（已落地）

1. `tests/mcp/test_streamable_http_transport.py`
2. fixture 自启 `streamable_http_app`（随机端口，不依赖本机 3001）
3. `Client("http://127.0.0.1:<port>/mcp")`：`tools/list` + 缺参 `call_tool` + 错误路径断言
4. `make test-e2e` 可只跑 `@pytest.mark.e2e`

---

## 6. 30 秒复习卡

> **L2 Mock**：假装 API，检查 MCP 发出的 HTTP 单据对不对。  
> **L4 真传输**：真打电话到 `:3001/mcp`，检查能否按 MCP 协议接通。  
> **API 测试**：厨房做菜对不对。  
> **scripts E2E**：顾客进店能否完成点单到喝完。

官方 MCP 协议由 Anthropic 提出（2024-11）；  
本文的 L1–L4 **不是** Anthropic 官方测试标准编号，而是本项目测试分层命名（详见 `TESTING_IMPROVEMENT_PLAN.zh.md`）。
