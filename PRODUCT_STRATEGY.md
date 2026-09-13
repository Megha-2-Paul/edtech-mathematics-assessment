# Product Strategy & Launch Scope

## 1. Commercial launch decision

### Launch with one subject, not all subjects.

**Initial commercial product:**

- Board: CBSE
- Class: Class 12
- Subject: Mathematics
- Geography: India
- Product: Mathematics Diagnostic + Improvement System

The architecture must remain subject/board/class configurable so that additional subjects can be added later without redesigning the core data model.

### Expansion path

```text
CBSE Class 12 Mathematics
        ↓
CBSE Class 10 Mathematics
        ↓
CBSE Class 11 Mathematics
        ↓
ICSE Mathematics
        ↓
Other subjects
        ↓
Tutor / coaching / school assessment infrastructure
```

Do not launch all subjects merely because the software can support them. Validation should happen one narrow market at a time.

---

## 2. Product positioning

Do not position the product as another generic mock-test series.

Primary promise:

> **Why are you losing marks even when you know the Maths?**

Supporting promise:

> **Find out exactly where you're losing marks, what to fix next, and whether you're actually improving.**

The test is the input. Diagnosis and measurable improvement are the product value.

---

## 3. Core improvement loop

```text
Baseline Assessment
        ↓
Evaluation
        ↓
Mark-Loss Map
        ↓
Chapter / Topic / Competency Analysis
        ↓
Knowledge vs Execution Diagnosis
        ↓
Recurring Error Detection
        ↓
Top 3 Improvement Priorities
        ↓
Personalised Next Focus
        ↓
Targeted Practice
        ↓
Next Assessment
        ↓
Test-to-Test Comparison
        ↓
Explain Why Score Changed
        ↓
Measure Improvement
        ↓
Updated Student Profile
        ↓
Repeat
```

---

## 4. Diagnostic report requirements

Every evaluated assessment should produce a student-friendly report.

### Core sections

1. Student name / ID
2. Test number and date
3. Score and percentage
4. Attempt rate
5. Accuracy
6. Marks lost by reason
7. Mark-Loss Map
8. Chapter performance
9. Topic performance where reliable
10. Competency performance where reliable
11. Strengths
12. Weaknesses
13. Recurring mistakes
14. Knowledge vs execution diagnosis
15. Comparison with previous assessment
16. Explanation of score change
17. Top 3 next priorities
18. Recommended next focus
19. Practice recommendation
20. Next assessment target

Do not expose internal error codes such as C01/C04 to students as the primary language. The evaluator/database may use codes; students should see readable labels such as Calculation Errors and Sign Errors.

---

## 5. Mark-Loss Map

The report must answer:

> **Where did my lost marks go?**

Example:

```text
Calculation          6 marks
Incomplete steps     4 marks
Conceptual           3 marks
Sign                  2 marks
Unattempted           3 marks
Other                 1 mark
---------------------------
Total lost           19 marks
```

The report should highlight the highest-impact improvement opportunity rather than overwhelm the student with every metric.

---

## 6. Knowledge vs execution diagnosis

The system should distinguish between:

### Knowledge problems

- Conceptual gaps
- Formula gaps
- Weak chapter/topic knowledge
- Weak application/reasoning

### Execution problems

- Calculation errors
- Sign errors
- Incomplete steps
- Wrong method execution
- Missing justification
- Misunderstanding the question
- Time/attempt problems

Example diagnosis:

> **Conceptual understanding is relatively strong, but execution accuracy is causing significant mark loss.**

This distinction is central to personalised recommendations.

---

## 7. Recurring error engine

An error becomes more important when it repeats across assessments.

Example:

```text
Test 1 → Calculation error
Test 2 → Calculation error
Test 3 → Calculation error
```

The system should label it:

> **Recurring error: Calculation**

Possible statuses:

- New
- Improving
- Persistent
- Resolved
- Reappeared

