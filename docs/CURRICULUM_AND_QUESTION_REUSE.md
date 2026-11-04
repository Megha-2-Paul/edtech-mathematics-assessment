# Curriculum and Cross-Board Question Reuse

## Purpose

Improvia must preserve exact official syllabus wording while allowing genuinely equivalent questions to be reused across boards/classes when the underlying curriculum concept and assessment requirements are compatible.

## Three layers

1. Official curriculum: Board, Class, Subject, Academic year, Unit, Official chapter name.
2. Canonical concept: a stable analytics concept shared across curricula.
3. Question applicability: a question is linked to one or more curriculum chapters through question_curriculum_map.

Compatibility must be explicitly approved as EXACT, CONCEPT_MATCH, or BOARD_SPECIFIC. REVIEW_REQUIRED prevents automatic reuse.

## Important rule

A shared chapter name, similar wording, or similar mathematical concept does not automatically make a question reusable.

Example: CBSE XI uses Conic Sections while ISC XI uses Conic Section. A question may still be reusable when its content is within both syllabi, but that reuse must be represented by two curriculum mappings to the same question.

## Database model

- subject_catalog: subject identity and code.
- curriculum_catalog: Board + Class + Subject + Academic Year.
- curriculum_units: official syllabus units in order.
- curriculum_chapters: exact official chapter name plus canonical analytics concept.
- canonical_concepts: cross-board analytics concepts.
- question_curriculum_map: maps a question to every curriculum where it is approved.
- student_subject_enrollments: allows one Student_ID to take multiple subjects without duplicate student records.

## Reuse example

One question Q00123 may have:
- CBSE X → Probability → EXACT
- ICSE X → Probability → EXACT

The question is stored once; curriculum mappings determine where it may appear.

## Current implementation

Migration 005_curriculum_question_reuse.py creates the new tables, seeds the 2026–27 curriculum registry, backfills legacy student subject records into enrollments, and automatically creates only exact official-name question mappings. Cross-board mappings that require conceptual judgment remain REVIEW_REQUIRED until explicitly approved.
