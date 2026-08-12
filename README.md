# User MCP Demo

学习项目：先提供用户与账单 REST API，再基于这些接口构建 **Streamable HTTP** MCP Server，覆盖 MCP 三要素（Tools / Resources / Prompts）。

> 生产环境里 `app` 与 `mcp_server` 完全可以拆成两个仓库：MCP 只通过 HTTP 调用已有微服务，旧服务无需改动。

## 架构

```
┌──────────────────────┐          HTTP /mcp          ┌──────────────────────┐
│  MCP Client          │ ──────────────────────────▶ │  MCP Server :3001    │
│  (Cursor / scripts)  │                             │  Streamable HTTP     │
└──────────────────────┘                             │  tools/resources/    │
                                                     │  prompts             │
                                                     └──────────┬───────────┘
                                                                │ httpx
                                                                ▼
                                                     ┌──────────────────────┐
                                                     │  User REST API :8000 │
                                                     │  FastAPI + SQLite    │
                                                     └──────────────────────┘
```

## 快速开始

```bash
cd /Users/jasqia/00D_PythonProject/my-mcp
source .venv/bin/activate
pip install -r requirements.txt

# 终端 1：启动 REST API
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 终端 2：启动 MCP Server（Streamable HTTP）
python -m mcp_server
# 等价：python -m mcp_server.server
```

- REST 文档：http://127.0.0.1:8000/docs
- MCP 端点：http://127.0.0.1:3001/mcp

## REST API

### 用户

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/users/register` | 注册 |
| POST | `/api/users/login` | 登录，返回 JWT |
| GET | `/api/users/me` | 当前用户（需 Bearer Token） |
| PATCH | `/api/users/me` | 更新个人信息（需 Bearer Token） |

### 账单

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/bills` | 创建自己的账单 |
| GET | `/api/bills` | 读取自己的账单列表 |
| GET | `/api/bills/shared-with-me` | 别人分享给自己的账单 |
| GET | `/api/bills/{id}` | 读取单条（自己的或分享给自己的） |
| PATCH | `/api/bills/{id}` | 更新自己的账单 |
| DELETE | `/api/bills/{id}` | 删除自己的账单 |
| POST | `/api/bills/{id}/share` | 分享给其他用户阅读 `{"username":"..."}` |
| DELETE | `/api/bills/{id}/share/{username}` | 取消分享 |
| POST | `/api/bills/{id}/like` | 点赞（自己的或已分享给自己的） |
| DELETE | `/api/bills/{id}/like` | 取消点赞 |

### 示例

```bash
# 登录拿 TOKEN 后创建账单
curl -s http://127.0.0.1:8000/api/bills \
  -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"午餐","amount":"32.50","category":"food","spent_at":"2026-08-11"}'

# 分享给 bob
curl -s http://127.0.0.1:8000/api/bills/1/share \
  -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"username":"bob"}'

# 点赞
curl -s http://127.0.0.1:8000/api/bills/1/like \
  -X POST \
  -H "Authorization: Bearer TOKEN"
```

## MCP 三要素

### Tools

**用户**

- `register_user` / `login_user` / `get_current_user` / `update_user_profile`

**账单**

- `create_bill` / `list_my_bills` / `list_shared_bills` / `get_bill`
- `update_bill` / `delete_bill`
- `share_bill` / `unshare_bill`
- `like_bill` / `unlike_bill`

### Resources

- `user://api/health` — API 健康检查
- `user://docs/overview` — 项目说明
- `user://profile/{access_token}` — 当前用户资料
- `bill://mine/{access_token}` — 我的账单列表
- `bill://shared/{access_token}` — 分享给我的账单
- `bill://item/{access_token}/{bill_id}` — 单条账单

### Prompts

- `welcome_new_user` — 欢迎新用户
- `help_update_profile` — 协助更新资料
- `help_create_bill` — 协助记账
- `help_share_bill` — 协助分享账单
- `help_like_bill` — 协助点赞

## Cursor 连接（Streamable HTTP）

```json
{
  "mcpServers": {
    "user-mcp": {
      "url": "http://127.0.0.1:3001/mcp"
    }
  }
}
```

## 本地验证

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt   # 首次需要

# 推荐：一条命令跑 pytest（无需先起服务）
make test
# 或：
# make test-api
# make test-mcp
# make test-e2e   # 只跑 L4 Streamable HTTP 等 e2e 标记

