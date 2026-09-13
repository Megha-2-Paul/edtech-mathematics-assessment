# Exam Platform Report

## Current platform

The project contains a Flask-based web exam platform backed by MySQL. It is designed for Mathematics assessment rather than a generic mock-test-only experience.

## Student experience

The student flow supports:

- Test listing
- Test instructions
- Attempt creation
- MCQ questions
- Subjective questions with predefined final-answer choices
- Configurable handwritten solution uploads
- Answer persistence
- Question navigation
- Countdown timer
- Submission confirmation
- Retake/duplicate-submission prevention
- Result and performance-report views

## Teacher/admin experience

The current foundation includes:

- Question-bank management
- Question metadata
- Marks and answer choices
- Handwritten-upload configuration
- Test creation
- Submission list
- Manual subjective evaluation
- Error-code capture

## Evaluation and diagnosis

Objective answers can be checked against stored correct answers. Subjective answers are intended to be evaluated by a human in the MVP.

The initial error taxonomy is C01–C09 for calculation, conceptual, formula, sign, incomplete-step, wrong-method, missing-justification, misunderstood-question, and time/attempt problems.

Evaluation data feeds result calculation, diagnosis and reporting.

## Data and persistence

MySQL is the persistent source of truth. The data model is designed to retain question, test, attempt, response, evaluation and history information so that performance can be compared over time.

## Analytics/reporting direction

The system is intended to calculate:

- Score and percentage
- Attempt rate
- Accuracy where available
- Chapter/topic performance
- Marks lost
- Error distribution
- Strengths and weaknesses
- Recurring errors
- Previous-test comparison
- Recommended next focus

## Architecture direction

```text
Student Website
      ↓
Flask / API
      ↓
MySQL
      ↓
Evaluation + Analytics + Diagnosis
      ↓
Report + Student Profile
      ↓
Next Assessment
```

n8n can later orchestrate notifications and scheduled workflows. Python remains the appropriate place for structured analysis and report generation.

## Testing status

The code has been through readability/organization cleanup, but the complete local MySQL workflow still needs functional testing. Testing should occur before further structural refactoring.

## Future work

Potential later stages include automated reporting/communication, cumulative student dashboards, AI-assisted evaluation and scalable tutor/school workflows. These are intentionally not prerequisites for the MVP validation.
