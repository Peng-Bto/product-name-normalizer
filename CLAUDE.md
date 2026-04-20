# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Product Name Normalizer (大批量品名标准化工具) is an industrial-grade tool for normalizing tens of thousands of product names using LLMs (specifically Spark/OpenAI-compatible APIs). It classifies product names into specific categories based on Chinese customs regulations.

## Common Commands

```bash
# Run the normalizer
python main.py

# Run in background (recommended for server)
nohup python main.py > nohup.out 2>&1 &

# Monitor progress
tail -f process.log

# Run test for max iterations feature
python test_max_iterations.py
```

## Architecture

### Core Processing Flow
1. **Data Loading**: Reads from `product.xlsx` (first column = product names)
2. **Name Mapping**: Generates `name_mapping.xlsx` with original vs cleaned names
3. **API Processing**: Uses async concurrency with `asyncio.Semaphore(CONCURRENCY_LIMIT=10)`
4. **Checkpointing**: Each successful result immediately appends to `result_checkpoint.jsonl`
5. **Resumption**: On restart, loads checkpoint to skip already-processed items
6. **Export**: Aggregates all results to `result.xlsx`

### Key Configuration (in `.env`)
```
SPARK_API_KEY=your_api_key:your_api_secret
SPARK_BASE_URL=https://spark-api-open.xf-yun.com/v1
SPARK_MODEL_DOMAIN=4.0Ultra
```

### Important Constants (main.py)
- `CONCURRENCY_LIMIT = 10` - Parallel API calls
- `RETRY_COUNT = 3` - Retries per product name within a single call
- `MAX_ITERATIONS = 3` - Maximum retry rounds across all products

## File Purposes

| File | Purpose |
|------|---------|
| `main.py` | Main entry point, async processing, checkpointing logic |
| `prompt.txt` | LLM classification rules and category definitions |
| `test_max_iterations.py` | Unit tests for iteration limit feature |

## Output Files

- `result_checkpoint.jsonl` - Incremental backup (JSON Lines, most important)
- `result.xlsx` - Final aggregated results
- `failed_products.txt` - Products that failed all retries (for manual review)
- `name_mapping.xlsx` - Original vs cleaned product name mapping
- `process.log` - Operational logs
- `model_request.log` - Raw API request/response for auditing

## Development Notes

- **No overwriting**: Never modify source `product.xlsx`; always output to `result.xlsx`
- **Immediate save**: Every successful result is flushed to disk immediately (non-negotiable safety feature)
- **JSON extraction**: Uses regex to extract JSON from model responses (handles markdown wrappers)
- **Logging split**: `process.log` for operations, `model_request.log` for API debugging