# Expanded Product Scope and Controlled Pilot Workflow

## 1. Scope decision

Improvia is expanding its initial controlled pilot from the earlier **Classes 10–12 Mathematics** focus to:

### Mathematics
- CBSE Classes 9–12 — Mathematics
- CBSE Classes 11–12 — Applied Mathematics (241)
- ICSE Classes 9–10 — Mathematics
- ISC Classes 11–12 — Mathematics

The exact official chapter name is stored at the curriculum layer. Cross-board concepts are stored separately for analytics and controlled question reuse.

### Computer-related subjects
The platform now models these as distinct subjects rather than one generic “Computer” value:

- CBSE IX–X — Information Technology (402)
- CBSE X — Computer Applications (165)
- CBSE XI–XII — Computer Science (083)
- CBSE XI–XII — Informatics Practices (065)
- ICSE IX–X — Computer Applications (86)
- ISC XI–XII — Computer Science (868)

A student's subject enrollment is stored separately from the core Student record so one Student_ID can hold multiple active subjects.

## 2. Initial real-student pilot

The first controlled pilot can use the two available students:

### Student A
**Class 10 CBSE**

Pilot:
- Mathematics
- The student's actual computer subject, selected explicitly as either Information Technology (402) or Computer Applications (165)

### Student B
**Class 9 ICSE**

Pilot:
- Mathematics

This gives Improvia an early test across:

- Class 9 and Class 10
- CBSE and ICSE
- Mathematics
- Computer-related subject assessment

This is a **product validation pilot**, not evidence that the whole expanded market is already validated.

## 3. Why expand the pilot now?

The purpose is not to add subjects for the sake of having a larger catalogue.

The purpose is to test whether the core Improvia experience works across different academic contexts:

**Test → Evaluation → Diagnosis → Feedback → Practice → Reassessment → Progress**

The central question remains:

> **Does the assessment help a student understand what is going wrong and what to work on next?**

## 4. Subject-specific diagnosis

The diagnosis framework must be subject-aware.

### Mathematics

The initial Mathematics categories are:

- Calculation Error
- Conceptual Error
- Formula Error
- Sign Error
- Incomplete Steps
- Wrong Method
- Missing Justification
- Misunderstood Question
- Time / Attempt Issue

These categories are intentionally useful for Maths and may evolve as real assessments are evaluated.

### Computer / IT

Do **not** force the Mathematics error categories onto Computer subjects.

First validate the exact CBSE subject and syllabus, then define appropriate assessment dimensions such as knowledge/recall, concept understanding, application, procedure/steps, interpretation, practical/technical execution, or time/attempt where relevant.

The exact diagnostic framework should be determined from the actual syllabus, question types and marking requirements before public launch.

## 5. Pilot workflow

### Step 1 — Select the exact curriculum

For every assessment, identify:

**Board → Class → Subject → Academic Year → Syllabus**

Examples:

**CBSE → Class 10 → Mathematics → 2026–27**

**CBSE → Class 10 → Information Technology (402) → 2026–27**

**CBSE → Class 10 → Computer Applications (165) → 2026–27**

**ICSE → Class 9 → Mathematics → applicable academic year**

Do not use an ambiguous “Computer” subject value when a board provides separate subjects.

### Step 2 — Build a focused assessment

The first assessment should be manageable enough to evaluate carefully.

The goal is not maximum question count.

The goal is to produce a useful diagnosis.

### Step 3 — Student takes the assessment

The student receives:

- Assessment instructions
- Duration
- Submission instructions
- Answer submission requirements

### Step 4 — Evaluate

Initially, subjective work is manually evaluated.

For each response, capture:

- Marks
- Relevant error/diagnostic category
- Short evaluator comment

### Step 5 — Generate the diagnosis

Analyse:

- Overall performance
- Chapter/topic or unit performance
- Question-type performance
- Marks lost
- Error/diagnostic patterns
- Recurring issues where enough history exists

### Step 6 — Create the report

The report should answer:

> **What happened?**

> **Why did it happen?**

> **What should the student focus on next?**

Avoid technical/data-science language in the student-facing report.

### Step 7 — Student/parent feedback

After delivering the report, ask:

- Was the analysis understandable?
- Did it reveal something you did not already know?
- Was the recommended focus useful?
- Would you change what you practise because of the report?
- Would you take another assessment?
- Would you recommend it to a friend?

This feedback is part of the pilot.

### Step 8 — Reassess

Where practical, give the student a second assessment after targeted practice.

The purpose is to see whether the diagnosis leads to a meaningful change in preparation and whether the next assessment reveals measurable changes.

## 6. Referral workflow

The two pilot students can also become the first referral channel, but only after they have experienced the product.

The intended sequence is:

**Assessment → Useful report → Student understands value → Student shares with friend → New registration**

Do not treat a friend referral as proof of product-market fit by itself. Track whether referred students actually register, take the assessment, view the report and return for another assessment.

A simple student referral message can focus on the experience:

> “I tried an Improvia assessment and it showed me where I was losing marks—not just my score. You should try it if you want to understand your Maths performance.”

## 7. Validation metrics for this pilot

Track:

- Registration
- Registration → assessment start
- Assessment start → submission
- Submission → completed evaluation
- Report viewed
- Student/parent feedback
- Report usefulness
- Recommended practice followed
- Assessment 1 → Assessment 2
- Referral attempts
- Referred registrations
- Referred assessment starts
- Repeat assessment
- Willingness to pay after the free pilot

The key question is:

> **Do students find the diagnosis useful enough to come back and take another assessment?**

## 8. Expansion rule

Adding a new class, board or subject should follow:

**Curriculum validation → Question availability → Assessment quality → Evaluation framework → Diagnosis quality → Pilot with real students → Feedback → Repeat usage → Commercial validation**

Do not add a large number of subjects simply because the database can store them.

## 9. Current positioning

The product can now be described at a high level as:

> **Improvia is building an assessment and improvement platform for school students that goes beyond the score to help them understand where they are losing marks, why it is happening, and what to work on next.**

The platform taxonomy currently supports the verified 2026–27 curriculum scope above. The controlled real-student pilot remains deliberately smaller; expanding database capability does not mean all curricula are commercially validated.

## 10. Important product principle

The expansion does not change the core idea.

Improvia is still not primarily selling:

> **“More tests.”**

It is selling:

> **“More useful information from every test.”**

The long-term loop remains:

**Test → Understand → Improve → Test Again → Track Progress**
