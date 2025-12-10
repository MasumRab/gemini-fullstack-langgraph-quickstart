# Observability

This module provides opt-in observability for the agent using [Langfuse](https://langfuse.com/).

## Configuration

To enable observability, set the following environment variables:

```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com # Optional, defaults to cloud
```

## Features

- **Tracing:** Captures full traces of agent execution, including planning, search, and reflection steps.
- **Latencies:** tracks duration of each step.
- **Inputs/Outputs:** Captures inputs and outputs for debugging.

## Implementation Details

- **Zero-impact default:** If disabled or dependencies are missing, the agent runs without any overhead.
- **Guarded Imports:** The module dynamically attempts to load `langfuse` components, ensuring compatibility across different SDK versions.
- **Shim:** A shim layer handles import path differences between Langfuse SDK v2 and v3.
