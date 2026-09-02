# Question Bank Agents

Specialized document-processing agents are reusable workflows for different PDF families.

## Current agent

- **CBSE Board Paper** (`cbse_board_paper`) — detects the document-level bilingual pattern used by the supported CBSE board-paper family and routes English pages for extraction while skipping Hindi duplicates.

## Design principles

1. Detect document structure before relying on page-level language classification.
2. Never hard-code page numbers for one source paper.
3. If a known structural pattern is not confidently detected, route uncertain pages to review rather than guessing.
4. Agents only decide document/page routing at this stage; question extraction remains a separate stage.
5. Preserve the original PDF/page as the source of truth.
6. New PDF families should get their own specialized agent rather than adding unrelated rules to an existing agent.
