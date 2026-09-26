from exam_platform.ingestion.curriculum import CanonicalTaxonomyResolver
from exam_platform.ingestion.models import RawQuestion, SourceDocument
from exam_platform.ingestion.pipeline import QuestionIngestionPipeline


def taxonomy():
    return {
        "taxonomy_version": "test-1",
        "canonical_chapters": [
            {"id": "real_numbers", "name": "Real Numbers"},
            {"id": "algebra", "name": "Algebra"},
        ],
        "units": [
            {
                "unit_id": "cbse10_u1",
                "board": "CBSE",
                "class_level": 10,
                "subject_id": "maths",
                "unit_name": "Number Systems",
            },
            {
                "unit_id": "cbse10_u2",
                "board": "CBSE",
                "class_level": 10,
                "subject_id": "maths",
                "unit_name": "Algebra",
            },
        ],
        "mappings": [
            {
                "unit_id": "cbse10_u1",
                "board": "CBSE",
                "class_level": 10,
                "canonical_chapter_id": "real_numbers",
                "chapter_order": 1,
                "status": "VERIFIED",
            },
            {
                "unit_id": "cbse10_u2",
                "board": "CBSE",
                "class_level": 10,
                "canonical_chapter_id": "algebra",
                "chapter_order": 1,
                "status": "VERIFIED",
            },
        ],
    }


def test_resolver_matches_canonical_chapter_with_context():
    result = CanonicalTaxonomyResolver(taxonomy_data=taxonomy()).resolve(
        subject="Mathematics",
        board="cbse",
        class_level=10,
        chapter="  real numbers ",
    )

    assert result.status == CanonicalTaxonomyResolver.MATCHED
    assert result.canonical_chapter_id == "real_numbers"
    assert result.canonical_chapter_name == "Real Numbers"
    assert result.syllabus_unit_id == "cbse10_u1"


def test_resolver_does_not_fuzzy_guess_unknown_chapter():
    result = CanonicalTaxonomyResolver(taxonomy_data=taxonomy()).resolve(
        subject="Mathematics",
        board="CBSE",
        class_level=10,
        chapter="Real Number Applications",
    )

    assert result.status == CanonicalTaxonomyResolver.UNRESOLVED
    assert result.reason == "no_exact_canonical_mapping"


def test_pipeline_preserves_original_chapter_and_mapping_metadata():
    resolver = CanonicalTaxonomyResolver(taxonomy_data=taxonomy())
    raw = RawQuestion(
        raw_question_id="raw-1",
        source_id="source-1",
        raw_text="Find the HCF.",
        raw_marks=1,
        metadata={
            "question_type": "vsaq",
            "subject": "Mathematics",
            "board": "CBSE",
            "class_level": 10,
            "chapter": "Real Numbers",
        },
    )
    source = SourceDocument(
        source_id="source-1",
        source_type="ai_json",
        name="test.json",
    )

    candidate = QuestionIngestionPipeline(taxonomy_resolver=resolver).prepare(
        [raw], source
    )[0]

    assert candidate.status == "review_required"
    assert candidate.question.metadata["original_chapter"] == "Real Numbers"
    assert candidate.question.metadata["canonical_chapter_id"] == "real_numbers"
    assert candidate.question.metadata["curriculum_mapping_status"] == "MATCHED"
    assert QuestionIngestionPipeline.publishable(candidate)


def test_pipeline_keeps_unresolved_curriculum_non_publishable():
    resolver = CanonicalTaxonomyResolver(taxonomy_data=taxonomy())
    raw = RawQuestion(
        raw_question_id="raw-2",
        source_id="source-1",
        raw_text="Find x.",
        raw_marks=1,
        metadata={
            "question_type": "vsaq",
            "subject": "Mathematics",
            "board": "CBSE",
            "class_level": 10,
            "chapter": "Unknown Chapter",
        },
    )
    source = SourceDocument(
        source_id="source-1",
        source_type="ai_json",
        name="test.json",
    )

    candidate = QuestionIngestionPipeline(taxonomy_resolver=resolver).prepare(
        [raw], source
    )[0]

    assert candidate.status == "review_required"
    assert candidate.question.metadata["curriculum_mapping_status"] == "UNRESOLVED"
    assert not QuestionIngestionPipeline.publishable(candidate)
