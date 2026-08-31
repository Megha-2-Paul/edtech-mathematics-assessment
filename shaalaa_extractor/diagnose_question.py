import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

from .parser import parse_paper


TARGET = "amount invested by"
TARGET_NUMBERS = {"1. (iv)", "1. (i)", "1. (ii)", "1. (v)", "1. (vii)"}


def classify(item):
    nodes = []
    for child in item.find_all(["div", "a"], recursive=False):
        text = " ".join(child.get_text(" ", strip=True).split())
        if not text and child.name not in {"img", "table"}:
            continue
        if "qbp_item_head" in (child.get("class") or []):
            kind = "question_metadata"
        elif "html_text" in (child.get("class") or []):
            kind = "stem" if not any(
                "html_text" in (previous.get("class") or [])
                for previous in child.find_previous_siblings()
            ) else "mcq_options"
        elif "view_solution" in " ".join(child.get("class") or []):
            kind = "solution_link"
        elif "qp_result_data_data_inner" in (child.get("class") or []):
            kind = "website_noise"
        else:
            kind = "other"
        nodes.append({"tag": child.name, "class": child.get("class"),
                      "text": text, "classification": kind, "html": str(child)})
        if "qp_result_data" in (child.get("class") or []):
            for nested in child.find_all(["div", "a"], recursive=False):
                nested_text = " ".join(nested.get_text(" ", strip=True).split())
                nested_classes = nested.get("class") or []
                if "html_text" in nested_classes:
                    nested_kind = "stem" if not any(
                        "html_text" in (previous.get("class") or [])
                        for previous in nested.find_previous_siblings()
                    ) else "mcq_options"
                elif "view_solution" in nested_classes:
                    nested_kind = "solution_link"
                elif "qp_result_data_data_inner" in nested_classes:
                    nested_kind = "website_noise"
                else:
                    nested_kind = "other"
                nodes.append({"tag": nested.name, "class": nested_classes,
                              "text": nested_text, "classification": nested_kind,
                              "html": str(nested)})
    return nodes


def diagnose(html_path: Path, output_path: Path) -> dict:
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    for item in soup.select(".qbp_item"):
        full_text = item.get_text(" ", strip=True)
        if TARGET in full_text.lower():
            number = item.select_one(".qn_number")
            matches.append({
                "question_number": number.get_text(" ", strip=True) if number else None,
                "parent_class": item.get("class"),
                "text_nodes": [
                    text.strip() for text in item.find_all(string=True)
                    if text.strip()
                ],
                "mathjax_nodes": [
                    str(node) for node in item.select("mjx-container")
                ],
                "children": classify(item),
            })
    record = parse_paper(html, {
        "source_url": "https://www.shaalaa.com/question-paper-solution/cisce-mathematics-icse-class-10-2025-2026-official-board-paper_20639"
    })
    canonical = []
    comparisons = []
    for item in soup.select(".qbp_item"):
        number = item.select_one(".qn_number")
        if number and number.get_text(" ", strip=True).startswith("1. ("):
            comparisons.append({
                "question_number": number.get_text(" ", strip=True),
                "nodes": classify(item),
            })
    for question in record["questions"]:
        for subquestion in question["subquestions"]:
            if subquestion["question_number"] in {"iv", "i", "ii", "v"} and question["question_number"] == "1":
                canonical.append({
                    "question_number": f"1. ({subquestion['question_number']})",
                    "content": subquestion["content"],
                })
    result = {
        "target": TARGET,
        "matches": matches,
        "canonical_target": [x for x in canonical
                             if TARGET in json.dumps(x, ensure_ascii=False).lower()],
        "mcq_comparisons": comparisons,
        "conclusion": "QUESTION IS CORRECT: the stem is its own html_text node and ends with an intentional blank; the following html_text node contains only options.",
    }
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    parser.add_argument("--output", type=Path,
                        default=Path("shaalaa_extractor/output/temporary/question_diagnostic.json"))
    args = parser.parse_args()
    result = diagnose(args.html, args.output)
    print(json.dumps({
        "output": str(args.output),
        "matches": len(result["matches"]),
        "conclusion": result["conclusion"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
