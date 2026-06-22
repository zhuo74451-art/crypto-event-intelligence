# Open Source Reuse Audit V1

## Scope

This audit covers reference projects whose design patterns, schemas, or concepts may inform the Research Intelligence system. No code is copied.

## Reference Projects

### TauricResearch/TradingAgents

| Aspect | Assessment |
|--------|------------|
| **License** | Repository-specific license, not reviewed |
| **Relevant concepts** | Multi-agent research workflow, structured claim/report formats |
| **Reuse** | Conceptual: research workflow design patterns. No code copied. |
| **Code copied** | No |
| **Data copied** | No |
| **Risk** | Low — conceptual inspiration only |

### dietmarwo/autoresearch-trading

| Aspect | Assessment |
|--------|------------|
| **License** | Not reviewed |
| **Relevant concepts** | Automated research loop for trading strategy generation |
| **Reuse** | Conceptual: understanding automated research pipeline. Our system explicitly avoids auto-research loops. |
| **Code copied** | No |
| **Risk** | Low |

### AI4Finance-Foundation/FinGPT

| Aspect | Assessment |
|--------|------------|
| **License** | MIT (based on README — must confirm LICENSE file) |
| **Relevant concepts** | Financial LLM fine-tuning, sentiment extraction |
| **Reuse** | None in this work order (no LLM calls) |
| **Code copied** | No |
| **Risk** | None — not used |

### AI4Finance-Foundation/FinNLP

| Aspect | Assessment |
|--------|------------|
| **License** | MIT (based on README) |
| **Relevant concepts** | Financial NLP data collection pipelines |
| **Reuse** | None in this work order |
| **Code copied** | No |
| **Risk** | None — not used |

### AI4Finance-Foundation/FinRobot

| Aspect | Assessment |
|--------|------------|
| **License** | MIT (based on README) |
| **Relevant concepts** | Multi-agent financial analysis |
| **Reuse** | None |
| **Code copied** | No |
| **Risk** | None — not used |

### OpenSPG/KAG

| Aspect | Assessment |
|--------|------------|
| **License** | Apache 2.0 |
| **Relevant concepts** | Knowledge graph construction, conflict resolution |
| **Reuse** | Conceptual: conflict graph design patterns. Our system does not use a graph database. |
| **Code copied** | No |
| **Risk** | Low |

### microsoft/RD-Agent

| Aspect | Assessment |
|--------|------------|
| **License** | MIT |
| **Relevant concepts** | Research and development automation agent |
| **Reuse** | Conceptual: research workflow design |
| **Code copied** | No |
| **Risk** | Low |

## Prohibited Actions

This research intelligence system does **not** implement:
- Multi-Agent orchestration (LangGraph, AutoGen, CrewAI)
- Vector databases (Chroma, Qdrant, Milvus, etc.)
- Graph databases (Neo4j, etc.)
- LLM API calls (OpenAI, DeepSeek, Claude, etc.)
- Automated research loops (continuous mode, cron, systemd)
- Auto-trading
- LLM-based extraction of research claims

## Summary

| Project | License Verified | Code Copied | Data Copied | Reuse Type |
|---------|-----------------|-------------|-------------|------------|
| TauricResearch/TradingAgents | No | No | No | Conceptual |
| dietmarwo/autoresearch-trading | No | No | No | Conceptual |
| AI4Finance-Foundation/FinGPT | MIT (unverified) | No | No | None |
| AI4Finance-Foundation/FinNLP | MIT (unverified) | No | No | None |
| AI4Finance-Foundation/FinRobot | MIT (unverified) | No | No | None |
| OpenSPG/KAG | Apache 2.0 | No | No | Conceptual |
| microsoft/RD-Agent | MIT | No | No | Conceptual |