# 测试分层说明（L2 Mock / L4 真传输等）：docs/MCP_L2_L4_EXPLAINED.zh.md
# Inspect + MCP 配合：docs/INSPECT_MCP.zh.md

# 手工 E2E 冒烟（需先启动 API；MCP 脚本还需启动 MCP）
python scripts/test_user_client.py
python scripts/test_bill_client.py
python scripts/test_mcp_user_client.py
python scripts/test_mcp_bill_client.py
```

## Inspect 评测示例（对接 `:3001/mcp`）

先启动 API + MCP，再：

```bash
pip install -r requirements-inspect.txt
# 另需模型 SDK，例如：pip install openai && export OPENAI_API_KEY=...

inspect eval evals/user_mcp_smoke.py --model openai/gpt-4o
inspect view

# 账单等多场景
./scripts/run_inspect_gemini.sh google/gemini-3.6-flash evals/bill_mcp_scenarios.py
./scripts/run_inspect_gemini.sh google/gemini-3.6-flash suite

# 无 API Key 时：用 mockllm 本地验证 Inspect→MCP 接线
python scripts/run_inspect_user_mcp_smoke_mock.py

# macOS + Netskope 若报 ClientConnectorCertificateError：
./scripts/build_ssl_certs.sh
export GOOGLE_API_KEY='...'
./scripts/run_inspect_gemini.sh google/gemini-3.6-flash
# 脚本会自动检查/拉起 API(:8000)+MCP(:3001)；若仍 ConnectError，先手动：
#   ./scripts/start_services.sh
```

说明见 [docs/INSPECT_MCP.zh.md](docs/INSPECT_MCP.zh.md)。

## 目录结构

```
my-mcp/
├── app/                      # FastAPI REST API
│   ├── __init__.py
│   ├── main.py               # 应用入口
│   ├── config.py             # 配置（端口、数据库、JWT）
│   ├── database.py           # SQLAlchemy / SQLite
│   ├── models.py             # User / Bill / BillShare / BillLike
│   ├── schemas.py            # 请求/响应 Pydantic 模型
│   ├── auth.py               # 密码哈希、JWT、鉴权依赖
│   ├── services.py           # 用户业务逻辑
│   ├── bill_services.py      # 账单业务逻辑
│   └── routers/
│       ├── __init__.py
│       ├── users.py          # /api/users
│       └── bills.py          # /api/bills
├── mcp_server/               # Streamable HTTP MCP Server
│   ├── __init__.py
│   ├── __main__.py           # python -m mcp_server
│   └── server.py             # Tools / Resources / Prompts
├── tests/                        # pytest 套件
│   ├── conftest.py
│   ├── api/
│   │   ├── test_users.py
│   │   └── test_bills.py
│   └── mcp/
│       ├── surface.golden.json   # L1b 表面指纹
│       ├── test_tool_contract.py
│       ├── test_surface_drift.py
│       ├── test_protocol_behavior.py
│       ├── test_resources_prompts.py
│       ├── test_tool_http_wiring.py          # L2 Mock：tool→REST 接线
│       └── test_streamable_http_transport.py # L4：真 Streamable HTTP /mcp
├── evals/                            # Inspect 评测示例
│   ├── __init__.py
│   ├── _common.py                    # MCP/Agent 公共辅助
│   ├── user_mcp_smoke.py             # 冒烟：注册/登录/创建账单
│   ├── user_profile_scenarios.py     # 用户资料更新
│   └── bill_mcp_scenarios.py         # 账单 CRUD / 点赞 / 分享
├── scripts/
│   ├── http_helpers.py           # REST 测试公共工具
│   ├── mcp_helpers.py            # MCP 测试公共工具
│   ├── test_user_client.py       # 手工 E2E：用户 REST
│   ├── test_bill_client.py       # 手工 E2E：账单 REST
│   ├── test_mcp_user_client.py   # 手工 E2E：MCP 用户
│   └── test_mcp_bill_client.py   # 手工 E2E：MCP 账单
├── docs/
│   ├── MCP_TOOLS_ONLY_SERVER.zh.md
│   ├── MCP_L2_L4_EXPLAINED.zh.md
│   ├── TESTING_IMPROVEMENT_PLAN.zh.md
│   └── INSPECT_MCP.zh.md             # Inspect + MCP 配合说明
├── data/
│   └── users.db                  # SQLite 数据库（运行后生成）
├── Makefile
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── requirements-inspect.txt          # 可选：Inspect 评测依赖
└── README.md
```