Do not mark a weakness as persistent from one assessment alone.

---

## 8. Test-to-test improvement explanation

Do not report only:

> 61 → 68 = +7 marks

Explain the likely sources of change.

Example:

```text
+3 marks  fewer calculation errors
+2 marks  better completion
+2 marks  stronger Integrals performance
```

The system should identify both positive and negative contributors where the data supports them.

---

## 9. Top 3 priorities

The report should not produce an overwhelming list of recommendations.

Return a maximum of three high-priority actions.

Example:

```text
1. Improve calculation accuracy
2. Revise Applications of Integrals
3. Practise timed application questions
```

Recommendations should be actionable and linked to observed evidence.

---

## 10. Next-test focus

Initially this is rule-based, not AI-driven.

The next assessment can deliberately include more questions matching the student's current needs.

Example:

```text
High calculation/sign errors
→ accuracy-focused questions

Weak chapter
→ targeted chapter questions

Strong direct questions + weak application
→ application/case-based questions

Repeated incomplete steps
→ multi-step written questions
```

Full adaptive testing is a later phase.

---

## 11. Student performance profile

The student's profile should accumulate evidence across assessments:

```text
Student Profile
├── Score history
├── Percentage history
├── Attempt history
├── Accuracy history
├── Chapter strengths
├── Chapter weaknesses
├── Topic strengths/weaknesses
├── Competency performance
├── Error history
├── Recurring errors
├── Error status
├── Question history
├── Improvement areas
├── Previous recommendations
└── Improvement outcomes
```

This longitudinal profile is more strategically important than any single test score.

---

## 12. Personal Best and progress presentation

Use self-comparison rather than competitive leaderboards.

Show:

- Current score
- Previous score
- Personal best
- Average score
- Improvement trend
- Error reduction

Example:

> **Personal Best: 72/80**
>
> Current: 68/80
>
> 4 marks from your best.

Avoid leaderboards in the initial product because the core proposition is improvement, not competition.

---

## 13. Parent summary

Each report should eventually have a short parent/guardian summary.

Example structure:

```text
Current score: 68/80
Previous score: 61/80
Improvement: +7

Biggest improvement:
Calculation accuracy

Current concern:
Application-based questions

Recurring issue:
Incomplete steps

Recommended focus:
Integrals + timed application practice
```

Parents care about measurable progress and the reason behind the score, not technical analytics terminology.

---

## 14. Optional confidence-vs-performance signal

Later, ask the student to rate confidence by chapter/topic before or after an assessment.

Compare:

```text
Self-confidence
        vs
Demonstrated performance
```

If confidence is high but performance is weak, the report may flag a calibration gap.

This is a later enhancement, not a launch blocker.

---

## 15. Marks-opportunity metric

The system may estimate marks that appear potentially recoverable through fixing execution or known weaknesses.

Example:

> **17 marks were potentially recoverable from calculation, incomplete-step and unattempted losses.**

Use careful wording. Never guarantee that those marks will be recovered.

---

## 16. Free lead-generation tool

Potential future website tool:

### Mark-Loss Calculator

Student enters approximate:

- Score
- Calculation errors
- Sign errors
- Incomplete answers
- Unattempted marks

The tool estimates where marks are being lost and leads to the full diagnostic.

This is a marketing/lead-generation feature, not core assessment infrastructure.

---

## 17. Pricing strategy for validation

Do not launch with a large subscription catalogue.

Initial experiments:

### Full Diagnostic

**₹99 introductory price**

Includes:

- Full assessment
- Human evaluation
- Error analysis
- Mark-Loss Map
- Chapter analysis
- Strengths/weaknesses
- Top 3 priorities
- PDF report

After validation, test ₹149–₹199 depending on report quality and evaluation cost.

### Improvement Pack

Potential later offer:

**₹399–₹499 for 3 assessments**

Value is the improvement journey, cumulative analysis and comparison — not merely the number of tests.

### Monthly plans

