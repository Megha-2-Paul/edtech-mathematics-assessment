# Mathematics Assessment & Improvement System — Canonical End-to-End Workflow

## 1. Product principle

This product is **not a mock-test platform**. Its core value is to answer:

> **Why is a student losing marks, and what should they improve next?**

The complete product loop is:

**Acquire → Register → Assess → Submit → Evaluate → Diagnose → Report → Communicate → Update Student Profile → Recommend Next Focus → Reassess → Measure Improvement**

The MVP should prove this loop with real paying students before adding AI grading, adaptive testing, parent dashboards, or other advanced features.

---

## 2. Target MVP

Initial market:

- CBSE / ICSE Mathematics
- Classes 10–12
- India
- Student-facing professional web exam experience
- Manual human evaluation of subjective answers
- Automated analytics and reporting
- WhatsApp + email communication

Google Forms may be used for administrative workflows if useful, but **not for the student examination experience**.

---

# 3. System architecture

```text
                         STUDENT
                            |
                            v
                 +----------------------+
                 |   Student Website   |
                 | Registration / Login |
                 | Take Test / Reports  |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |     Flask / API      |
                 | Exam + Auth + Pages  |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |        MySQL         |
                 | Single Source Truth  |
                 +----------+-----------+
                            |
                       Event/Webhook
                            |
                            v
                 +----------------------+
                 |         n8n           |
                 | Workflow Orchestration|
                 +----------+-----------+
                            |
             +--------------+--------------+
             |              |              |
             v              v              v
       +-----------+  +-----------+  +-----------+
       |  Python   |  |  Reports  |  | Messaging |
       | Analysis  |  | PDF/HTML  |  | WhatsApp  |
       | Engine    |  |           |  | Email     |
       +-----------+  +-----------+  +-----------+
             |              |              |
             +--------------+--------------+
                            |
                            v
                 +----------------------+
                 | Student Performance  |
                 | Profile / History    |
                 +----------+-----------+
                            |
                            v
                     NEXT ASSESSMENT
                            |
                            +----------> LOOP
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| Flask | Student website, exam UI, authentication, exam/session logic, APIs |
| MySQL | Persistent source of truth for students, tests, questions, attempts, evaluations and history |
| n8n | Workflow orchestration, notifications, scheduled jobs, integration between services |
| Python | Scoring, analytics, diagnosis, longitudinal comparison and recommendations |
| Report generator | Student PDF / HTML reports |
| WhatsApp | High-engagement notifications and result delivery |
| Email | Reports, records and formal communication |
| Question bank | Structured and validated questions with chapter/topic/difficulty/competency metadata |

---

# 4. End-to-end customer workflow

## Stage A — Acquisition

```text
Instagram / YouTube / Google / Referral / Tutor
                    |
                    v
               Landing Page
                    |
                    v
       Diagnostic Assessment Offer
                    |
                    v
          Register / Purchase
```

Primary positioning:

- "Why are you losing marks even when you know the Maths?"
- "Find out exactly where you're losing marks."

The initial product should sell a **diagnostic assessment + useful report**, not a generic mock-test subscription.

---

## Stage B — Registration

Student submits:

- Name
- Phone
- Email
- Class
- Board
- School (optional)

System creates a permanent `Student_ID`.

Example:

```text
STU000123
```

### n8n registration workflow

```text
Registration webhook
        |
        v
Validate registration
        |
        v
Create/update student in MySQL
        |
        v
Generate/confirm Student ID
        |
        v
Send welcome WhatsApp
        |
        v
Send confirmation email
```

---

# 5. Test creation and question-bank workflow

## Question pipeline

```text
Source PDF / Question Source
            |
            v
       Extraction
            |
            v
   Parse + structure question
            |
            v
   Validate with multiple signals
            |
      +-----+-----+
      |           |
   High         Low/
 confidence   uncertain
      |           |
      v           v
 Auto-accept  Exception Queue
                  |
                  v
              Human Review
                  |
                  v
              Question Bank
                  |
                  v
              Test Builder
