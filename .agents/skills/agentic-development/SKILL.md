---
name: agentic-development
description: Use when building agents with the Claude API or Gemini API, implementing tool use, designing Plan-Act-Observe loops, coordinating multi-agent systems, managing context windows, or testing agent behaviour
---

# Agentic Development

## Overview

Covers the design and implementation of AI agents. Primary compute: **Vertex AI / Google AI Studio (Gemini)**; Claude API maintained for parity. All agent patterns are **provider-agnostic** — tool definitions, loop logic, and output validation are decoupled from the LLM provider to prevent vendor lock-in.

Orchestration framework: **Antigravity** (internal). Core loop: **Plan → Act → Observe**.

## Scope

**Owns:** Agent loop design and state management, tool definition standard (Pydantic → JSON Schema), structured output enforcement (Pydantic + Correction Observation), multi-agent coordination (Orchestrator + Handoff patterns), context window and prompt management, agent state persistence (Checkpointer), agent testing patterns.

**Does not own:** General API development patterns (→ `application-development`), agent deployment infrastructure (→ `design-infrastructure`), data pipeline patterns used by agents (→ `data-engineering`), model serving infrastructure (→ `mlops`), telemetry instrumentation for agent spans (→ `observability`).

**Interfaces with:**
- `application-development` — agents often expose or consume APIs; general API patterns live there
- `design-infrastructure` — agent runtime deployment, Firestore setup, Vertex AI Vector Search provisioning
- `observability` — agent loop steps emit OTel spans (one span per iteration); use OTel as the primary tracing layer
- `git-workflow` — agent-driven git automation uses the patterns defined in git-workflow

## When to Use

- **Trigger:** Building an agent with Gemini, Claude, or any LLM API
- **Trigger:** Implementing tool use or structured outputs
- **Trigger:** Designing a Plan-Act-Observe loop or multi-turn conversation flow
- **Trigger:** Coordinating multiple agents (Orchestrator + Handoff)
- **Trigger:** Managing context window limits or prompt structure
- **Trigger:** Writing tests for agent behaviour

**Do NOT use for:**
- General API endpoint development (→ `application-development`)
- Agent deployment and infrastructure (→ `design-infrastructure`)
- Data pipelines that agents consume (→ `data-engineering`)
- Telemetry instrumentation patterns (→ `observability`)

---

## Core Pattern

### The Plan-Act-Observe Loop

A recursive state machine. The agent receives a goal, generates a thought, selects a tool, executes it, and observes the result — repeating until the `final_response` schema is satisfied or `max_iterations` is reached.

```
[Goal]
  └─→ [Plan: Generate Thought]
        └─→ [Act: Select + Execute Tool]
              └─→ [Observe: Parse Result]
                    ├─→ loop (tool_use) ──────────────────────────────┐
                    │                                                  │
                    └─→ end_turn → [Structured Output: Pydantic]      │
                                         ├─→ parse ok  → DONE         │
                                         └─→ parse fail → Correction ─┘
```

**Termination conditions (in priority order):**
1. `final_response` parses successfully into the target Pydantic model → success
2. `max_iterations` reached → raise typed `AgentMaxIterationsError` → hard stop
3. Tool returns a non-recoverable terminal error → hard stop

**Always cap iterations — never remove this guard:**

```python
MAX_ITERATIONS = 10

for iteration in range(MAX_ITERATIONS):
    response = llm.generate(messages, tools=tools)
    # ... process response
else:
    raise AgentMaxIterationsError(
        f"Agent did not complete within {MAX_ITERATIONS} iterations"
    )
```

---

### Structured Output Enforcement

Every final agent response must parse into a Pydantic model. On failure, inject the validation error back into the loop as a Correction Observation — not a crash.

```python
from pydantic import BaseModel, ValidationError

def parse_or_correct(
    raw: str,
    model: type[BaseModel],
    messages: list[dict],
) -> BaseModel | None:
    try:
        return model.model_validate_json(raw)
    except ValidationError as e:
        messages.append({
            "role": "user",
            "content": f"Your response failed validation:\n{e}\n\nCorrect your output and retry.",
        })
        return None  # loop continues
```

---

### Provider-Agnostic Action Executor

The `execute_tool` function is the critical isolation layer. Tool execution must be **completely decoupled from the LLM provider** — swap Gemini for Claude without rewriting any tool logic.

```python
from collections.abc import Callable

# Registry maps tool name → Python function
TOOL_REGISTRY: dict[str, Callable] = {
    "get_absenteeism_metrics": get_absenteeism_metrics,
    "get_branch_info": get_branch_info,
    "transfer_to_agent": transfer_to_agent,
}

def execute_tool(tool_name: str, tool_input: dict) -> str:
    fn = TOOL_REGISTRY.get(tool_name)

    if fn is None:
        # Hallucinated tool — inform the model, do not crash
        available = list(TOOL_REGISTRY.keys())
        return f"Error: Tool '{tool_name}' does not exist. Available tools: {available}"

    try:
        result = fn(**tool_input)
        return str(result)
    except Exception as e:
        # Return error as string — let the LLM self-correct
        return f"Error: {e}"
```

