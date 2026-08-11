# 只有 Tools 的 MCP Server 是否可用？

**结论：可以。** 只实现 Tools、没有 Prompts / Resources 的 MCP Server，部署后完全可用。

## 背景

有的 MCP Server 代码仓库里只实现了 **Tools**，没有 **Prompts**，也没有 **Resources**。这类服务是否还能正常部署、被客户端使用？

## 协议说明

在 MCP（Model Context Protocol）中，以下三类能力都是**可选**的，不必全部实现：

| 能力 | 作用 | 是否必须 |
|------|------|----------|
| **Tools** | 让模型调用具体操作（查数据、发请求、改状态等） | 否 |
| **Resources** | 暴露可读数据源（文件、文档、配置等） | 否 |
| **Prompts** | 提供可复用的提示词模板 | 否 |

实际中很多正式 MCP Server 也只暴露 Tools，例如只做「查 Jira / 发邮件 / 调 API」一类能力的服务，同样可以正常部署，并被 Cursor 等客户端连接使用。

## 部署后客户端行为

客户端一般会：

1. 与 Server 握手，并发现该 Server 声明了哪些能力  
2. 若只有 Tools → 就只注册 Tools  
3. Agent 在需要时调用这些 Tools  

**没有 Prompts / Resources 只是少了两类能力**，不影响 Tools 本身的工作。

## 能力选型建议

- 若业务只需要「执行动作」→ 只做 Tools 就够了  
- Resources 适合「把内容当上下文读进来」  
- Prompts 适合「给用户 / Agent 提供固定对话模板」  

## 总结

只有 Tools 的 MCP Server 仓库，部署后一样可用；这是正常且常见的实现方式。
