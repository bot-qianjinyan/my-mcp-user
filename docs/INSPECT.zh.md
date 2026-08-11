# Inspect

> 本文根据 [Inspect 官网](https://inspect.aisi.org.uk/) 整理为中文介绍。  
> 与本仓库 MCP 的对接说明见：[INSPECT_MCP.zh.md](./INSPECT_MCP.zh.md)。

## 欢迎

Inspect 是由 [英国 AI Security Institute](https://aisi.gov.uk) 与 [Meridian Labs](https://meridianlabs.ai) 共同开发的前沿 AI 评测框架。可用于评测编码、Agent 任务、推理、知识、行为以及多模态理解等广泛能力。核心特性包括：

- **可组合积木**：数据集（datasets）、智能体（agents）、工具（tools）、评分器（scorers），方便编写与复用评测。
- **200+ 预置评测**：可直接在任意模型上运行。
- **完善工具链**：基于 Web 的 Inspect View 用于监控与可视化评测；另有 VS Code 扩展，辅助编写与调试。
- **灵活的工具调用**：支持自定义工具与 MCP 工具，以及内置的 bash、python、文本编辑、网页搜索、网页浏览、计算机操作等工具。
- **Agent 评测**：内置灵活 Agent、多 Agent 原语，也可运行外部 Agent（如 Claude Code、Codex CLI、Gemini CLI）。
- **沙箱系统**：可在 Docker、Kubernetes、Modal、Proxmox、Vagrant 等环境中运行不可信模型代码，并提供扩展 API。

下文给出两个简短的「Hello, Inspect」示例。读完基础后，可继续阅读官方文档中的 [Datasets](https://inspect.aisi.org.uk/datasets.html)、[Solvers](https://inspect.aisi.org.uk/solvers.html)、[Scorers](https://inspect.aisi.org.uk/scorers.html)、[Tools](https://inspect.aisi.org.uk/tools.html)、[Agents](https://inspect.aisi.org.uk/agents.html)，以编写更复杂的评测。

若你主要关心**运行**已有评测而非开发新评测，可查看 [Evals](https://inspect.aisi.org.uk/evals/) 列表，其中收录了 200+ 常见 benchmark 的实现。

## 快速开始

1. 从 PyPI 安装 Inspect：

   ```bash
   pip install inspect-ai
   ```

2. 若使用 VS Code，建议安装 [Inspect VS Code Extension](https://inspect.aisi.org.uk/vscode.html)（非必须，但强烈推荐）。

开发与运行评测还需要可用的模型，通常要安装对应 Python 包，并在环境中配置 API Key。例如：

```bash
pip install openai
export OPENAI_API_KEY=your-openai-api-key
inspect eval simpleqa.py --model openai/gpt-4o
```

```bash
pip install anthropic
export ANTHROPIC_API_KEY=your-anthropic-api-key
inspect eval simpleqa.py --model anthropic/claude-sonnet-4-0
```

```bash
pip install google-genai
export GOOGLE_API_KEY=your-google-api-key
inspect eval simpleqa.py --model google/gemini-2.5-pro
```

```bash
pip install torch transformers
export HF_TOKEN=your-hf-token
inspect eval simpleqa.py --model hf/meta-llama/Llama-2-7b-chat-hf
```

Inspect 内置支持 20+ 模型提供商，也支持通过 HuggingFace、vLLM、SGLang 做本地推理。详见 [Model Providers](https://inspect.aisi.org.uk/providers.html)。

## Hello, Inspect

一次 Inspect 评测是一个 [Task](https://inspect.aisi.org.uk/tasks.html)，由三部分组成：

1. **[Dataset](https://inspect.aisi.org.uk/datasets.html)**：提供带标签的样本——通常是含 `input` 与 `target` 列的表；`input` 是提示，`target` 是理想答案或打分指引。

2. **[Solver](https://inspect.aisi.org.uk/solvers.html)**：为每个样本生成答案。可以只是一次 [`generate()`](https://inspect.aisi.org.uk/reference/inspect_ai.solver.html#generate) 调用，也可以是多轮使用工具的完整 Agent。

3. **[Scorer](https://inspect.aisi.org.uk/scorers.html)**：评估输出——可用文本比对、模型打分或其他自定义方案。

下面看两个短示例：问答 benchmark，以及 Capture the Flag（CTF）挑战。

### Benchmark：SimpleQA

该任务在 [SimpleQA](https://openai.com/index/introducing-simpleqa/)（简短事实问答）上评测模型：

`simpleqa.py`

```python
from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, hf_dataset
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate

@task  # ①
def simpleqa():
    return Task(
        dataset=hf_dataset(  # ②
            "codelion/SimpleQA-Verified",
            split="train",
            sample_fields=FieldSpec(  # ③
                input="problem",
                target="answer",
            ),
        ),
        solver=generate(),  # ④
        scorer=model_graded_qa(),  # ⑤
    )
```

1. `@task` 把函数注册到 Inspect，从而可用 `inspect eval` 按名称发现并运行。
2. [`hf_dataset()`](https://inspect.aisi.org.uk/reference/inspect_ai.dataset.html#hf_dataset) 直接从 Hugging Face 加载样本；也支持 CSV、JSON 与内存数据集。
3. [`FieldSpec`](https://inspect.aisi.org.uk/reference/inspect_ai.dataset.html#fieldspec) 声明式地把数据集的 `problem` / `answer` 映射为样本的 `input` / `target`，无需手写转换函数。
4. [`generate()`](https://inspect.aisi.org.uk/reference/inspect_ai.solver.html#generate) 把每个 `input` 发给模型并收集回复。
5. 答案为自由文本，故用 [`model_graded_qa()`](https://inspect.aisi.org.uk/reference/inspect_ai.scorer.html#model_graded_qa) 让模型对照 `target` 打分。

命令行运行（用 `--model` 指定模型）：

```bash
inspect eval simpleqa.py --model openai/gpt-5
```

查看结果：

```bash
inspect view
```

### Agent：CTF 挑战

Agent 评测要求模型**采取行动**，而不只是回答问题。下面是一个 CTF 任务：[`react()`](https://inspect.aisi.org.uk/agents.html) Agent 在沙箱中用 [`bash()`](https://inspect.aisi.org.uk/reference/inspect_ai.tool.html#bash) 与 [`todo_write()`](https://inspect.aisi.org.uk/reference/inspect_ai.tool.html#todo_write) 寻找隐藏 flag：

`ctf.py`

```python
from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import includes
from inspect_ai.tool import bash, todo_write

@task
def ctf():
    return Task(
        dataset=json_dataset("challenges.json"),
        solver=react(  # ①
            prompt=(
                "You are a Capture the Flag player. "
                "Explore the system and find the flag."
            ),
            tools=[bash(), todo_write()],
            attempts=3,
        ),
        scorer=includes(),  # ②
        sandbox="docker",  # ③
    )
```

1. [`react()`](https://inspect.aisi.org.uk/reference/inspect_ai.agent.html#react) 是内置 Agent：执行 reason-act-observe 循环，向模型提供给定 `tools`，直到提交答案（此处最多 3 次尝试）。
2. [`includes()`](https://inspect.aisi.org.uk/reference/inspect_ai.scorer.html#includes)：若目标 flag 出现在 Agent 提交的答案中则通过。
3. `sandbox="docker"`：所有工具调用在隔离的 Docker 容器中执行（由任务旁的 `Dockerfile` 或 `compose.yaml` 配置）。

用 `inspect view` 查看结果，并仔细阅读各条 transcript。

更多进阶示例见官方 [Tutorial](https://inspect.aisi.org.uk/tutorial.html)。

## Python API

上面用 CLI 的 `inspect eval` 运行评测；同样的操作也可在 Python 中通过 [`eval()`](https://inspect.aisi.org.uk/reference/inspect_ai.html#eval) 完成：

```python
from inspect_ai import eval
from simpleqa import simpleqa

eval(simpleqa(), model="openai/gpt-5")
```

## LLM 辅助

学习与使用 Inspect 时，建议把文档提供给 LLM 以便协助。有两份便于 LLM 阅读的 Markdown：

- [llms.txt](https://inspect.aisi.org.uk/llms.txt)：文档索引，按需拉取文章（约 2k tokens）。
- [llms-guide.txt](https://inspect.aisi.org.uk/llms-guide.txt)：全部文档全文（约 185k tokens）。

每个文档页顶部也有 **Copy Page** 按钮，可复制该页的 Markdown 版本。

## 进一步学习

| 章节 | 内容 |
|------|------|
| [Tutorial](https://inspect.aisi.org.uk/tutorial.html) | 带注释的示例，展示多种特性与写法 |
| [Components](https://inspect.aisi.org.uk/tasks.html) | 评测积木：tasks、datasets、solvers、scorers |
| [Models](https://inspect.aisi.org.uk/models.html) | 模型与提供商、缓存、多模态、推理、batch、并发 |
| [Agents](https://inspect.aisi.org.uk/agents.html) | 规划、记忆与工具；ReAct、多 Agent、外部框架桥接 |
| [Tools](https://inspect.aisi.org.uk/tools.html) | 自定义/内置工具、MCP、沙箱、工具调用审批 |
| [Running](https://inspect.aisi.org.uk/running.html) | 大规模评测集：错误处理、限额、并行、早停 |
| [Analysis](https://inspect.aisi.org.uk/analysis.html) | 读日志、提取 DataFrame、扫描 transcript 找问题 |
| [Extensions](https://inspect.aisi.org.uk/extensions.html) | 扩展模型 API、组件、沙箱、审批器、hooks、文件系统 |

还可浏览 [Evals](https://inspect.aisi.org.uk/evals/)（可直接跑的 benchmark）、社区 [Extensions 画廊](https://inspect.aisi.org.uk/extensions/)、以及完整 [Reference](https://inspect.aisi.org.uk/reference/)（Python / CLI API）。

## 引用

BibTeX：

```bibtex
@software{UK_AI_Security_Institute_Inspect_AI_Framework_2024,
  author = {AI Security Institute, UK},
  title = {Inspect {AI:} {Framework} for {Large} {Language} {Model}
    {Evaluations}},
  date = {2024-05},
  url = {https://github.com/UKGovernmentBEIS/inspect_ai},
  langid = {en}
}
```

引用格式：

AI Security Institute, UK. 2024. *Inspect AI: Framework for Large Language Model Evaluations*. Released May. <https://github.com/UKGovernmentBEIS/inspect_ai>.
