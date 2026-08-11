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

## 反向问题：可以没有 Tools，只有 Prompts 或只有 Resources 吗？

**结论：可以，协议允许。**

Tools / Prompts / Resources 都是可选能力，Server 可以任意组合，包括：

| 组合 | 是否合法 | 常见程度 |
|------|----------|----------|
| 只有 Tools | ✅ | 最常见 |
| 只有 Resources | ✅ | 少见，但合理 |
| 只有 Prompts | ✅ | 更少见，但合法 |
| Tools + Resources | ✅ | 常见 |
| 三者都有 | ✅ | 完整型 |
| 三者都没有 | ✅（协议上） | 基本没实用价值 |

### 只有 Resources 的典型用途

把文档、配置、知识库当「可读上下文」暴露给客户端，不提供可调用动作。

### 只有 Prompts 的典型用途

提供固定对话 / 工作流模板（如「写周报」「做 code review」），用户或 Agent 选用，但不执行具体 Tool。

### 生态现实

实际生态里 **Tools-only 最多**；纯 Resources / 纯 Prompts 合法但少见，因为多数产品更需要「能做事」。

这正是 MCP「能力可选」的设计点：不是必须三者齐全，按场景实现即可。

## 总结

- 只有 Tools 的 MCP Server，部署后一样可用；这是正常且常见的实现方式。  
- 只有 Resources、或只有 Prompts 的 MCP Server，协议上也合法可用，只是实际更少见。  
- 三类能力可任意组合，按业务需要实现即可。
