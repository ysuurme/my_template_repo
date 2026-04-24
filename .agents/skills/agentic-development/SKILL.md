---
name: agentic-development
description: Use when building agents with the Claude API, implementing tool use, designing agent loops, coordinating multi-agent systems, managing context windows, or testing agent behaviour
---

# Agentic Development

## Overview

Covers the design and implementation of AI agents using the Claude API. Enforces reliable tool definitions, predictable agent loop behaviour, and testable agent patterns that avoid common hallucination and context management failures.

## Scope

**Owns:** Claude API usage patterns (tool use, structured outputs, streaming), agent loop design and state management, multi-agent coordination patterns, tool definition and validation, context window and prompt management, agent testing patterns.

**Does not own:** General API development patterns (→ `application-development`), agent deployment infrastructure (→ `design-infrastructure`), data pipeline patterns used by agents (→ `data-engineering`), model serving infrastructure (→ `mlops`).

**Interfaces with:**
- `application-development` — agents often expose or consume APIs; general API patterns live there
- `design-infrastructure` — agent runtime deployment follows general container/cloud patterns
- `git-workflow` — agent-driven git automation uses the patterns defined in git-workflow

## When to Use

- **Trigger:** Building an agent with the Claude API
- **Trigger:** Implementing tool use or structured outputs
- **Trigger:** Designing an agent loop or multi-turn conversation flow
- **Trigger:** Coordinating multiple agents
- **Trigger:** Managing context window limits or prompt structure
- **Trigger:** Writing tests for agent behaviour

**Do NOT use for:**
- General API endpoint development (→ `application-development`)
- Agent deployment and infrastructure (→ `design-infrastructure`)
- Data pipelines that agents consume (→ `data-engineering`)

## Core Pattern

[TODO: Add agent loop pattern, tool definition standard, structured output pattern with Claude API]

## Quick Reference

[TODO: Add tool definition template, context management strategies, multi-agent coordination patterns, testing approach, prompt caching patterns]

## Implementation

[TODO: Add Claude API usage patterns: tool use, structured outputs, streaming, prompt caching, error handling in tool calls, agent state management]

## Common Mistakes

[TODO: Document common agent mistakes — poorly defined tools, missing error handling in tool calls, context window overflow, untestable agent behaviour]
