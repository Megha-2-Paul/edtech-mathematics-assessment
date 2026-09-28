"""Conservative 2026-27 curriculum resolver.

Official syllabus chapters are the curriculum layer. Canonical concepts are the
cross-board analytics/reuse layer. A question is never considered reusable
across curricula merely because a concept name looks similar; it must have an
explicit question_curriculum_map entry with an approved compatibility status.
"""
from __future__ import annotations
import json, re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

SUBJECT_ALIASES = {
    "mathematics":"mathematics","maths":"mathematics",
    "applied mathematics":"applied_mathematics","applied maths":"applied_mathematics",
    "information technology":"cbse_information_technology",
    "information technology (402)":"cbse_information_technology",
    "computer applications":"computer_applications",
    "computer applications (165)":"cbse_computer_applications",
    "computer applications (86)":"icse_computer_applications",
    "computer science":"computer_science",
    "computer science (083)":"cbse_computer_science",
    "computer science (868)":"isc_computer_science",
    "informatics practices":"cbse_informatics_practices",
    "informatics practices (065)":"cbse_informatics_practices",
}
BOARD_ALIASES={"cbse":"CBSE","icse":"ICSE","isc":"ISC"}

def normalize_label(value: Any)->str:
    return re.sub(r"\s+"," ",str(value or "").strip()).casefold()

def canonical_subject_id(value: Any, board: Any=None, subject_code: Any=None)->str|None:
    label=normalize_label(value); board_name=BOARD_ALIASES.get(normalize_label(board))
    if label=="computer applications":
        if board_name=="CBSE": return "cbse_computer_applications"
        if board_name=="ICSE": return "icse_computer_applications"
    if label=="computer science":
        if board_name=="CBSE": return "cbse_computer_science"
        if board_name=="ISC": return "isc_computer_science"
    return SUBJECT_ALIASES.get(label)

def canonical_board(value: Any)->str|None:
    return BOARD_ALIASES.get(normalize_label(value))

@dataclass(frozen=True)
class CurriculumMapping:
    status:str
    original_chapter:str|None=None
    canonical_chapter_id:str|None=None
    canonical_chapter_name:str|None=None
    canonical_concept_id:str|None=None
    syllabus_unit_id:str|None=None
    syllabus_unit_name:str|None=None
    official_chapter_id:str|None=None
    official_chapter_name:str|None=None
    board:str|None=None
    class_level:int|None=None
    subject_id:str|None=None
    candidates:tuple[dict[str,Any],...]=field(default_factory=tuple)
    reason:str|None=None

class CanonicalTaxonomyResolver:
    MATCHED="MATCHED"; UNRESOLVED="UNRESOLVED"; AMBIGUOUS="AMBIGUOUS"
    def __init__(self,taxonomy_path: str|Path|None=None,*,taxonomy_data:Mapping[str,Any]|None=None):
        if taxonomy_data is not None:
            self.data=dict(taxonomy_data)
        else:
            root=Path(__file__).resolve().parents[2]
            path=Path(taxonomy_path) if taxonomy_path else root/"curriculum_taxonomy_2026_27.json"
            if not path.exists():
                path=root/"canonical_math_taxonomy_2026_27.json"
            self.data=json.loads(path.read_text(encoding="utf-8"))
        self._new=bool(self.data.get("curricula"))
        self._chapters={x["id"]:x for x in self.data.get("canonical_chapters",[]) if isinstance(x,dict) and x.get("id")}
        self._units={x["unit_id"]:x for x in self.data.get("units",[]) if isinstance(x,dict) and x.get("unit_id")}
        self._mappings=[x for x in self.data.get("mappings",[]) if isinstance(x,dict)]
        self._curricula=self.data.get("curricula",[])

    def resolve(self,*,subject:Any,board:Any,class_level:Any,chapter:Any)->CurriculumMapping:
        original=str(chapter).strip() if chapter is not None else None
        board_name=canonical_board(board)
        try: class_number=int(class_level) if class_level is not None else None
        except (TypeError,ValueError): class_number=None
        subject_id=canonical_subject_id(subject,board)
        if not original:
            return CurriculumMapping(self.UNRESOLVED,original,board=board_name,class_level=class_number,subject_id=subject_id,reason="missing_chapter")
        if not subject_id:
            return CurriculumMapping(self.UNRESOLVED,original,board=board_name,class_level=class_number,reason="unsupported_subject")
        if not board_name or class_number is None:
            return CurriculumMapping(self.UNRESOLVED,original,board=board_name,class_level=class_number,subject_id=subject_id,reason="missing_board_or_class")
        label=normalize_label(original); candidates=[]
        if self._new:
            for cur in self._curricula:
                if cur.get("board")!=board_name or cur.get("class_level")!=class_number or cur.get("subject_id")!=subject_id: continue
                for ui,u in enumerate(cur.get("units",[]),1):
                    uid=f"{cur.get('curriculum_id')}__u{ui}"
                    for ci,ch in enumerate(u.get("chapters",[]),1):
                        if normalize_label(ch.get("official_chapter_name"))==label:
                            candidates.append({"official_chapter_id":f"{uid}__c{ci}","official_chapter_name":ch.get("official_chapter_name"),"canonical_concept_id":ch.get("canonical_concept_id") or normalize_label(ch.get("official_chapter_name")).replace(" ","_"),"syllabus_unit_id":uid,"syllabus_unit_name":u.get("unit_name"),"chapter_order":ci,"mapping_status":"VERIFIED"})
        else:
            for mapping in self._mappings:
                if normalize_label(mapping.get("board"))!=normalize_label(board_name) or mapping.get("class_level")!=class_number: continue
                unit=self._units.get(mapping.get("unit_id"),{})
                if unit.get("subject_id")!=subject_id: continue
                ch=self._chapters.get(mapping.get("canonical_chapter_id"),{})
                if normalize_label(ch.get("name"))==label:
                    candidates.append({"canonical_chapter_id":ch.get("id"),"canonical_chapter_name":ch.get("name"),"syllabus_unit_id":unit.get("unit_id"),"syllabus_unit_name":unit.get("unit_name"),"chapter_order":mapping.get("chapter_order"),"mapping_status":mapping.get("status")})
        if len(candidates)==1:
            m=candidates[0]
            if m.get("mapping_status")!="VERIFIED":
                return CurriculumMapping(self.UNRESOLVED,original,board=board_name,class_level=class_number,subject_id=subject_id,candidates=(m,),reason="taxonomy_mapping_not_verified")
            return CurriculumMapping(self.MATCHED,original,m.get("official_chapter_id") or m.get("canonical_chapter_id"),m.get("official_chapter_name") or m.get("canonical_chapter_name"),m.get("canonical_concept_id"),m.get("syllabus_unit_id"),m.get("syllabus_unit_name"),m.get("official_chapter_id"),m.get("official_chapter_name"),board_name,class_number,subject_id,(m,),"")
        if not candidates:
            return CurriculumMapping(self.UNRESOLVED,original,board=board_name,class_level=class_number,subject_id=subject_id,reason="no_exact_official_chapter")
        return CurriculumMapping(self.AMBIGUOUS,original,board=board_name,class_level=class_number,subject_id=subject_id,candidates=tuple(candidates),reason="multiple_exact_official_chapters")
