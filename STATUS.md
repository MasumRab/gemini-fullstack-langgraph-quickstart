# Project Status

## Overview
This document tracks the current implementation state, deviations from the original roadmap, and deferred tasks. It serves as the source of truth for the "Incremental Evolution" strategy.

## Strategic Direction
**"Wrap, Don't Rewrite"**
- We are maintaining upstream compatibility by keeping the existing `persistence.py` and `graph.py` logic intact.
- New features (MCP, complex planning) are added as optional, non-invasive wrappers or parallel paths.

## Component Status

### 1. Persistence & Memory
- **Status:** ✅ Functional / Wrapped
- **Implementation:** `backend/src/agent/persistence.py` (Core JSON logic)
- **MCP Integration:** `backend/src/agent/mcp_persistence.py` (New Wrapper)
- **Notes:** The original JSON implementation is treated as production-ready. We are not rewriting it, but wrapping it to be exposed via `langchain-mcp-adapters`.

### 2. Model Context Protocol (MCP)
- **Status:** 🚧 In Progress
- **Implementation:** `backend/src/agent/mcp_config.py` (Connection Manager)
- **Notes:** Focusing on "File-system" tools first (`load_plan`, `save_plan`). Other tools will be migrated incrementally.

### 3. Planning Mode (Open SWE)
- **Status:** ⏸️ Deferred
- **Notes:** Logic to support `Todo` objects and dynamic re-planning is deferred until Phase 1 (Infrastructure) is stable.
- **Future Work:** `generate_query` node in `graph.py` will eventually evolve into `generate_plan`.

### 4. Frontend & Open Canvas
- **Status:** ⏸️ Deferred
- **Notes:** No frontend changes are being made in the current phase.
- **Requirements:** Split-pane UI (Chat + Artifacts) is required but on hold.

## Deferred Tasks
- Frontend "Open Canvas" split-pane implementation.
- Refactoring of `graph.py` into sub-graphs (keeping it monolithic for now to avoid merge conflicts).
- Full migration of all tools to MCP (doing it incrementally).
