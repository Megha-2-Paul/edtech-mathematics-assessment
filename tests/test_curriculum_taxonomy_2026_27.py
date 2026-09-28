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
