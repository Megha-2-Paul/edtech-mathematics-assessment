import html
from pathlib import Path
import subprocess


def to_html(record: dict) -> str:
    parts = ["<html><head><meta charset='utf-8'><style>",
             "body{font-family:Arial,sans-serif;margin:36px} "
             ".question{margin:12px 0}.marks{float:right} table{border-collapse:collapse} "
             "td,th{border:1px solid #555;padding:5px}", "</style></head><body>"]
    parts.append(f"<h1>{html.escape(record['paper'].get('source_title', 'Question Paper'))}</h1>")
    for question in record["questions"]:
        parts.append(f"<div class='question'><b>{html.escape(question['question_number'])}</b>")
        if question.get("marks") is not None:
            parts.append(f"<span class='marks'>[{question['marks']}]</span>")
        rendered_structured = False
        for block in question.get("content", []):
            if block["type"] == "text":
                structured = block.get("metadata", {}).get("structured_html")
                if structured:
                    parts.append(f"<div class='structured-content'>{structured}</div>")
                    rendered_structured = True
                else:
                    parts.append(f"<p>{html.escape(block['value'])}</p>")
            elif block["type"] == "math":
                if not rendered_structured:
                    parts.append(f"<p><i>{html.escape(str(block['value']))}</i></p>")
            elif block["type"] == "table":
                parts.append("<table>" + "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>" for row in block["value"]) + "</table>")
            elif block["type"] == "image" and block.get("metadata", {}).get("local_asset_path"):
                parts.append(f"<img src='{Path(block['metadata']['local_asset_path']).resolve().as_uri()}' style='max-width:600px;max-height:400px'>")
        for subquestion in question.get("subquestions", []):
            parts.append(f"<div class='question'><b>{html.escape(subquestion['question_number'])}</b>")
            if subquestion.get("marks") is not None:
                parts.append(f"<span class='marks'>[{subquestion['marks']}]</span>")
            rendered_structured = False
            for block in subquestion.get("content", []):
                if block["type"] == "text":
                    structured = block.get("metadata", {}).get("structured_html")
                    if structured:
                        parts.append(f"<div class='structured-content'>{structured}</div>")
                        rendered_structured = True
                    else:
                        parts.append(f"<p>{html.escape(block['value'])}</p>")
                elif block["type"] == "math":
                    if not rendered_structured:
                        parts.append(f"<p><i>{html.escape(str(block['value']))}</i></p>")
                elif block["type"] == "table":
                    parts.append("<table>" + "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>" for row in block["value"]) + "</table>")
                elif block["type"] == "image" and block.get("metadata", {}).get("local_asset_path"):
                    parts.append(f"<img src='{Path(block['metadata']['local_asset_path']).resolve().as_uri()}' style='max-width:600px;max-height:400px'>")
            parts.append("</div>")
        parts.append("</div>")
    return "".join(parts) + "</body></html>"


def generate_pdf(record: dict, output: Path, browser_executable: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    html_path = output.with_suffix(".html")
    html_path.write_text(to_html(record), encoding="utf-8")
    subprocess.run([browser_executable, "--headless", "--disable-gpu",
                    f"--print-to-pdf={output.resolve()}", html_path.resolve().as_uri()],
                   check=True)
