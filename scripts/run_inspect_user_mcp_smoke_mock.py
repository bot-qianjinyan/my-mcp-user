"""本地无模型 API Key 时，用 mockllm 跑通 Inspect → MCP(:3001) 链路。

前置：API :8000 与 MCP :3001 已启动。

用法：
    source .venv/bin/activate
    python scripts/run_inspect_user_mcp_smoke_mock.py
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inspect_ai import eval as inspect_eval
from inspect_ai.model import ChatMessageAssistant, ModelOutput, get_model
from inspect_ai.tool import ToolCall

from evals.user_mcp_smoke import user_mcp_smoke


def _parse_creds(text: str) -> dict[str, str]:
    username = re.search(r"username=([^\s,]+)", text).group(1)
    email = re.search(r"email=([^\s,]+)", text).group(1)
    password = re.search(r"password=([^\s,]+)", text).group(1)
    return {"username": username, "email": email, "password": password}


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if text is not None:
                parts.append(text)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _last_tool_json(messages) -> dict:
    for msg in reversed(messages):
        if getattr(msg, "role", None) != "tool":
            continue
        raw = _message_text(msg.content)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    return {}


def _assistant_with_tool(function: str, arguments: dict) -> ModelOutput:
    return ModelOutput(
        model="mockllm/model",
        choices=[
            {
                "message": ChatMessageAssistant(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id=f"call_{uuid.uuid4().hex[:10]}",
                            function=function,
                            arguments=arguments,
                        )
                    ],
                    model="mockllm/model",
                ),
                "stop_reason": "tool_calls",
            }
        ],
    )


def _make_custom_outputs():
    state = {"step": 0, "creds": None}

    def custom_outputs(messages, tools, tool_choice, config) -> ModelOutput:
        if state["creds"] is None:
            for msg in messages:
                if getattr(msg, "role", None) == "user" and "register_user" in str(
                    msg.content
                ):
                    state["creds"] = _parse_creds(str(msg.content))
                    break
            if state["creds"] is None:
                raise RuntimeError("无法从 sample 中解析注册凭证")

        creds = state["creds"]
        step = state["step"]
        state["step"] += 1

        if step == 0:
            return _assistant_with_tool(
                "register_user",
                {
                    "username": creds["username"],
                    "email": creds["email"],
                    "password": creds["password"],
                    "display_name": "Inspect Smoke",
                },
            )
        if step == 1:
            return _assistant_with_tool(
                "login_user",
                {"username": creds["username"], "password": creds["password"]},
            )
        if step == 2:
            data = _last_tool_json(messages)
            token = data.get("access_token") or (data.get("data") or {}).get(
                "access_token"
            )
            if not token:
                # 兼容嵌套
                token = data.get("token")
            if not token:
                raise RuntimeError(f"login 结果中未找到 access_token: {data}")
            return _assistant_with_tool(
                "create_bill",
                {
                    "access_token": token,
                    "title": "Inspect午餐",
                    "amount": 36.5,
                    "category": "food",
                },
            )
        return _assistant_with_tool("submit", {"answer": "SMOKE_OK"})

    return custom_outputs


def main() -> int:
    model = get_model("mockllm/model", custom_outputs=_make_custom_outputs())
    logs = inspect_eval(user_mcp_smoke(), model=model, log_dir=str(ROOT / "logs"))
    log = logs[0]
    status = getattr(log, "status", None)
    scores = getattr(log, "results", None)
    print("status:", status)
    if scores is not None:
        print("results:", scores)
    # 打印样本得分
    for sample in getattr(log, "samples", []) or []:
        print("sample_id:", sample.id, "scores:", sample.scores)
        print("output:", getattr(sample, "output", None))
    ok = status == "success"
    # includes 目标 SMOKE_OK
    if log.samples:
        sample_scores = log.samples[0].scores or {}
        for scorer_name, score in sample_scores.items():
            print(f"scorer[{scorer_name}]:", score)
            if getattr(score, "value", None) == 1.0 or score == 1.0:
                ok = True
    return 0 if ok and status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
