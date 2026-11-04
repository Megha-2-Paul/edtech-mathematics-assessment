import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_taxonomy():
    return json.loads((ROOT / "curriculum_taxonomy_2026_27.json").read_text(encoding="utf-8"))


def test_taxonomy_covers_required_curricula():
    data = load_taxonomy()
    keys={(c["board"],c["class_level"],c["subject_id"]) for c in data["curricula"]}
    required={
        ("CBSE",9,"mathematics"),("CBSE",10,"mathematics"),
        ("CBSE",11,"mathematics"),("CBSE",12,"mathematics"),
        ("ICSE",9,"mathematics"),("ICSE",10,"mathematics"),
        ("ISC",11,"mathematics"),("ISC",12,"mathematics"),
        ("CBSE",9,"cbse_information_technology"),("CBSE",10,"cbse_information_technology"),
        ("CBSE",10,"cbse_computer_applications"),
        ("CBSE",11,"cbse_computer_science"),("CBSE",12,"cbse_computer_science"),
        ("CBSE",11,"cbse_informatics_practices"),("CBSE",12,"cbse_informatics_practices"),
        ("ICSE",9,"icse_computer_applications"),("ICSE",10,"icse_computer_applications"),
        ("ISC",11,"isc_computer_science"),("ISC",12,"isc_computer_science"),
    }
    assert required <= keys


def test_official_names_preserve_board_specific_wording():
    data=load_taxonomy()
    by={(c["board"],c["class_level"],c["subject_id"]):c for c in data["curricula"]}
    cbse11=[x["official_chapter_name"] for u in by[("CBSE",11,"mathematics")]["units"] for x in u["chapters"]]
    isc11=[x["official_chapter_name"] for u in by[("ISC",11,"mathematics")]["units"] for x in u["chapters"]]
    cbse12=[x["official_chapter_name"] for u in by[("CBSE",12,"mathematics")]["units"] for x in u["chapters"]]
    isc12=[x["official_chapter_name"] for u in by[("ISC",12,"mathematics")]["units"] for x in u["chapters"]]
    assert "Conic Sections" in cbse11 and "Conic Section" in isc11
    assert "Introduction to Three-dimensional Geometry" in cbse11
    assert "Introduction to Three Dimensional Geometry" in isc11
    assert "Application of the Integrals" in cbse12
    assert "Applications of Integrals" in isc12


def test_no_generic_computer_subject():
    names={s["name"] for s in load_taxonomy()["subjects"]}
    assert "Computer" not in names