```

Human review is an **exception queue**, not routine review of every extracted question.

Each question should retain metadata such as:

- Question_ID
- Subject
- Board
- Class
- Chapter
- Topic
- Subtopic
- Question type
- Difficulty
- Competency
- Marks
- Source
- Source year
- Content/assets
- Answer data where applicable
- Status

---

# 6. Test publishing

Admin creates/publishes:

```text
Test_ID
Date
Duration
Total marks
Board
Class
Subject
Test type
Questions
```

Eligible students are notified through n8n.

```text
Test Published
      |
      v
Find eligible students
      |
      v
WhatsApp notification
      |
      v
Email notification
```

---

# 7. Student exam workflow

```text
Student Login
      |
      v
Test Dashboard
      |
      v
Test Instructions
      |
      v
Start Test
      |
      v
Create Attempt
      |
      v
Exam Interface
```

The exam interface supports:

- MCQ questions
- Subjective questions
- Question navigation
- Answer persistence
- Countdown timer
- Handwritten answer upload
- Multiple pages per answer
- Submission confirmation

The current repository already contains this MVP exam experience and API structure.

---

# 8. Attempt lifecycle

```text
                +-------------+
                |   Available |
                +------+------+ 
                       |
                     START
                       |
                       v
                +-------------+
                | In Progress |
                +------+------+ 
                       |
             +---------+---------+
             |                   |
          SUBMIT              TIMEOUT
             |                   |
             v                   v
       +-----------+       +-----------+
       | Submitted |       |  Expired  |
       +-----------+       +-----------+
```

Production requirements:

- Server-authoritative timing
- Authentication
- Attempt ownership checks
- Duplicate-submission protection
- HTTPS
- Secure file storage
- Rate limiting
- Proper session/attempt locking

---

# 9. Submission workflow

Student clicks **Submit Test**.

Backend validates:

- Attempt exists
- Student owns attempt
- Attempt is still active
- Required handwritten uploads exist
- Attempt has not already been submitted

Then:

```text
attempt.status = submitted
submitted_at = timestamp
```

Student sees a submission confirmation. Marks are not shown until evaluation/analysis is complete.

The system emits:

```text
TEST_SUBMITTED
```

with:

```text
student_id
attempt_id
test_id
```

---

# 10. n8n submission workflow

```text
TEST_SUBMITTED webhook
          |
          v
Validate event
          |
          v
Load student + test + attempt
          |
          v
Load responses + answer images
          |
          v
Auto-evaluate objective responses
          |
          v
Create subjective evaluation task
          |
          v
Notify evaluator
```

n8n orchestrates this process; it does **not** contain the core mathematical analytics logic.

---

# 11. Objective/MCQ evaluation

For each objective question:

```text
Student answer
      |
      v
Compare with correct answer
      |
      v
marks_awarded
is_correct
answer_status
```

The evaluation is stored in MySQL.

---

# 12. Subjective evaluation workflow

Initially this is human evaluated.

Evaluator dashboard displays:

- Student answer images
- Question
- Maximum marks
- Student response
- Existing metadata
- Marks awarded field
- Error-code selection
- Comment field

Evaluator records:

```text
Question_ID
Marks_awarded
Error code(s)
Comment
Marks lost
```

Initial error codes:

```text
C01 Calculation
C02 Conceptual
C03 Formula
C04 Sign
C05 Incomplete steps
C06 Wrong method
C07 Missing justification
C08 Misunderstood question
C09 Time/attempt
```

Multiple error codes may be assigned to one response.

---

# 13. Evaluation completion

When all required subjective questions are evaluated:

```text
Evaluation Status = COMPLETE
```

System emits:

```text
EVALUATION_COMPLETED
```

n8n then starts the analysis workflow.

---

# 14. Python analysis engine

n8n sends:

```text
student_id
attempt_id
test_id
```

to the Python analysis service.

Python retrieves the complete assessment data from MySQL and calculates:

### Overall

- Score
- Percentage
- Attempt rate
- Accuracy
- Time taken

### Chapter/topic performance

- Marks by chapter
- Percentage by chapter
- Topic performance
- Competency performance

### Error analysis

- Error counts
- Marks lost by error type
- Error percentage
- Highest-impact error

### Longitudinal analysis

- Previous scores
- Score trend
- Accuracy trend
- Attempt trend
- Chapter trend
- Recurring errors
- Improvements
- Deterioration

---

# 15. Diagnosis engine

The first version is deterministic/rule-based, not AI.

Examples:

```text
IF calculation/sign errors are high
AND conceptual performance is strong
THEN diagnose accuracy/calculation weakness.
```

```text
IF chapter performance < threshold
THEN diagnose chapter weakness.
```

```text
IF direct questions are strong
AND application questions are weak
THEN diagnose application weakness.
```

```text
IF the same error appears across multiple tests
THEN mark it as a recurring error.
```

The diagnosis should explain **why marks were lost**, not merely rank students.

---

# 16. Student performance profile

After every evaluated test, update the student's longitudinal profile.

```text
Student Profile
    |
    +-- Score history
    +-- Percentage history
    +-- Attempt rate history
    +-- Accuracy history
    +-- Chapter strengths
    +-- Chapter weaknesses
    +-- Topic strengths/weaknesses
    +-- Competency performance
    +-- Error history
    +-- Recurring errors
    +-- Question history
    +-- Improvement areas