**Rule:** `execute_tool` never raises. It always returns a string. This prevents the agent from halting on recoverable errors.

---

## Quick Reference

### Tool Definition Template (Pydantic → JSON Schema)

All tools are defined as Pydantic models. This ensures structural consistency and compatibility across Gemini, Claude, and GPT-4.

```python
from pydantic import BaseModel, Field

class GetAbsenteeismMetrics(BaseModel):
    """
    Fetches absenteeism percentage for a specific SBI branch and quarter.
    Use this tool when the user requests branch-level absenteeism data.
    Returns: float representing the absenteeism percentage (0.0–100.0).
    """
    branch_id: str = Field(..., description="The SBI branch code, e.g., 'SBI_123'")
    quarter: str = Field(..., pattern=r"^\d{4}Q[1-4]$", description="Quarter in YYYY Q[1-4] format, e.g., '2024Q3'")
```

**Convert to provider format:**

```python
# Gemini / OpenAI-compatible format
tool_schema = GetAbsenteeismMetrics.model_json_schema()

# Claude format
claude_tool = {
    "name": "get_absenteeism_metrics",
    "description": GetAbsenteeismMetrics.__doc__,
    "input_schema": GetAbsenteeismMetrics.model_json_schema(),
}
```

**Tool description rules:**
- Write as technical documentation for the model, not a human-friendly summary
- Include: what it does, when to use it, what each parameter means, what it returns
- Vague descriptions → wrong tool selection or missing required parameters

---

### Tool Choice

```python
# Claude
tool_choice = {"type": "auto"}   # model decides whether to call a tool
tool_choice = {"type": "any"}    # force at least one tool call this turn

# Gemini (equivalent)
tool_config = {"function_calling_config": {"mode": "AUTO"}}
tool_config = {"function_calling_config": {"mode": "ANY"}}
```

Use `any` / `ANY` only when the task explicitly requires a tool call (e.g., first turn of a data-retrieval agent). Default to `auto` / `AUTO`.

---

### Context and State Management

| Scope | Mechanism | Notes |
|---|---|---|
| Short-term | Thread-local message histories (Antigravity State) | Current conversation turn; trimmed via sliding window |
| Long-term | Vertex AI Vector Search | RAG-based retrieval for cross-session knowledge |
| Prompt cache | Gemini 1.5 Pro / Claude 3.5 | Cache system prompt + tool defs for iterative loops |

**Sliding window for long conversations:**

```python
def trim_messages(messages: list[dict], max_tokens: int = 8_000) -> list[dict]:
    system = [m for m in messages if m["role"] == "system"]
    history = [m for m in messages if m["role"] != "system"]
    # Drop oldest user+assistant pairs first
    while estimate_tokens(history) > max_tokens and len(history) > 2:
        history = history[2:]
    return system + history
```

**Prompt caching (Claude) — cache long-lived, static content only:**

```python
# Cache system prompt and tool definitions — static across all loop iterations
system=[{
    "type": "text",
    "text": SYSTEM_PROMPT,
    "cache_control": {"type": "ephemeral"},  # TTL: 5 minutes
}]
```

Do NOT cache per-turn messages or tool results.

---

### Multi-Agent Coordination

**Orchestrator Pattern:** A Lead Agent dispatches tasks to specialised sub-agents.

```
[Orchestrator Agent]
    ├── transfer_to_agent("data_engineer_agent", task, context)
    ├── transfer_to_agent("ml_evaluator_agent", task, context)
    └── transfer_to_agent("report_writer_agent", task, context)
```

**Handoff tool definition:**

```python
class TransferToAgent(BaseModel):
    """
    Transfer control to a specialised sub-agent.
    Use when the current task requires expertise outside your own scope.
    Returns: the sub-agent's final response as a string.
    """
    agent_name: str = Field(
        ...,
        description="Target agent identifier: 'data_engineer_agent' | 'ml_evaluator_agent' | 'report_writer_agent'",
    )
    task: str = Field(..., description="Clear, self-contained task description for the sub-agent")
    context: dict = Field(
        default_factory=dict,
        description="Relevant state to pass forward (prior results, user preferences)",
    )
```

**Rule:** The `context` dict must be self-contained. The sub-agent has no access to the orchestrator's message history.

---

### State Persistence (Checkpointer)

Save state after every loop iteration. Enables Human-in-the-Loop (HITL) approvals and crash recovery.

