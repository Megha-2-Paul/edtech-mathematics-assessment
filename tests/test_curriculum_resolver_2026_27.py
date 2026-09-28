from exam_platform.ingestion.curriculum import CanonicalTaxonomyResolver, canonical_subject_id

def test_subject_aliases_are_board_aware():
    assert canonical_subject_id("Computer Applications","CBSE") == "cbse_computer_applications"
    assert canonical_subject_id("Computer Applications","ICSE") == "icse_computer_applications"
    assert canonical_subject_id("Computer Science","CBSE") == "cbse_computer_science"
    assert canonical_subject_id("Computer Science","ISC") == "isc_computer_science"

def test_resolver_uses_exact_official_names():
    r=CanonicalTaxonomyResolver()
    cbse=r.resolve(subject="Mathematics",board="CBSE",class_level=11,chapter="Conic Sections")
    isc=r.resolve(subject="Mathematics",board="ISC",class_level=11,chapter="Conic Section")
    assert cbse.status=="MATCHED"
    assert isc.status=="MATCHED"
    assert cbse.official_chapter_name=="Conic Sections"
    assert isc.official_chapter_name=="Conic Section"

def test_resolver_does_not_accept_wrong_board_wording():
    r=CanonicalTaxonomyResolver()
    result=r.resolve(subject="Mathematics",board="ISC",class_level=11,chapter="Conic Sections")
    assert result.status=="UNRESOLVED"
