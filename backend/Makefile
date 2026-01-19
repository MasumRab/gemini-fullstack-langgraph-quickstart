lint lint_diff lint_package lint_tests:
	uv run ruff check .
	# [ "$(PYTHON_FILES)" = "" ] || uv run ruff format $(PYTHON_FILES) --diff
	[ "$(PYTHON_FILES)" = "" ] || uv run ruff check --select I $(PYTHON_FILES)
	# [ "$(PYTHON_FILES)" = "" ] || uv run mypy --strict $(PYTHON_FILES)
	# [ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && uv run mypy --strict $(PYTHON_FILES) --cache-dir $(MYPY_CACHE) || true