```python
from dataclasses import dataclass, asdict

@dataclass
class AgentCheckpoint:
    run_id: str
    iteration: int
    messages: list[dict]
    tool_calls: list[dict]
    status: str  # "running" | "awaiting_approval" | "complete" | "failed"

def save_checkpoint(checkpoint: AgentCheckpoint, backend: str = "sqlite") -> None:
    if backend == "firestore":
        db.collection("agent_checkpoints").document(checkpoint.run_id).set(
            asdict(checkpoint)
        )
    else:  # sqlite — local dev and testing
        _save_to_sqlite(checkpoint)
```

| Backend | When to use |
|---|---|
| **Firestore (GCP)** | Production; HITL approval workflows, cross-service visibility |
| **SQLite** | Local development and testing |

Firestore provisioning and configuration → `design-infrastructure`.

---

## Implementation

### Full Agent Loop (Claude API)

```python
import anthropic
from pydantic import BaseModel

client = anthropic.Anthropic()
MAX_ITERATIONS = 10

def run_agent(
    goal: str,
    tools: list[dict],
    response_model: type[BaseModel],
    system: str = "",
) -> BaseModel:
    messages = [{"role": "user", "content": goal}]

    for iteration in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4_096,
            system=system,
            tools=tools,
            tool_choice={"type": "auto"},
            messages=messages,
        )

        # Append assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            result = parse_or_correct(text, response_model, messages)
            if result:
                return result
            # Correction injected into messages — loop continues

        elif response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})

    raise AgentMaxIterationsError(
        f"Agent did not complete within {MAX_ITERATIONS} iterations"
    )
```

---

### Streaming with SSE

```python
# Accumulate partial tool call JSON before executing — never execute on a fragment
with client.messages.stream(
    model="claude-3-5-sonnet-20241022",
    tools=tools,
    messages=messages,
) as stream:
    accumulated: dict[str, str] = {}  # tool_use_id → partial_json

    for event in stream:
        if event.type == "content_block_start" and event.content_block.type == "tool_use":
            accumulated[event.content_block.id] = ""

        elif event.type == "content_block_delta":
            if hasattr(event.delta, "partial_json"):
                block_id = event.index  # resolve to current block id
                accumulated[str(block_id)] = accumulated.get(str(block_id), "") + event.delta.partial_json

        elif event.type == "content_block_stop":
            # Full JSON now available — safe to execute
            pass  # execute in message_stop handler

    final = stream.get_final_message()
```

**Rule:** Always accumulate `partial_json` deltas before execution. Executing on partial JSON raises a parse error that silently corrupts the loop.

---

### Agent Observability

Agent loop steps emit OpenTelemetry spans — one span per iteration. Full OTel setup lives in → `observability`.

```python
from opentelemetry import trace

tracer = trace.get_tracer("agent.loop")

for iteration in range(MAX_ITERATIONS):
    with tracer.start_as_current_span("agent.iteration") as span:
        span.set_attribute("agent.iteration", iteration)
        span.set_attribute("agent.stop_reason", response.stop_reason)
        if response.stop_reason == "tool_use":
            span.set_attribute("agent.tool_called", tool_name)
        # ... rest of loop
```

For agent-specific visualisation beyond OTel:
- **Vertex AI Service Runtime** — GCP-native agent tracing dashboard
- **LangSmith** — valid alternative in LangChain ecosystems; captures full loop replay

---

## Common Mistakes

| Mistake | Consequence | Correction |
|---|---|---|
| Vague tool descriptions | Model selects wrong tool or omits required params | Write as technical docs: what it does, when to use it, what each param means, what it returns |
| No `max_iterations` cap | Self-correction loop → infinite loop → runaway cost | Always set `MAX_ITERATIONS = 10`; raise typed `AgentMaxIterationsError` on breach |
| Executing partial streaming JSON | JSON parse error mid-loop | Accumulate all `partial_json` deltas before executing any tool call |
| Raising on tool execution error | Agent halts; no recovery possible | `execute_tool` never raises — catch all exceptions, return `"Error: <message>"` as string |
| Crashing on hallucinated tool name | Agent halts | Check `TOOL_REGISTRY`; return available tool names as feedback message |
| Provider-coupled tool logic | Vendor lock-in; rewrite required when switching LLM | Keep `execute_tool` provider-agnostic; the registry is the only coupling point |
| No state persistence | Crash = lost work; HITL impossible | Checkpoint after every iteration (Firestore for prod, SQLite for dev) |
| Untestable agent behaviour | Determinism lost; impossible to debug regressions | Emit OTel spans per iteration (→ `observability`); use Vertex AI Service Runtime or LangSmith for full loop replay |
| Passing full history to sub-agent | Sub-agent receives irrelevant context; performance degrades | Pass only a `context: dict` with the specific state the sub-agent needs |