```

This profile is the foundation for future personalisation.

---

# 17. Recommendation engine

Initial recommendations are rule-based.

Examples:

```text
High C01/C04
→ accuracy and sign-error practice
```

```text
Weak chapter
→ chapter revision + targeted practice
```

```text
Good direct-question performance
but weak application performance
→ application/case-based practice
```

```text
Repeated incomplete-step errors
→ step-by-step solution/presentation practice
```

Do not build AI recommendations before this rule-based system proves useful.

---

# 18. Report generation

Python/reporting service generates an individual report.

Recommended structure:

1. Student name / ID
2. Test number/date
3. Score and percentage
4. Attempt rate
5. Accuracy
6. Where marks were lost
7. Chapter analysis
8. Topic/competency analysis where useful
9. Error analysis
10. Strengths
11. Weaknesses
12. Repeated mistakes
13. Comparison with previous assessment
14. Recommended focus
15. Next-step practice recommendation

The report must be understandable to a student/guardian and avoid Data Science jargon.

---

# 19. Report delivery

```text
Analysis Complete
       |
       v
Generate PDF
       |
       v
Store report securely
       |
       v
n8n Report-Ready Workflow
       |
       +---------> WhatsApp
       |
       +---------> Email
       |
       +---------> Student Dashboard
```

### WhatsApp result message

Include:

- Score
- Previous score
- Improvement
- Biggest weakness
- Strongest area
- Report link

### Email

Include the report as attachment or secure link and maintain it as the formal record.

---

# 20. Student dashboard

After login, the student should eventually see:

```text
My Progress

Test 1    48/80
Test 2    54/80
Test 3    61/80
Test 4    67/80
```

And:

```text
Accuracy trend
Chapter performance
Recurring mistakes
Improvement areas
Recent reports
Next recommended focus
```

This dashboard should be built after the assessment → report loop works reliably.

---

# 21. Next-assessment workflow

Initially use scheduled/predefined tests rather than full adaptive testing.

```text
Student Profile
      |
      v
Weakest chapters
      |
      v
Recurring errors
      |
      v
Unmastered competencies
      |
      v
Recommended focus
      |
      v
Next scheduled assessment
```

Later, the system can evolve toward personalised/adaptive test generation.

---

# 22. n8n workflow inventory

## Workflow 1 — Registration

```text
Registration → MySQL → Student ID → WhatsApp/Email
```

## Workflow 2 — Test Published

```text
Test Published → Eligible Students → WhatsApp/Email
```

## Workflow 3 — Test Reminder

```text
Schedule → Find eligible students who have not attempted → Reminder
```

## Workflow 4 — Submission

```text
Submission → Validate → Auto-score objective → Create evaluation task → Notify evaluator
```

## Workflow 5 — Evaluation Complete

```text
Evaluation Complete → Python Analysis → Update Profile → Generate Report
```

## Workflow 6 — Report Delivery

```text
Report Ready → WhatsApp + Email + Dashboard notification
```

## Workflow 7 — Follow-up

```text
Delay → Check next assessment participation → Reminder if needed
```

## Workflow 8 — Monthly Progress

```text
Schedule → Python cumulative analysis → Monthly report → Email
```

---

# 23. What n8n must NOT own

Do not put the following core logic inside n8n:

- Mathematical scoring algorithms
- Complex analytics
- Diagnosis rules that belong in the analysis engine
- Authentication
- Exam UI
- Timer authority
- Core database model
- Question-selection intelligence
- AI grading

n8n is the **orchestrator**, not the assessment engine.

---

# 24. MVP production architecture

The first production version should be:

```text
Student
  |
  v
