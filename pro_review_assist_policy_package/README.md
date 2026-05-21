# Review Assist Extraction Package

Generated: 2026-05-21

This package contains a comprehensive implementation-oriented extraction from the uploaded Review Assist framing notes and example Environmental Constraints Report.

## Files

- `review_assist_extraction_package.docx` - polished main memo.
- `review_assist_extraction_package.pdf` - PDF rendering of the main memo.
- `review_assist_extraction_package.md` - Markdown version of the main memo.
- `config/review_assist_report_policy.json` - canonical machine-readable policy starter.
- `docs/domains/REPORT_POLICY.md` - concise policy explanation.
- `docs/domains/GPT_STYLE_CONTEXT.md` - style-only GPT guidance.
- `prompts/codex_prompt_starters.md` - implementation prompt starters.

## How to use

1. Start with `config/review_assist_report_policy.json`.
2. Use `docs/domains/REPORT_POLICY.md` as the human explanation.
3. Use `docs/domains/GPT_STYLE_CONTEXT.md` only as style/shape guidance, not as evidence.
4. Use `prompts/codex_prompt_starters.md` to generate implementation tasks.

## Key stance

The example report is a pattern source, not a template. Do not copy project facts, trail-specific logic, PEL-specific text, unfinished draft content, or restricted/manual findings into generic Review Assist outputs.
