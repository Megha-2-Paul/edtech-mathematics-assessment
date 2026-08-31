# Shaalaa extraction prototype

This is an isolated prototype for one ICSE Class 10 Mathematics paper. It uses
Playwright to load the public Shaalaa page, parses the rendered DOM into a
JSON intermediate representation, validates loss-sensitive conditions, and
provides a small HTML-to-PDF renderer.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m shaalaa_extractor.collector
```

The default output is `shaalaa_extractor/output/temporary/paper.json`.
`pdf_generator.py` can render a validated record with a locally installed
Chromium/Edge executable. The prototype does not download gated PDFs, bypass
authentication, scrape the full archive, or modify production question-bank
files.

If Shaalaa presents an access challenge in headless mode, the collector stops
with an explicit error. Use a browser session that is legitimately permitted
to view the public page, or pass saved page HTML to the parser; do not bypass
the challenge.

Limitations: the live DOM varies by paper and some mathematical expressions,
tables, matrices, and diagrams may require human review. Image retrieval is
deliberately a separate step so every asset retains its source URL and
question association.
