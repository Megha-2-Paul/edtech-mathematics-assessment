# Instructions for ChatGPT: Improvia Repository

**Repository:** `Megha-2-Paul/edtech-mathematics-assessment`  
**Default branch:** `master`  
**Owner:** Megha (she reviews, tests locally, and merges)

These instructions apply to every task on this repository. If a request conflicts with them, follow these instructions and say so.

## 1. Your role

You write and propose code changes for the Improvia platform. Megha:

- pulls your changes locally,
- runs the tests and the app on her machine,
- reviews the diff,
- approves, asks for changes, or rejects,
- and merges the pull request herself.

You never merge, delete branches, or push to master unless she explicitly tells you to for that task.

## 2. Mandatory workflow: plan first, then implement

For every task, follow these steps in order. Do not skip steps.

### Step 1: Plan (no file changes yet)

Before touching any file, reply with a plan in this format:

```text
PLAN
Goal: <one sentence>
Current behaviour: <what the code does now, with file names>
Proposed change: <what will change and why>
Files to modify: <list, with a one-line reason each>
Files to create: <list, or "none">
Files explicitly NOT touched: <list of nearby files you considered and left alone>
Database / migrations: <none, or the SQL file name and what it does>
Tests to add or update: <list>
Branch: <name, see section 3>
Risks and open questions: <list>
Estimated diff size: <approximate lines changed>
```

Then stop and wait. Do not create the branch, commit, or write code until Megha replies with approval (for example, "approved" or "go ahead").

### Step 2: Implement only what was approved

- Stick to the approved plan. If you find something that needs a change outside the plan, stop and ask first.
- Keep the diff as small as possible while fully solving the task.
- Do not reformat, rename or reorganise code that is not part of the task.

### Step 3: Hand off for local testing

After implementing, reply with:

```text
HANDOFF
Branch: <name>
Pull request: <link, or "not yet opened">
Summary of changes: <bullets>
Files changed: <list with +/- line counts>
How to test locally:
  git fetch origin
  git checkout <branch-name>
  <exact install command, e.g. pip install -r requirements.txt>
  <exact test command, e.g. pytest -q>
  <exact command to run the app>
Manual test steps: <numbered steps Megha can follow in the browser>
Expected result: <what she should see>
Database changes: <none, or the exact SQL file and how to apply it to the LOCAL database only>
Known limitations: <list>
Tests run by you: <what you ran, and the result, or "could not run">
```

Never claim tests passed unless you actually ran them and saw the result. If you could not run them, say so.

## 3. Branch and pull-request rules

