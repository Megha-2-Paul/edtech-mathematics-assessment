import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from .parser import parse_paper
from .validator import validate


DEFAULT_URL = "https://www.shaalaa.com/question-paper-solution/cisce-mathematics-icse-class-10-2025-2026-official-board-paper_20639"


def configure_utf8_output() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="strict")


def collect(url: str, output: Path) -> dict:
    with sync_playwright() as playwright:
        executable = os.getenv("SHAALAA_BROWSER_EXECUTABLE")
        if not executable:
            executable = shutil.which("chrome") or shutil.which("msedge")
        browser_options = {"headless": True}
        if executable:
            browser_options["executable_path"] = executable
        browser = playwright.chromium.launch(**browser_options)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector("body", timeout=30_000)
        if "Just a moment" in page.title() or "checking your browser" in page.locator("body").inner_text().lower():
            raise RuntimeError("Shaalaa returned an access challenge; no access-control bypass is attempted")
        html = page.content()
        title = page.title()
        browser.close()
    metadata = {
        "source_url": url, "source_title": title, "board": "CISCE",
        "class_level": 10, "subject": "Mathematics",
        "academic_year": "2025-2026", "extraction_method": "Playwright DOM",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
    record = parse_paper(html, metadata)
    record["validation"] = validate(record)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    output.with_name("validation.json").write_text(
        json.dumps(record["validation"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return record


def main() -> None:
    configure_utf8_output()
    parser = argparse.ArgumentParser(description="Shaalaa extraction prototype")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=Path("shaalaa_extractor/output/temporary/paper.json"))
    args = parser.parse_args()
    record = collect(args.url, args.output)
    print(json.dumps({"output": str(args.output), "questions": len(record["questions"]),
                      "validation": record["validation"]}, indent=2))


if __name__ == "__main__":
    main()
