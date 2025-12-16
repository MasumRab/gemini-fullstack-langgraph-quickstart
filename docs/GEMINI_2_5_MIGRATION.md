# Gemini 2.5 Migration Guide

**Date**: December 12, 2024  
**Status**: ✅ Complete

## Overview

This document outlines the migration from deprecated Gemini 1.5/2.0 models to the currently accessible Gemini 2.5 series models.

## Background

Based on testing with the Google GenAI SDK and official documentation:
- **Gemini 1.5 models** (1.5-flash, 1.5-flash-8b, 1.5-pro): ❌ Not accessible via API (404 errors)
- **Gemini 2.0 models** (2.0-flash, 2.0-flash-exp, 2.0-flash-lite): ❌ Deprecated/Not accessible
- **Gemini 2.5 models** (2.5-flash, 2.5-flash-lite, 2.5-pro): ✅ **Currently accessible**

## Available Models

### Gemini 2.5 Flash (Recommended)
- **Model ID**: `gemini-2.5-flash`
- **Best for**: Price-performance balance, general use
- **Token limit**: 1,048,576 tokens
- **Use case**: Default for all operations

### Gemini 2.5 Flash-Lite (Fastest)
- **Model ID**: `gemini-2.5-flash-lite`
- **Best for**: High-throughput, cost-efficiency
- **Token limit**: 1,048,576 tokens
- **Use case**: Query generation, fast operations

### Gemini 2.5 Pro (Best Quality)
- **Model ID**: `gemini-2.5-pro`
- **Best for**: Complex reasoning, highest quality
- **Token limit**: 2,097,152 tokens
- **Use case**: Final answer generation, complex analysis

## Changes Made

### 1. Backend Configuration
**File**: `backend/src/agent/configuration.py`

```python
# Updated defaults
query_generator_model: str = Field(default="gemini-2.5-flash")
reflection_model: str = Field(default="gemini-2.5-flash")
answer_model: str = Field(default="gemini-2.5-flash")
```

### 2. Research Tools
**File**: `backend/src/agent/research_tools.py`

- Updated `writer_model` from `gemini-1.5-flash` to `gemini-2.5-flash`
- Added `gemini-2.5-flash-lite` to `MODEL_TOKEN_LIMITS`
- Marked 1.5 and 2.0 models as deprecated in comments

### 3. Model Update Script
**File**: `update_models.py`

Replaced strategies:
- ~~`free_tier`~~ → `flash` (Gemini 2.5 Flash for all)
- ~~`optimized`~~ → `flash_lite` (Gemini 2.5 Flash-Lite for all)
- ~~`stable`~~ → Removed (1.5 models deprecated)
- ~~`flash_2_0`~~ → Removed (2.0 models deprecated)
- `pro` → Gemini 2.5 Pro for answers, Flash for queries
- `balanced` → Flash-Lite for queries, Flash for reflection, Pro for answers

### 4. Notebooks
**Files**: All 12 notebooks updated

Updated model configuration cell:
```python
MODEL_STRATEGY = "Gemini 2.5 Flash (Recommended)" # @param ["Gemini 2.5 Flash (Recommended)", "Gemini 2.5 Flash-Lite (Fastest)", "Gemini 2.5 Pro (Best Quality)"]
```

Added model verification cell using `google-genai` SDK to test API connectivity.

## Usage

### Quick Start

1. **Update all configurations to Gemini 2.5 Flash** (default):
   ```bash
   python update_models.py flash
   ```

2. **For fastest/cheapest operations**:
   ```bash
   python update_models.py flash_lite
   ```

3. **For highest quality**:
   ```bash
   python update_models.py pro
   ```

4. **For balanced approach**:
   ```bash
   python update_models.py balanced
   ```

### Notebook Usage

All notebooks now include:

1. **Setup Cell**: Configures backend environment
2. **Model Configuration Cell**: Select from available Gemini 2.5 models
3. **Model Verification Cell**: Test API key and model availability

Simply run cells in order and select your preferred model strategy.

## Rate Limiting Considerations

Based on [Google AI Rate Limits Documentation](https://ai.google.dev/gemini-api/docs/rate-limits):

### Free Tier Limits (Tier 1)
- **RPM** (Requests Per Minute): 15
- **TPM** (Tokens Per Minute): 1,000,000
- **RPD** (Requests Per Day): 1,500

### Recommendations

1. **Use Flash-Lite for high-volume operations** to maximize throughput
2. **Implement exponential backoff** for 429 (quota exceeded) errors
3. **Monitor daily quotas** - resets at midnight Pacific time
4. **Consider upgrading tier** for production workloads

## Testing

Test model availability:
```bash
python test_available_models.py
```

This will:
- Load API key from `.env`
- Test all Gemini models
- Report which models are accessible
- Provide recommendations

## Migration Checklist

- [x] Update backend configuration defaults
- [x] Update research_tools.py model references
- [x] Update update_models.py strategies
- [x] Update all 12 notebooks with new model options
- [x] Add model verification cells to notebooks
- [x] Create test script for model availability
- [x] Document rate limiting considerations
- [x] Update MODEL_TOKEN_LIMITS dictionary

## Next Steps

1. **Implement Rate Limiting**:
   - Add retry logic with exponential backoff
   - Track RPM/TPM/RPD usage
   - Queue requests when approaching limits

2. **Monitor Performance**:
   - Compare 2.5 Flash vs Flash-Lite performance
   - Measure cost savings
   - Track error rates

3. **Update Documentation**:
   - Update README with new model information
   - Add rate limiting best practices
   - Document upgrade path to higher tiers

## References

- [Gemini Models Documentation](https://ai.google.dev/gemini-api/docs/models)
- [Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Deprecations](https://ai.google.dev/gemini-api/docs/deprecations)
- [API Key Setup](https://ai.google.dev/gemini-api/docs/api-key)

## Support

For issues or questions:
1. Check model availability with `test_available_models.py`
2. Verify API key is set correctly in `.env`
3. Review rate limit errors in logs
4. Consult Google AI documentation for latest updates
