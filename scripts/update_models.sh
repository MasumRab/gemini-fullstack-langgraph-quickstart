#!/bin/bash
# Wrapper script to update Gemini model configurations
# Usage: ./update_models.sh [strategy]
# Strategies: optimized, stable, experimental, cost_saver

# Ensure python is available
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python not found. Please install Python to run the update script."
    exit 1
fi

# Run the update script
SCRIPT_DIR="$(dirname "$0")"
$PYTHON_CMD "$SCRIPT_DIR/update_models.py" "$@"
