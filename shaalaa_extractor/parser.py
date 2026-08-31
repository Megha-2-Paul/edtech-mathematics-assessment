import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

from .models import ContentBlock, QuestionRecord


QUESTION_RE = re.compile(r"^(?P<number>\d{1,2})(?:[.)])?$")
SUBQUESTION_RE = re.compile(r"^(?:\(?([ivx]+|[a-z])\)?[.)]?)$", re.I)


def _text(node: Tag) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def _visible_math(node: Tag) -> str:
    clone = BeautifulSoup(str(node), "html.parser")
    for hidden in clone.select("mjx-speech, mjx-assistive-mml"):
        hidden.decompose()
    return _text(clone)


def _math_block(node: Tag, source_question_number: Optional[str] = None) -> ContentBlock:
    speech = node.get("data-semantic-speech-none") or node.get("aria-label")
    semantic = node.select_one("[data-semantic-type]")
    return ContentBlock(
        "math",
        value=_visible_math(node) or speech or "",
        metadata={
            "format": "MathJax/semantic-DOM",
            "visible": _visible_math(node),
            "accessibility": speech,
            "semantic_type": semantic.get("data-semantic-type") if semantic else None,
            "semantic_structure": node.get("data-semantic-structure"),
            "source_html": str(node),
            "confidence": "high" if speech or node.get("data-semantic-structure") else "medium",
            "source_question_number": source_question_number,
        },
    )


def _marks(text: str) -> Optional[int]:
    match = re.search(r"\[(\d+)\]\s*$", text)
    return int(match.group(1)) if match else None


def _blocks(container: Tag) -> List[ContentBlock]:
    blocks: List[ContentBlock] = []
    for child in container.find_all(["p", "div", "li", "table", "img"], recursive=False):
        if child.name == "img":
            blocks.append(ContentBlock("image", asset_id=None, metadata={
                "source_url": child.get("src") or child.get("data-src"),
                "alt": child.get("alt", ""),
            }))
        elif child.name == "table":
            rows = [[_text(cell) for cell in row.find_all(["th", "td"])]
                    for row in child.find_all("tr")]
            blocks.append(ContentBlock("table", value=rows))
        else:
            text = _text(child)
            if text and "view solution" not in text.lower():
                blocks.append(ContentBlock("text", value=text))
    return blocks


def find_question_container(soup: BeautifulSoup) -> Tag:
    candidates = soup.find_all(["main", "article", "section", "div"])
    return max(candidates, key=lambda node: len(node.find_all(string=re.compile("SECTION", re.I))),
               default=soup.body or soup)


def parse_questions(html: str) -> List[QuestionRecord]:
    soup = BeautifulSoup(html, "html.parser")
    questions: List[QuestionRecord] = []
    section: Optional[str] = None
    by_number = {}
    for item in soup.select(".qbp_item"):
        head = item.select_one(".qbp_item_head")
        number_node = item.select_one(".qn_number")
        if not head or not number_node:
            continue
        head_text = _text(head)
        section_match = re.search(r"SECTION\s*[- ]\s*([A-Z])", head_text, re.I)
        if section_match:
            section = section_match.group(1).upper()
        number_text = _text(number_node)
        match = re.match(r"^(\d+)\.?\s*(?:\(([ivx]+)\))?", number_text, re.I)
        if not match:
            continue
        number, subnumber = match.group(1), match.group(2)
        target = by_number.get(number)
        if subnumber:
            if target is None:
                target = QuestionRecord(number, section, None)
                by_number[number] = target
                questions.append(target)
            target.subquestions.append(QuestionRecord(
                subnumber.lower(), section, _item_score(item),
                _item_blocks(item, number_text)
            ))
        else:
            target = QuestionRecord(number, section, _item_score(item),
                                    _item_blocks(item, number_text))
            by_number[number] = target
            questions.append(target)
    return questions


def _item_score(item: Tag) -> Optional[int]:
    score = item.select_one(".score")
    return _marks(_text(score)) if score else None


def _item_blocks(item: Tag, source_question_number: Optional[str] = None) -> List[ContentBlock]:
    blocks: List[ContentBlock] = []
    body = item.select_one(".qp_result_data > .html_text") or item.select_one(".qn_text") or item
    original_html = str(item)
    render_fragment = BeautifulSoup(str(body), "html.parser")
    for node in render_fragment.select("img, table"):
        node.decompose()
    for node in render_fragment.select("a, .qp_result_data_data_inner"):
        node.decompose()
    structured_html = render_fragment.decode_contents()

    for math in body.select("mjx-container"):
        blocks.append(_math_block(math, source_question_number))
    for node in body.find_all(["sup", "sub"]):
        if node.find_parent("mjx-container"):
            continue
        blocks.append(ContentBlock(
            "math",
            _text(node),
            metadata={
                "format": "HTML",
                "structure": node.name,
                "visible": _text(node),
                "accessibility": node.get("aria-label"),
                "source_html": str(node),
                "confidence": "high",
                "source_question_number": source_question_number,
            },
        ))
    text = _text(body)
    text = re.split(r"\bVIEW SOLUTION\b", text, maxsplit=1, flags=re.I)[0].strip()
    text = re.sub(r"^\[\d+\]\s*\d+\.\s*(?:\([ivx]+\))?\s*", "", text, flags=re.I)
    text = _remove_mcq_options(text)
    if text:
        blocks.insert(0, ContentBlock("text", text, metadata={
            **_math_metadata(body),
            "source_html": original_html,
            "structured_html": structured_html,
        }))
    for table in item.find_all("table"):
        rows = [[_text(cell) for cell in row.find_all(["th", "td"])]
                for row in table.find_all("tr")]
        blocks.append(ContentBlock("table", value=rows))
    for image in item.find_all("img"):
        source = image.get("src") or image.get("data-src")
        if source and "logo" not in source.lower():
            blocks.append(ContentBlock("image", metadata={
                "source_url": source, "alt": image.get("alt", ""),
                "width": image.get("width"), "height": image.get("height"),
            }))
    return blocks


def _remove_mcq_options(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    assertion_options = re.compile(
        r"^(?:both\s+)?(?:\(a\)|\(b\)|\(c\)|\(d\)|a\)|b\)|c\)|d\))\s+"
        r"(?:is true|is false|the correct explanation)", re.I)
    lines = [line for line in lines if not assertion_options.match(line)]
    return " ".join(lines)


def _math_metadata(node: Tag) -> dict:
    math_nodes = node.find_all(["mjx-container", "math", "sup", "sub"])
    if not math_nodes:
        return {}
    return {
        "structured_math_count": len(math_nodes),
        "structured_math_formats": sorted({
            "MathJax" if child.name == "mjx-container" else child.name
            for child in math_nodes
        }),
    }


def parse_paper(html: str, metadata: dict) -> dict:
    questions = parse_questions(html)

    def serialize(question: QuestionRecord) -> dict:
        return {
            "question_number": question.question_number,
            "section": question.section,
            "marks": question.marks,
            "content": [
                {"type": block.type, "value": block.value,
                 "asset_id": block.asset_id, "metadata": block.metadata}
                for block in question.content
            ],
            "subquestions": [serialize(subquestion)
                             for subquestion in question.subquestions],
            "source_container": question.source_container,
        }

    return {
        "paper": metadata,
        "questions": [serialize(question) for question in questions],
    }