def test_migration_version_matches_taxonomy():
    import importlib.util
    migration_path = ROOT / "question_bank" / "migrations" / "005_curriculum_question_reuse.py"
    spec = importlib.util.spec_from_file_location("curriculum_migration", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.VERSION == load_taxonomy()["taxonomy_version"]


def test_board_specific_mathematics_codes():
    data = load_taxonomy()
    by = {(c["board"], c["class_level"], c["subject_id"]): c for c in data["curricula"]}
    assert by[("CBSE", 10, "mathematics")]["subject_code"] == "041"
    assert by[("ICSE", 10, "mathematics")]["subject_code"] == "51"
    assert by[("ISC", 11, "mathematics")]["subject_code"] == "860"


def test_migration_audit_expected_counts():
    import importlib.util
    migration_path = ROOT / "question_bank" / "migrations" / "005_curriculum_question_reuse_audit.py"
    spec = importlib.util.spec_from_file_location("curriculum_migration_audit", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = load_taxonomy()
    curricula, chapters = module.expected_curriculum_counts(data)
    assert curricula == len(data["curricula"])
    assert chapters == sum(
        len(unit["chapters"])
        for curriculum in data["curricula"]
        for unit in curriculum["units"]
    )


def test_migration_upserts_use_real_target_columns():
    migration_path = ROOT / "question_bank" / "migrations" / "005_curriculum_question_reuse.py"
    source = migration_path.read_text(encoding="utf-8")

    # Avoid VALUES(<column>) aliases entirely: they are easy to mistype and have
    # already caused production failures against the real Aiven schema.
    assert "VALUES(subject)" not in source
    assert "VALUES(canonical_concept)" not in source
    assert "VALUES(canonical_concept_id)" not in source

    assert "subject_name=:name,subject_code=:code,active=1" in source
    assert "concept_name=:name,subject_id=:subject,active=1" in source
    assert "subject_code=:code,status='VERIFIED'" in source
    assert "unit_name=:name,unit_order=:order" in source
    assert "official_chapter_name=:name,canonical_concept_id=:concept,status='VERIFIED'" in source



def test_canonical_concept_ids_are_subject_scoped_but_keep_aliases():
    import importlib.util
    migration_path = ROOT / "question_bank" / "migrations" / "005_curriculum_question_reuse.py"
    spec = importlib.util.spec_from_file_location("curriculum_migration", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.canonical_concept_id("mathematics", "Probability") != module.canonical_concept_id(
        "applied_mathematics", "Probability"
    )
    assert module.canonical_concept_id("mathematics", "Trigonometry") == module.canonical_concept_id(
        "mathematics", "Introduction to Trigonometry"
    )


def test_subject_context_resolves_duplicate_display_names_by_board_and_class():
    import importlib.util
    migration_path = ROOT / "question_bank" / "migrations" / "005_curriculum_question_reuse_audit.py"
    spec = importlib.util.spec_from_file_location("curriculum_migration_audit", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    index = module.subject_context_index(load_taxonomy())

    assert module.resolve_subject_id(index, "CBSE", 10, "Computer Applications") == "cbse_computer_applications"
    assert module.resolve_subject_id(index, "ICSE", 10, "Computer Applications") == "icse_computer_applications"
    assert module.resolve_subject_id(index, "CBSE", 10, "Not a subject") is None


def test_enrollment_audit_counts_only_missing_enrollments(tmp_path):
    from sqlalchemy import create_engine, text
    import importlib.util

    migration_path = ROOT / "question_bank" / "migrations" / "005_curriculum_question_reuse_audit.py"
    spec = importlib.util.spec_from_file_location("curriculum_migration_audit", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine(f"sqlite:///{tmp_path / 'enrollment-audit.sqlite'}")
    with engine.begin() as db:
        db.execute(text("""
            CREATE TABLE students (
                student_id TEXT PRIMARY KEY, board TEXT, class_level INTEGER,
                subject TEXT, status TEXT
            )
        """))
        db.execute(text("""
            CREATE TABLE student_subject_enrollments (
                enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT,
                board TEXT, class_level INTEGER, subject_id TEXT, academic_year TEXT,
                status TEXT
            )
        """))
        db.execute(text("""
            INSERT INTO students(student_id,board,class_level,subject,status) VALUES
            ('S1','CBSE',10,'Mathematics','active'),
            ('S2','CBSE',10,'Mathematics','active'),
            ('S3','CBSE',12,'Applied Mathematics','active'),
            ('S4','CBSE',10,'Mathematics','inactive')
        """))
        db.execute(text("""
            INSERT INTO student_subject_enrollments(student_id,board,class_level,subject_id,academic_year,status)
            VALUES ('S1','CBSE',10,'mathematics','2026-27','ACTIVE')
        """))
        count = module.expected_enrollment_inserts(
            db,
            eligible_rows=3,
            tables={"students", "student_subject_enrollments"},
            missing_columns={},
        )
    assert count == 2
    engine.dispose()


def test_migration_question_mapping_is_scoped_by_board_class_and_subject():
    migration_path = ROOT / "question_bank" / "migrations" / "005_curriculum_question_reuse.py"
    source = migration_path.read_text(encoding="utf-8")
    assert "sc.subject_id=cur.subject_id AND sc.subject_name=q.subject" in source
    assert "COUNT(DISTINCT cur2.subject_id)" in source
    assert "cur2.board=q.board AND cur2.class_level=q.class_level" in source
