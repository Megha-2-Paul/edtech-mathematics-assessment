#!/usr/bin/env python
"""Install the 2026-27 curriculum/question-reuse model.

Usage:
  python question_bank/migrations/005_curriculum_question_reuse.py --database-url <URL> --taxonomy curriculum_taxonomy_2026_27.json --apply
"""
from __future__ import annotations
import argparse, json, os, re
from pathlib import Path
from sqlalchemy import create_engine, text

VERSION="2026.27.7"
ALIASES={
"Statistics":"statistics","Probability":"probability","Trigonometry":"trigonometry",
"Introduction to Trigonometry":"trigonometry","Trigonometric Functions":"trigonometry",
"Coordinate Geometry":"coordinate_geometry","Co-ordinate Geometry":"coordinate_geometry",
"Circles":"circles","Circle":"circles","Triangles":"triangles",
"Triangles – Congruence Theorems":"triangles","Similarity":"triangle_similarity",
"Constructions":"constructions","Matrices":"matrices","Determinants":"determinants",
"Sets":"sets","Relations & Functions":"relations_functions","Relations and Functions":"relations_functions",
"Inverse Trigonometric Functions":"inverse_trigonometric_functions",
"Linear Programming":"linear_programming","Vectors":"vectors","Vector Algebra":"vectors",
"Three-dimensional Geometry":"three_d_geometry","Three-Dimensional Geometry":"three_d_geometry",
"Introduction to Three-dimensional Geometry":"three_d_geometry","Introduction to Three Dimensional Geometry":"three_d_geometry",
"Integrals":"integrals","Applications of Integrals":"integrals","Application of the Integrals":"integrals",
"Differential Equations":"differential_equations","Continuity and Differentiability":"continuity_differentiability",
"Applications of Derivatives":"applications_derivatives","Limits and Derivatives":"limits_derivatives",
"Straight Lines":"straight_lines","Conic Sections":"conics","Conic Section":"conics",
"Complex Numbers":"complex_numbers","Complex Numbers and Quadratic Equations":"complex_quadratic",
"Permutations and Combinations":"permutations_combinations","Binomial Theorem":"binomial_theorem",
"Sequence and Series":"sequence_series","Sequences and Progressions":"sequences_progressions",
"Arithmetic Progressions":"arithmetic_progressions","Linear Inequations":"linear_inequalities",
"Quadratic Equations":"quadratic_equations","Quadratic Equations in one variable":"quadratic_equations",
"Pair of Linear Equations in Two Variables":"linear_equations_two_variables",
"Simultaneous Linear Equations in two variables":"linear_equations_two_variables",
"Factorisation of polynomials":"factorisation_polynomials","Factorisation of Polynomials":"factorisation_polynomials",
"Ratio and Proportion":"ratio_proportion","Arithmetic and Geometric Progression":"arithmetic_geometric_progression",
"Mensuration":"mensuration","Surface Areas and Volumes":"surface_area_volume",
"Areas Related to Circles":"areas_related_circles",
"Introduction to Probability":"probability","Area and Perimeter":"area_perimeter",
"Data Structures":"data_structures","Arrays":"arrays","String Handling":"string_handling",
"Arrays, Strings":"arrays_strings","Recursion":"recursion","Computer Networks":"computer_networks",
"Database Management":"database_management","Networking":"networking","HTML":"html",
"Cyber ethics":"cyber_ethics","Programming in Python":"python_programming",
"Introduction to Python":"python_programming","Database Query using SQL":"sql_database",
"Database concepts and the Structured Query Language":"sql_database",
}
def slug(name):
    s=ALIASES.get(name)
    if s: return s
    s=re.sub(r"[^a-z0-9]+","_",name.lower()).strip("_")
    return s[:100] or "unclassified"