Flask web application
  |
  +---- MySQL
  |
  +---- Secure object storage for answer images/reports
  |
  +---- n8n webhooks
           |
           +---- Python analysis service
           |
           +---- Email
           |
           +---- WhatsApp
```

A single appropriately sized VPS can initially host Flask, MySQL and self-hosted n8n to minimise cost. Object storage should be separated from the application server as usage grows.

---

# 25. Security/production requirements before public launch

Must have:

- HTTPS
- Production secret management
- Proper student authentication
- Password/session security
- Server-authoritative timer
- Attempt locking
- Authorization checks
- Secure answer-image storage
- File type/content validation
- File size limits
- Rate limiting
- Database backups
- Error logging
- Audit trail for evaluation changes
- Secure report links
- Privacy/consent handling for student data

The current prototype explicitly identifies authentication, server-side timing, rate limiting, attempt locking and persistent storage as production gaps; these must be closed before a public high-stakes assessment launch.

---

# 26. What NOT to build before validation

Do not make these launch blockers:

- AI automatic grading
- Handwriting OCR
- Fully adaptive testing
- Parent dashboard
- Tutor dashboard
- Mobile app
- Multiple subjects
- State boards
- JEE
- Large annual subscription system
- Complex gamification

The first commercial milestone is **20–30 real paying students**, not a large technology platform.

---

# 27. MVP launch definition

The product is ready for a controlled paid launch when one real student can complete this complete loop reliably:

```text
Register
  ↓
Pay / receive assessment access
  ↓
Login
  ↓
Take professional online assessment
  ↓
Submit MCQ + handwritten answers
  ↓
Human evaluation
  ↓
Error codes C01–C09
  ↓
Python analysis
  ↓
Individual PDF report
  ↓
WhatsApp + Email delivery
  ↓
Student profile updated
  ↓
Next-focus recommendation
  ↓
Second assessment
  ↓
Improvement comparison
```

The key validation question is:

> **Do students/guardians find the diagnosis useful enough to take another assessment?**

If yes, continue building. If no, improve the product value before adding technology.

---

# 28. Development order

### Phase 1 — Stabilise foundation

1. Make MySQL the authoritative persistence layer.
2. Cleanly separate Flask service/data-access layers.
3. Add authentication.
4. Add production-grade server-side timing.
5. Secure answer/report storage.

### Phase 2 — Evaluation

6. Build evaluator dashboard.
7. Implement C01–C09 error coding.
8. Store marks, marks lost and comments.
9. Add evaluation completion state/audit trail.

### Phase 3 — Intelligence

10. Build Python scoring/analytics engine.
11. Build chapter/topic/competency analysis.
12. Build recurring-error detection.
13. Build deterministic diagnosis rules.
14. Build recommendation engine.

### Phase 4 — Reporting + automation

15. Build PDF report generator.
16. Create n8n registration workflow.
17. Create submission/evaluation workflow.
18. Create analysis/report workflow.
19. Integrate email.
20. Integrate WhatsApp.

### Phase 5 — Student experience

21. Build cumulative student dashboard.
22. Add previous-test comparison.
23. Add next-focus recommendations.
24. Add second/third assessment loop.

### Phase 6 — Commercial launch

25. Integrate payment gateway.
26. Deploy production infrastructure.
27. Run controlled pilot.
28. Measure registration → payment → attempt → report → second test → retention/referral.
29. Improve based on real behaviour.

### Phase 7 — Later scale

30. AI-assisted evaluation.
31. Handwriting/OCR assistance.
32. Personalised question selection.
33. Tutor/coaching dashboard.
34. Parent dashboard.
35. Additional subjects/boards.

---

# 29. Core business loop

```text
TEST
  ↓
EVALUATION
  ↓
ERROR DIAGNOSIS
  ↓
ANALYSIS
  ↓
REPORT
  ↓
PERSONALISED FOCUS
  ↓
NEXT TEST
  ↓
IMPROVEMENT MEASUREMENT
  ↓
UPDATED PROFILE
  ↓
NEXT TEST
```

**This loop — not the exam UI, AI, or number of questions — is the product.**
