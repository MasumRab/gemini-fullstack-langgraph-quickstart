# Jules API Skill

Reference and instructions for using the Jules REST API.

## Requirements
- `JULES_API_KEY` - Generate at https://jules.google.com/settings#api

## Quick Start
```bash
# List sessions
curl -H "x-goog-api-key: $JULES_API_KEY" \
  https://jules.googleapis.com/v1alpha/sessions
```

See SKILL.md and references/ for full documentation.