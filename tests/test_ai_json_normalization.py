from question_bank.extraction.ai_json_extractor import AIJSONQuestionExtractor


def test_ai_json_normalizes_provider_question_types_and_mcq_answers():
    payload = {
        "schema_version": "1.0",
        "metadata": {"subject": "Mathematics", "board": "ICSE", "class": 10},
        "questions": [
            {
                "type": "MCQ",
                "chapter": "Algebra",
                "topic": "Quadratic Equations - Nature of Roots",
                "question_text": "Choose.",
                "options": ["1", "2", "4", "5"],
                "correct_answer": "4",
                "marks": 1,
            },
            {
                "type": "SHORT",
                "chapter": "Algebra",
                "topic": "Arithmetic Progression",
                "question_text": "Find the term.",
                "options": [],
                "marks": 3,
            },
            {
                "type": "LONG",
                "chapter": "Trigonometry",
                "topic": "Heights and Distances",
                "question_text": "Find the height.",
                "options": [],
                "marks": 4,
            },
            {
                "type": "ASSERTION_REASON",
                "chapter": "Trigonometry",
                "topic": "Trigonometric Identities",
                "question_text": "Assertion and reason.",
                "options": ["(a)", "(b)", "(c)", "(d)"],
                "correct_answer": "(c)",
                "marks": 1,
            },
        ],
    }

    questions = AIJSONQuestionExtractor(payload).extract()

    assert [q.metadata["question_type"] for q in questions] == [
        "mcq", "saq", "laq", "mcq"
    ]
    assert questions[0].raw_answer == "C"
    assert questions[3].raw_answer == "C"
    assert questions[0].metadata["chapter"] == "Quadratic Equations"
    assert questions[1].metadata["chapter"] == "Arithmetic Progressions"
    assert questions[2].metadata["chapter"] == "Heights and Distances"
    assert questions[3].metadata["chapter"] == "Trigonometric Identities"


def test_ai_json_keeps_ambiguous_multi_topic_chapters_for_review():
    payload = {
        "schema_version": "1.0",
        "metadata": {"subject": "Mathematics", "board": "ICSE", "class": 10},
        "questions": [
            {
                "type": "SHORT",
                "chapter": "Coordinate Geometry",
                "topic": "Section Formula & Equation of a Line",
                "question_text": "Find the point.",
                "options": [],
                "marks": 3,
            },
            {
                "type": "LONG",
                "chapter": "Geometry",
                "topic": "Loci and Constructions",
                "question_text": "Construct the figure.",
                "options": [],
                "marks": 4,
            },
        ],
    }

    questions = AIJSONQuestionExtractor(payload).extract()

    assert questions[0].metadata["chapter"] == "Coordinate Geometry"
    assert questions[1].metadata["chapter"] == "Geometry"
    assert questions[0].metadata["chapter_normalization"]["status"] == "UNCHANGED"
    assert questions[1].metadata["chapter_normalization"]["status"] == "UNCHANGED"
