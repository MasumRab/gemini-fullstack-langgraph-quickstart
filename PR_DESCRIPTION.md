---
**Agent Report Summary**
- **Branch**: maintenance/cleanup-and-todo-refactor
- **Commit**: 9a97d6132d8f293d9507e857f22ebb65bc7de03f
- **Diff Summary**: Moved 14 standalone scripts from root `scripts/` to `backend/scripts/` to consolidate python tooling, updating internal relative path logic inside them. Standardized all TODO complexity attributes across `backend/` and `tests/` to use (`Small`, `Medium`, `Large`, `Epic`) instead of the deprecated (`Low`, `Medium`, `High`) values.

**Scan Results**
- Unused files: []
- Generated artifacts removed: []
- Ambiguous files: []
- Misplaced files moved: [scripts/analyze_churn_plot.py, scripts/debug_import.py, scripts/dev.py, scripts/extract_todos_structured.py, scripts/generate_sample_reports.py, scripts/pruning_plan.py, scripts/test_available_models.py, scripts/test_model_availability.py, scripts/update_active_context.py, scripts/update_all_notebooks.py, scripts/update_models.py, scripts/update_notebook_models_gemini.py, scripts/update_notebooks_gemma3.py, scripts/verify_env.py]

**TODOs**
- Valid TODOs: 30
- Stale TODOs: []
- Ambiguous TODOs: []
- TODO complexity changes: Changed 22 TODOs from 'Low' to 'Small', and 5 TODOs from 'High' to 'Large'.

**Convention Enforcement**
- Enforcements applied: Moved backend tooling into `backend/scripts/` per AGENTS memory guidelines; updated `TODO` syntax per new complexity standards.
- Matched patterns: Python tools logic; TODO complexity schema.
- Convention adherence score: 100

**Verification**
- Commands run: `python backend/scripts/extract_todos_structured.py`, `git diff --stat`, `uv run ruff check --fix backend/src/ backend/scripts/`, `uv run pytest tests/`
- Verification status: pass
- Failure conditions encountered: []

**Risk Assessment**
- Risk summary: Low risk. The scripts moved are utility and maintenance scripts not actively invoked by the core runtime. The TODO changes are purely structural string updates inside comments.
- Files requiring human review: []

**Next Steps**
- Recommended actions: []
- Suggested reviewers: []
- Labels: [cleanup, automated, needs-review]

**Machine Metadata**
```
agent: repository_maintenance_agent
branch: maintenance/cleanup-and-todo-refactor
commit: 9a97d6132d8f293d9507e857f22ebb65bc7de03f
pr: TBD
verification_status: pass
todo_quality_score: 100
knowledge_base_health_score: 100
```
---

- Checklist for reviewers:
  - [ ] Confirm verification status and run commands locally if needed
  - [ ] Review ambiguous files and TODOs marked requires_review
  - [ ] Confirm convention enforcements match project intent
  - [ ] Approve or request changes
