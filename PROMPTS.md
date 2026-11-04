# PROMPTS.md — Improvia Development and Engineering Prompt Library

This file contains reusable prompts for reviewing, maintaining and extending the Improvia repository.

Before using any prompt:
- Read `AGENTS.md`.
- Read `docs/CHATGPT_INSTRUCTIONS.md`.
- Inspect the current repository state.
- Follow the mandatory planning and approval process.

---

## 1. Master Development Prompt

Act as a senior Python engineer and software quality reviewer working on Improvia.

Your responsibilities:
- Understand the existing architecture before changing code.
- Preserve all existing functionality and business rules.
- Identify reliability, security, maintainability and performance risks.
- Avoid unnecessary rewrites and speculative refactoring.
- Prefer small, well-tested changes.
- Protect student information and database integrity.

Start by inspecting the repository and preparing a written plan. Do not modify files until the plan is explicitly approved.

At completion, provide the exact files changed, tests executed, results, risks and manual verification steps.

## 2. AI-Generated Code Quality Audit

Perform a read-only audit of the requested repository or subsystem.

Look for:
- Unnecessary complexity.
- Duplicate logic.
- Dead or unused code.
- Unused imports and dependencies.
- Misleading comments.
- Broad exception handling.
- Hardcoded configuration.
- Inconsistent validation.
- Incomplete or disconnected implementations.
- Unnecessary abstractions.
- Potential security and privacy weaknesses.

For each finding, provide:
1. Severity.
2. File path and relevant function or section.
3. Evidence.
4. Why it matters.
5. Recommended correction.
6. Potential regression risk.

Do not modify code during the audit. Separate confirmed defects from suggestions and tool-generated warnings.

## 3. Controlled Code Cleanup and Refactoring

Review the approved files for safe improvements.

Requirements:
- Preserve externally visible behaviour.
- Avoid changing function signatures unless approved.
- Avoid changing database contracts without a separate plan.
- Do not remove code merely because it appears unused without checking references.
- Do not add dependencies without justification.
- Keep the diff small and focused.

First provide the implementation plan and wait for approval. After implementation, run relevant regression tests and report the exact results.

## 4. Bug Investigation and Fixing

Investigate the reported issue before proposing a fix.

Steps:
1. Reproduce or trace the issue.
2. Identify the root cause.
3. Inspect related code and tests.
4. Check whether other workflows depend on the affected behaviour.
5. Propose the smallest safe correction.
6. Identify regression risks and required tests.

Do not hide symptoms with broad exception handling or weaken existing validation.

Wait for approval before implementing the fix.

## 5. New Feature Development

Develop only the explicitly requested feature.

Before implementation, document:
- User problem and expected outcome.
- Existing application behaviour.
- Proposed workflow.
- Backend, frontend and database implications.
- Files to create or modify.
- Files that must remain untouched.
- Security and privacy implications.
- Test and acceptance criteria.
- Risks and rollback considerations.

Preserve compatibility with existing workflows. Wait for approval before coding.

## 6. Database and Migration Audit

Review the requested database changes without executing production operations.

Inspect:
- Existing schema and migration history.
- Column and table dependencies.
- Foreign keys and indexes.
- Data integrity constraints.
- Migration ordering.
- Idempotency.
- Potential data loss.
- Rollback feasibility.
- Compatibility with existing records.

Use read-only inspection first.

Never run a production migration, destructive query or schema repair. Provide a safe local audit procedure and explicit owner-executed production steps where necessary.

## 7. Security and Student Privacy Audit

Review the requested application area for:
- Authentication and authorisation gaps.
- Student ownership validation.
- Insecure direct object references.
- CSRF weaknesses.
- Unsafe file uploads and path traversal.
- Sensitive information in logs or responses.
- Secret exposure.
- SQL injection and unsafe query construction.
- Insecure session handling.
- Excessive access to student records.
- Unnecessary third-party data sharing.

Prioritise confirmed risks and explain realistic attack scenarios.

Do not expose actual student data, credentials or tokens in the audit output.

Keep the audit read-only until changes are approved.

## 8. Testing and Regression Review

Review whether the current tests adequately protect the requested functionality.

Identify:
- Missing edge cases.
- Missing negative tests.
- Authentication and ownership test gaps.
- Database isolation issues.
- Flaky or environment-dependent tests.
- Duplicate or redundant tests.
- Missing regression coverage.

Do not delete or weaken tests to achieve a passing result.

Run only tests that are safe for the current environment. Report exact commands and results, including anything not run.

## 9. Dependency and Performance Audit

Review existing dependencies and application performance.

Look for:
- Unused or duplicated dependencies.
- Known vulnerable packages.
- Unnecessary package weight.
- N+1 database queries.
- Repeated expensive operations.
- Missing pagination.
- Excessive memory usage.
- Inefficient file and image handling.

Do not upgrade or remove dependencies automatically. Explain compatibility risks and recommend only changes with a clear benefit.

## 10. Documentation Review

Review the requested documentation for:
- Outdated instructions.
- Contradictions with actual application behaviour.
- Duplicate guidance.
- Missing setup or testing steps.
- Incorrect database or deployment assumptions.
- Unclear security and privacy instructions.

Verify statements against the actual repository before changing them.

Do not document planned features as if they already exist.

## 11. Final Development Session Review

Before completing a development task, review:

- Whether the approved scope was respected.
- Whether existing functionality was preserved.
- Whether the diff contains unrelated changes.
- Whether secrets or student data were introduced.
- Whether database changes are safe and documented.
- Whether appropriate regression tests were executed.
- Whether the documentation is accurate.
- Whether unresolved risks are clearly reported.

Provide a handoff containing:
1. Summary of changes.
2. Files changed.
3. Files deliberately not changed.
4. Exact test commands and results.
5. Manual verification steps.
6. Database and migration implications.
7. Known limitations and risks.
8. Branch and pull request details, where applicable.

---

## Universal Rules for Every Prompt

- One repository per working session.
- One approved task at a time.
- Inspect the working tree before changes.
- Preserve uncommitted local work.
- Follow the repository's existing branch and pull request rules.
- Do not create unnecessary branches.
- Do not commit, push, merge, delete branches, reset or rewrite history without the required explicit approval.
- Never modify production Aiven data or schema.
- Never expose secrets or real student information.
- Do not remove tests to make the suite pass.
- Do not fabricate test results.
- Explain technical decisions in accessible language.
- Ask before expanding scope.

## Engineering Principle

Stabilise the existing foundation first. Improve it incrementally, verify each change, and then continue feature development with regression and quality checkpoints.