Only introduce after evidence that students return for another assessment.

Potential experiments:

- Basic: ₹299/month
- Plus: ₹499/month
- Intensive/manual: ₹699–₹999/month

These are hypotheses and must be validated against conversion, retention, evaluation time and willingness to pay.

---

## 18. Marketing strategy

### Primary message

> **Why are you losing marks even when you know the Maths?**

### Secondary message

> **Don't just know your score. Know why you lost the marks.**

### Organic channels first

- Instagram
- YouTube Shorts
- YouTube
- WhatsApp
- Referrals
- Tutor relationships
- Search/SEO over time

Do not start with significant paid advertising.

### Content themes

1. Lost-mark analysis
2. Answer-sheet evaluation examples
3. Common CBSE Maths mistakes
4. Calculation/sign/presentation mistakes
5. Why correct answers can still lose marks
6. Chapter weakness examples
7. Student before/after improvement
8. Exam strategy based on observed errors
9. “Where did the marks go?” series

The product should generate anonymised insights that can later become content.

---

## 19. Marketing funnel

```text
Instagram / YouTube / Search / Referral / Tutor
                    ↓
              Useful content
                    ↓
             Landing page
                    ↓
          Free mini diagnostic
                    ↓
          ₹99 full diagnostic
                    ↓
               Assessment
                    ↓
               Diagnosis
                    ↓
                 Report
                    ↓
          Improvement recommendation
                    ↓
              Retest / Pack
                    ↓
               Retention
                    ↓
               Referral
```

The key conversion metric is not followers. It is:

> **Test 1 → Test 2 conversion**

If students do not return because the diagnosis is not useful, adding technology or increasing marketing spend is unlikely to fix the business.

---

## 20. Tutor/channel strategy

After initial B2C validation, test private tutors and small coaching centres.

Potential offer:

```text
Tutor gives assessment to 20–50 students
          ↓
Platform handles submission/evaluation workflow
          ↓
Individual student reports
          ↓
Batch-level error analysis
          ↓
Tutor receives actionable class insights
```

This may eventually have better acquisition economics than direct-to-student advertising.

Do not build a full tutor dashboard until there is evidence of tutor demand.

---

## 21. Business validation gates

### Gate 1 — Product usefulness

20–30 real paying students.

Measure:

- Registration → payment
- Payment → attempt
- Attempt → report viewed
- Satisfaction
- Evaluation time
- Referral rate

### Gate 2 — Retention

Measure:

- Test 1 → Test 2
- Test 2 → Test 3
- Repeat purchase
- Improvement after recommendations

### Gate 3 — Economics

Measure:

- Acquisition cost
- Evaluation cost/time
- Infrastructure cost/student
- Gross contribution per student
- Willingness to pay

### Gate 4 — Scale

Only after the first three gates are healthy:

- Automate more evaluation
- Add personalised practice
- Add more classes/boards
- Add tutor/coaching workflows
- Consider AI-assisted evaluation

---

## 22. Explicit non-goals before validation

Do not make these launch blockers:

- AI automatic grading
- OCR/handwriting recognition
- Fully adaptive testing
- Mobile apps
- Parent dashboard
- Tutor dashboard
- Multiple subjects
- JEE
- State boards
- Large annual subscription catalogue
- Heavy gamification
- Large paid advertising budget

---

## 23. Architecture principle

### Multi-subject-ready architecture, single-subject commercial launch.

The database and services should support:

```text
Board
Class
Subject
Chapter
Topic
Subtopic
Competency
Question
Assessment
Evaluation
Error
Student Profile
```

But the initial customer-facing catalogue should expose only:

```text
CBSE
└── Class 12
    └── Mathematics
```

This keeps the codebase scalable without making the business proposition broad.

---

## 24. Product success definition

The MVP is successful when a student can say:

> **“I now understand why I lost marks, I know exactly what to work on, and my next assessment shows whether I improved.”**

That is the product outcome to optimise for.
