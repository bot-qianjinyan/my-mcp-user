# User MCP Demo

学习项目：先提供用户 REST API，再基于这些接口构建 **Streamable HTTP** MCP Server，覆盖 MCP 三要素（Tools / Resources / Prompts）。

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

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/users/register` | 注册 |
| POST | `/api/users/login` | 登录，返回 JWT |
| GET | `/api/users/me` | 当前用户（需 Bearer Token） |
| PATCH | `/api/users/me` | 更新个人信息（需 Bearer Token） |

### 示例

```bash
# 注册
curl -s http://127.0.0.1:8000/api/users/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"alice@example.com","password":"secret123","display_name":"Alice"}'

# 登录
curl -s http://127.0.0.1:8000/api/users/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secret123"}'

# 更新资料（替换 TOKEN）
curl -s http://127.0.0.1:8000/api/users/me \
  -X PATCH \
  -H "Authorization: Bearer TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"display_name":"Alice Updated","bio":"Hello MCP"}'
```

## MCP 三要素

### Tools（可执行操作）

- `register_user` → POST `/api/users/register`
- `login_user` → POST `/api/users/login`
- `get_current_user` → GET `/api/users/me`
- `update_user_profile` → PATCH `/api/users/me`

### Resources（可读数据）

- `user://api/health` — API 健康检查
- `user://docs/overview` — 项目说明
- `user://profile/{access_token}` — 当前用户资料

### Prompts（提示词模板）

- `welcome_new_user` — 欢迎新用户
- `help_update_profile` — 协助更新资料

## Cursor 连接（Streamable HTTP）

在 Cursor MCP 配置中增加：

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

先启动 API（以及可选的 MCP Server），再分别运行：

```bash
source .venv/bin/activate

# 只测 REST API
python scripts/test_api_client.py

# 只测 MCP（需 API + MCP 都已启动）
python scripts/test_mcp_client.py
```

## 目录结构

```
my-mcp/
├── app/                      # FastAPI 用户 REST API
│   ├── __init__.py
│   ├── main.py               # 应用入口
│   ├── config.py             # 配置（端口、数据库、JWT）
│   ├── database.py           # SQLAlchemy / SQLite
│   ├── models.py             # User 表模型
│   ├── schemas.py            # 请求/响应 Pydantic 模型
│   ├── auth.py               # 密码哈希、JWT、鉴权依赖
│   ├── services.py           # 注册/登录/更新业务逻辑
│   └── routers/
│       ├── __init__.py
│       └── users.py          # /api/users 路由
├── mcp_server/               # Streamable HTTP MCP Server
│   ├── __init__.py
│   ├── __main__.py           # python -m mcp_server
│   └── server.py             # Tools / Resources / Prompts
├── scripts/
│   ├── test_api_client.py    # 独立测试 REST API
│   └── test_mcp_client.py    # 独立测试 MCP Server
├── data/
│   └── users.db              # SQLite 数据库（运行后生成）
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
