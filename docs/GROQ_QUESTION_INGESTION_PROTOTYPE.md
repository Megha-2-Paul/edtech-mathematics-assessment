# Groq PDF Extraction Prototype — G1

## Status
Prototype code and mocked tests are on `docs/groq-question-ingestion-workflow`, tracked in [draft PR #32](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/pull/32).

GitHub Actions passed on commit `ba75d5b14cac4063c46d7f5a4088268a831b0f59`. This is not yet a real-PDF accuracy benchmark or a live API verification. The current PR's mergeability needs rechecking after documentation conflict reconciliation.

## Safety boundary
- Reads a local text-based PDF only.
- Processes at most two pages by default.
- Writes candidate JSON locally only.
- Does not write to the database, publish questions, deploy, or run bulk processing.
- Use only a PDF that Improvia is permitted to process.
- Never commit or share the Groq API key.

## Configure Groq locally (PowerShell)

In the PowerShell terminal where you will run tests and the sample:

```powershell
$env:GROQ_API_KEY = Read-Host "Enter Groq API key"
```

The key is held only in that terminal's environment for the current session. Do not paste it into chat, add it to source code, or put it in a committed `.env` file. Optionally set `$env:GROQ_MODEL` to a model available to your Groq account.

## 1. Run mocked tests

From the repository root, activate the project virtual environment and run:

```powershell
python -m pytest -q tests/test_groq_ingestion.py tests/test_groq_benchmark.py
```

Then run the existing ingestion regression tests:

```powershell
python -m pytest -q tests/test_bulk_json_ingestion.py tests/test_ai_json_normalization.py question_bank/tests/test_json_extractor.py
```

The second command is the previously recorded 15-test baseline. Record the new output separately; do not describe it as a full-suite result.

## 2. Run a permitted sample PDF

Use a local, text-based PDF you are permitted to process. Replace the example filename with its actual path:

```powershell
python -m question_bank.ingest_groq pdf "C:\path\to\sample-paper.pdf" --max-pages 2 --board ICSE --class-level 10
```

The default output is written beside the PDF as `sample-paper.groq_candidates.json`. If that output already exists, choose a new `--output` path instead of overwriting it.

Do not run this command until the mocked tests pass and the API key is configured. This call may consume Groq API usage. No API call is required to run the mocked tests.

## 3. Manually verify the candidate file

Compare the JSON to the original PDF, checking:
- question boundaries and numbering;
- mathematical notation, minus signs, exponents, roots, fractions and symbols;
- subquestions and their hierarchy;
- MCQ options and labels;
- marks, including whether they were explicitly printed;
- page numbers and source provenance;
- empty, malformed, invented or incomplete fields.

The existing normalization path may apply a default to missing marks. Never treat defaulted marks as verified marks. Keep candidates pending until manually checked.

## 4. Benchmark against human-verified gold JSON

Create a separate gold JSON file by manually transcribing the same sampled pages. Do not copy the model output into gold without verification.

Then run:

```powershell
python -m scripts.benchmark_groq_extraction --candidate "sample-paper.groq_candidates.json" --gold "sample-paper.gold.json" --output "groq-benchmark.json" --review-minutes 10
```

Adjust paths and the review time to the actual files and time spent. Inspect the benchmark JSON and report:
- candidate count versus gold count;
- question-text boundary precision and recall;
- subquestion/options/marks/type/page accuracy;
- invalid and missing fields;
- manual correction time per question.

Text matching only normalizes whitespace; it is not a mathematical-equivalence checker. The benchmark does not measure diagram fidelity or prove correctness by itself.

## Exit criteria before any bulk processing
1. Focused mocked tests pass locally.
2. Existing ingestion regression tests pass locally.
3. One permitted sample PDF is processed successfully.
4. Every extracted candidate is manually compared with the source.
5. Benchmark and human correction time are recorded.
6. No key, source PDF, candidate output, or gold file is accidentally committed.
7. No merge or publication occurs until the results are reviewed.
