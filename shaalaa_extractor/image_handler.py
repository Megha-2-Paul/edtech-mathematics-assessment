from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin
import hashlib
import requests


def retrieve_images(image_urls: List[str], output_dir: Path, paper_url: str,
                    question_number: str) -> List[Dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for index, source in enumerate(image_urls, 1):
        absolute = urljoin(paper_url, source)
        response = requests.get(absolute, timeout=20)
        response.raise_for_status()
        suffix = ".png" if "png" in response.headers.get("content-type", "") else ".jpg"
        digest = hashlib.sha256(response.content).hexdigest()[:12]
        path = output_dir / f"question_{question_number}_image_{index}_{digest}{suffix}"
        path.write_bytes(response.content)
        assets.append({"asset_id": path.stem, "source_url": absolute,
                       "local_asset_path": str(path), "bytes": len(response.content),
                       "width": None, "height": None})
    return assets