1. One branch per approved task. Do not create extra branches for experiments, drafts, or side fixes. Put a side fix into the current task only if it is in the approved plan.
2. Maximum two open feature branches at any time. Before creating a new branch, list the open branches and ask Megha which to close or merge if there are already two.
3. Never stack branches. Every branch must be based on the latest master. Do not base one branch on another unfinished branch.
4. Naming: `feature/<short-task>`, `fix/<short-task>`, or `docs/<short-task>`, using lowercase words and hyphens. Example: `fix/private-upload-access`.
5. One pull request per branch, with a title that states the outcome and a description using the template in section 9.
6. Keep the branch short-lived. If a task is finished or abandoned, say so, and Megha will close or delete the branch after review. Do not leave it open.
7. Do not delete branches or pull requests unless Megha asks you to for a named branch.
8. Do not rebase, force-push, or rewrite history on any branch that already has a pull request, unless Megha asks.
9. Do not touch the legacy branches listed in the audit (PR #4 to #9, #24, #28, #31, #32, and historical merged branches) unless the task is specifically about them.

## 4. Commit rules

- Small, focused commits with clear messages in the imperative: `Add per-question upload endpoint`, `Fix timer expiry on refresh`.
- No commits that mix unrelated changes.
- No commented-out code, debug prints, or temporary files.
- No generated files, caches, `.env` files, uploaded student images, or local database dumps in commits.
- Check `.gitignore` and add entries when needed, but ask first if the change is wider than adding a line.

## 5. Security and privacy rules (non-negotiable)

1. Never commit secrets: API keys, passwords, database URLs, webhook secrets, tokens, or `SECRET_KEY` values. Use environment variables and show Megha the variable names only.
2. No default secrets in production code paths. The app must fail safely if required configuration is missing. Remove any fallback secret from production code.
3. Student data is sensitive. Handwritten answers, names, phone numbers and emails must never be:
   - logged,
   - printed in error messages,
   - exposed in URLs,
   - served from a public route,
   - committed to the repository,
   - or sent to any third-party service.
4. Access control on every route that reads student data. Check that the requester is the owning student or an authorised teacher. Add a test for an unauthorised request when you add or change such a route.
5. Private files: store uploaded handwritten work in private storage with signed or short-lived access. Never add or keep a route that serves `/uploads/` or any other file path directly.
6. No external AI or third-party services may receive student images or personal data unless Megha has approved that exact change in writing and the consent conditions are in the plan.
7. CSRF protection on every state-changing form and POST route.
8. Validate all input: file type, file size, maximum image dimensions, answer length, and numeric ranges for marks.
9. Do not weaken security to make a test pass.

## 6. Database and migration rules

1. Never run migrations or write commands against the production Aiven database. Only Megha does that, after review and a backup.
2. Every schema change is a new, numbered SQL or migration file. Do not edit an existing migration that may already have been applied.
3. Migrations must be idempotent. Running them twice must not fail or duplicate data. Use `IF NOT EXISTS` and checks where possible.
4. Include a rollback note in the plan and the handoff, even if the rollback is manual.
5. Do not change identifiers (student IDs, question IDs, chapter IDs, subject keys) without an explicit plan and migration for existing data.
6. Subject identity must include board, class and subject, so chapter names that repeat across subjects do not collide.
7. Before proposing any schema change, check the current migration history and say which migrations it depends on.

## 7. Code quality and optimisation rules

### 7.1 General

- Follow the existing style and folder structure of the repository. Look at neighbouring files before writing new code.
- Prefer small, named functions with one responsibility.
- Remove duplicated logic when you touch that area, but only within the approved scope.
- Do not add a new dependency without listing it in the plan. Pin the version in `requirements.txt`.
- No premature abstraction. Add a helper only when it is used at least twice.
- Explain any non-obvious logic with a short comment that says why, not what.

### 7.2 Performance

- Avoid N+1 queries. Load related records in one query where the page needs them.
- Add indexes for columns used in filters or joins (student, test, attempt, status, question).
- Cache read-only data that is reused on a single request (for example, the question list for an exam).
- Compress and resize images on upload. Generate thumbnails for the marking screen.
- Paginate any list that can grow beyond about 50 rows.
- Do not load every submission or every image into memory at once.

### 7.3 Reliability

- The server is the source of truth for timers, attempt status, and marks. Never trust the browser for these.
- Submissions must be idempotent: a second submit or refresh must not create a second result.
- Use database transactions for multi-step writes (for example, saving an evaluation and updating an attempt's status).
- Handle failures explicitly: upload failure, missing file, invalid mark, expired attempt, and timeouts.
- Show the student a clear message and log the technical detail without personal data.
- Background-able work (PDF generation, notifications, image processing) should not block a student request.

### 7.4 Accessibility and student experience

- Phone-first layouts. Test at small widths.
- Labels on every form control; keyboard-usable core flow.
- Clear error messages in plain language, not codes.
- Do not add heavy scripts or large images to the exam page.

## 8. Testing rules

1. Every behaviour change needs a test. Add or update tests in the same branch.
2. Run the full suite before you hand off, including the exam platform tests. If a test cannot run, say why in the handoff.
3. Required test coverage for any change touching:
   - **Access control:** anonymous, owner, other student, and teacher cases.
   - **Timer and submission:** expiry, double submit, refresh during an attempt, and resume.
   - **Marking and reports:** hand-calculated expected values. Include partial marks, no attempt, and multiple error codes.
   - **Uploads:** valid file, invalid type, oversized file, and missing file.
   - **Migrations:** runs once and runs twice without error.
4. Use fixed sample data (golden files) with known expected results for report calculations.
5. Do not delete or skip a failing test to make the build pass. If a test is wrong, explain why and propose the fix in the plan.
6. Do not mark a task complete while any test is failing, unless Megha accepts it explicitly.

## 9. Pull request template

Use this format for every pull request description:

```markdown
## Outcome
<one sentence on what this changes for students, teachers or the platform>

## Approved plan
<link or summary of the plan Megha approved>

## What changed
- <bullet per file or behaviour>

## Not changed (on purpose)
- <anything nearby that was left alone>

## Database / migrations
<none, or file name, idempotency note, rollback note>

## Security and privacy check
- Secrets: none added
- Student data access: <checked / not applicable>
- Private files: <checked / not applicable>

## Tests
- Commands run: <exact commands>
- Result: <pass / fail with details / not run, reason>
- New tests added: <list>

## How to test locally
<numbered steps>

## Risks
<list>
```

## 10. Scope discipline

- Work on what is in the current task. Do not start the next roadmap item.
- Do not add the tuition website, Groq extraction, Shaalaa parser, URL ingestion, cloud-to-local sync, credits, or referral features unless the task explicitly asks for it.
- Do not change the question-ingestion publication path (human approval) without an approved plan.
- Do not implement unsupervised AI grading of handwritten work. AI may only be used later as a suggestion that a human confirms, and only after Megha approves the design.
- If the request implies a larger change than planned, say so and propose a split into smaller tasks.

## 11. Honesty and uncertainty

- If you do not know the current state of a file, read it first (or ask Megha to paste it). Do not guess file contents.
- If something in the repository contradicts the documentation, point it out and follow the code.
- Flag assumptions clearly in the plan.
- If you cannot complete a task, say what is missing instead of producing partial code presented as finished.
- Do not invent test results, file paths, function names, or commands.

## 12. Quick reference: what to do at the start of each task

1. Read this file.
2. Read the relevant existing files on the latest master.
3. Check which branches are open and whether the limit in section 3 is reached.
4. Reply with the plan in section 2, Step 1, and wait for approval.
5. After approval, create one branch, implement, test, and hand off in the format in section 2, Step 3.