def load(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("taxonomy_version")!=VERSION: raise ValueError("Unexpected taxonomy version")
    return data
def apply(url,taxonomy):
    data=load(taxonomy); eng=create_engine(url)
    with eng.begin() as db:
        db.execute(text("""CREATE TABLE IF NOT EXISTS subject_catalog (
          subject_id VARCHAR(80) PRIMARY KEY, subject_name VARCHAR(150) NOT NULL,
          subject_code VARCHAR(30), active BOOLEAN NOT NULL DEFAULT TRUE,
          UNIQUE KEY uq_subject_catalog_name_code(subject_name,subject_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""))
        db.execute(text("""CREATE TABLE IF NOT EXISTS curriculum_catalog (
          curriculum_id VARCHAR(120) PRIMARY KEY, board VARCHAR(20) NOT NULL,
          class_level INT NOT NULL, subject_id VARCHAR(80) NOT NULL,
          subject_code VARCHAR(30), academic_year VARCHAR(20) NOT NULL,
          status VARCHAR(30) NOT NULL DEFAULT 'VERIFIED',
          FOREIGN KEY(subject_id) REFERENCES subject_catalog(subject_id),
          UNIQUE KEY uq_curriculum(board,class_level,subject_id,academic_year)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""))
        db.execute(text("""CREATE TABLE IF NOT EXISTS curriculum_units (
          unit_id VARCHAR(150) PRIMARY KEY, curriculum_id VARCHAR(120) NOT NULL,
          unit_order INT NOT NULL, unit_name VARCHAR(255) NOT NULL,
          FOREIGN KEY(curriculum_id) REFERENCES curriculum_catalog(curriculum_id) ON DELETE CASCADE,
          UNIQUE KEY uq_curriculum_unit(curriculum_id,unit_order)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""))
        db.execute(text("""CREATE TABLE IF NOT EXISTS canonical_concepts (
          concept_id VARCHAR(100) PRIMARY KEY, concept_name VARCHAR(200) NOT NULL,
          subject_id VARCHAR(80), active BOOLEAN NOT NULL DEFAULT TRUE,
          FOREIGN KEY(subject_id) REFERENCES subject_catalog(subject_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""))
        db.execute(text("""CREATE TABLE IF NOT EXISTS curriculum_chapters (
          curriculum_chapter_id VARCHAR(180) PRIMARY KEY, unit_id VARCHAR(150) NOT NULL,
          chapter_order INT NOT NULL, official_chapter_name VARCHAR(255) NOT NULL,
          canonical_concept_id VARCHAR(100) NOT NULL, status VARCHAR(30) NOT NULL DEFAULT 'VERIFIED',
          FOREIGN KEY(unit_id) REFERENCES curriculum_units(unit_id) ON DELETE CASCADE,
          FOREIGN KEY(canonical_concept_id) REFERENCES canonical_concepts(concept_id),
          UNIQUE KEY uq_curriculum_chapter(unit_id,chapter_order),
          INDEX idx_curriculum_chapter_lookup(official_chapter_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""))
        db.execute(text("""CREATE TABLE IF NOT EXISTS question_curriculum_map (
          question_id VARCHAR(40) NOT NULL, curriculum_chapter_id VARCHAR(180) NOT NULL,
          compatibility_status VARCHAR(30) NOT NULL DEFAULT 'REVIEW_REQUIRED',
          notes TEXT, reviewed_by VARCHAR(100), reviewed_at DATETIME NULL,
          PRIMARY KEY(question_id,curriculum_chapter_id),
          FOREIGN KEY(question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
          FOREIGN KEY(curriculum_chapter_id) REFERENCES curriculum_chapters(curriculum_chapter_id) ON DELETE CASCADE,
          INDEX idx_qcm_status(compatibility_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""))
        db.execute(text("""CREATE TABLE IF NOT EXISTS student_subject_enrollments (
          enrollment_id BIGINT AUTO_INCREMENT PRIMARY KEY, student_id VARCHAR(32) NOT NULL,
          board VARCHAR(20) NOT NULL, class_level INT NOT NULL, subject_id VARCHAR(80) NOT NULL,
          subject_code VARCHAR(30), academic_year VARCHAR(20) NOT NULL,
          status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
          FOREIGN KEY(subject_id) REFERENCES subject_catalog(subject_id),
          UNIQUE KEY uq_student_enrollment(student_id,board,class_level,subject_id,academic_year),
          INDEX idx_active_enrollment(student_id,status,board,class_level,subject_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""))
        for s in data["subjects"]:
            db.execute(text("""INSERT INTO subject_catalog(subject_id,subject_name,subject_code,active)
              VALUES(:id,:name,:code,1)
              ON DUPLICATE KEY UPDATE subject_name=VALUES(subject_name),subject_code=VALUES(subject_code),active=1"""),
              {"id":s["subject_id"],"name":s["name"],"code":s["subject_code"]})
        concept_subject={}
        for c in data["curricula"]:
            subject_id=c["subject_id"]
            for u in c["units"]:
                for ch in u["chapters"]:
                    cid=slug(ch["official_chapter_name"])
                    previous=concept_subject.get(cid)
                    if previous is None and cid not in concept_subject:
                        concept_subject[cid]=subject_id
                    elif previous != subject_id:
                        # Same canonical concept is intentionally shared across subjects.
                        concept_subject[cid]=None
        for cid,sid in concept_subject.items():
            db.execute(text("""INSERT INTO canonical_concepts(concept_id,concept_name,subject_id,active)
              VALUES(:id,:name,:subject,1) ON DUPLICATE KEY UPDATE concept_name=VALUES(concept_name),subject_id=VALUES(subject),active=1"""),
              {"id":cid,"name":cid.replace("_"," ").title(),"subject":sid})
        for c in data["curricula"]:
            db.execute(text("""INSERT INTO curriculum_catalog(curriculum_id,board,class_level,subject_id,subject_code,academic_year,status)
              VALUES(:id,:board,:class,:subject,:code,:year,'VERIFIED')
              ON DUPLICATE KEY UPDATE subject_code=VALUES(subject_code),status='VERIFIED'"""),
              {"id":c["curriculum_id"],"board":c["board"],"class":c["class_level"],"subject":c["subject_id"],"code":c["subject_code"],"year":c["academic_year"]})
            for ui,u in enumerate(c["units"],1):
                uid=f"{c['curriculum_id']}__u{ui}"
                db.execute(text("""INSERT INTO curriculum_units(unit_id,curriculum_id,unit_order,unit_name)
                  VALUES(:id,:curr,:order,:name)
                  ON DUPLICATE KEY UPDATE unit_name=VALUES(unit_name),unit_order=VALUES(unit_order)"""),
                  {"id":uid,"curr":c["curriculum_id"],"order":ui,"name":u["unit_name"]})
                for ci,ch in enumerate(u["chapters"],1):
                    ccid=slug(ch["official_chapter_name"]); chid=f"{uid}__c{ci}"
                    db.execute(text("""INSERT INTO curriculum_chapters(curriculum_chapter_id,unit_id,chapter_order,official_chapter_name,canonical_concept_id,status)
                      VALUES(:id,:unit,:order,:name,:concept,'VERIFIED')
                      ON DUPLICATE KEY UPDATE official_chapter_name=VALUES(official_chapter_name),canonical_concept_id=VALUES(canonical_concept),status='VERIFIED'"""),
                      {"id":chid,"unit":uid,"order":ci,"name":ch["official_chapter_name"],"concept":ccid})
        # Backfill existing subject registrations into the new enrollment model.
        db.execute(text("""INSERT IGNORE INTO student_subject_enrollments(student_id,board,class_level,subject_id,subject_code,academic_year,status)
          SELECT s.student_id,s.board,s.class_level,
                 CASE WHEN s.subject='Applied Mathematics' THEN 'applied_mathematics' ELSE 'mathematics' END,
                 CASE WHEN s.subject='Applied Mathematics' THEN '241' ELSE '041' END,
                 '2026-27','ACTIVE'
          FROM students s
          WHERE s.status='active' AND s.board IS NOT NULL AND s.class_level IS NOT NULL
            AND s.subject IN ('Mathematics','Applied Mathematics')"""))
        # Exact official-name backfill only; unmatched legacy question chapter labels remain for review.
        db.execute(text("""INSERT IGNORE INTO question_curriculum_map(question_id,curriculum_chapter_id,compatibility_status,notes)
          SELECT q.question_id,cc.curriculum_chapter_id,'EXACT','Backfilled from exact official chapter/board/class/subject match.'
          FROM questions q
          JOIN subject_catalog sc ON sc.subject_name=q.subject
          JOIN curriculum_catalog cur ON cur.board=q.board AND cur.class_level=q.class_level AND cur.subject_id=sc.subject_id
          JOIN curriculum_units cu ON cu.curriculum_id=cur.curriculum_id
          JOIN curriculum_chapters cc ON cc.unit_id=cu.unit_id AND cc.official_chapter_name=q.chapter
          WHERE q.board IS NOT NULL AND q.class_level IS NOT NULL AND q.chapter IS NOT NULL"""))
    print("Applied curriculum/question-reuse schema",VERSION)
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--database-url",default=os.getenv("DATABASE_URL")); p.add_argument("--taxonomy",default="curriculum_taxonomy_2026_27.json"); p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    if not a.apply: p.error("Use --apply explicitly.")
    if not a.database_url: p.error("No database URL supplied.")
    apply(a.database_url,a.taxonomy)
