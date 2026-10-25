"""Media storage helpers for local development and cloud deployment."""

import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

CLOUDINARY_ENABLED = bool(os.getenv("CLOUDINARY_URL"))

if CLOUDINARY_ENABLED:
    import cloudinary
    import cloudinary.uploader
    from cloudinary.utils import cloudinary_url

    cloudinary.config(secure=True)


def store_image(file_obj, filename, upload_folder=None):
    """Store an uploaded image and return the reference persisted in answer_images.file_path.

    Cloud deployments use authenticated Cloudinary delivery. Local development uses
    the configured upload folder, which should be persistent if used beyond testing.
    """
    if CLOUDINARY_ENABLED:
        stem = Path(filename).stem
        public_id = f"improvia/answers/{stem}"
        result = cloudinary.uploader.upload(
            file_obj,
            public_id=public_id,
            resource_type="image",
            type="authenticated",
            overwrite=False,
        )
        return f"cloudinary://{result['public_id']}"

    upload_folder = Path(upload_folder or os.getenv("UPLOAD_FOLDER", "uploads"))
    upload_folder.mkdir(parents=True, exist_ok=True)
    destination = upload_folder / Path(filename).name
    file_obj.save(destination)
    return str(destination)


def media_url(file_path):
    """Never expose direct Cloudinary URLs; use an access-checked proxy route."""
    return None


def read_stored_image(file_path):
    """Read image bytes for an authenticated proxy route.

    New Cloudinary answer images use authenticated delivery. The upload-type
    fallback supports files created before this protection was enabled; those
    URLs are fetched server-side and are never returned to the browser.
    """
    value = str(file_path or "")
    if value.startswith("cloudinary://"):
        public_id = value[len("cloudinary://") :]
        last_error = None
        for delivery_type in ("authenticated", "upload"):
            try:
                url, _ = cloudinary_url(
                    public_id,
                    resource_type="image",
                    type=delivery_type,
                    secure=True,
                    sign_url=(delivery_type == "authenticated"),
                )
                with urlopen(url, timeout=15) as response:
                    data = response.read()
                    content_type = response.headers.get_content_type()
                if not data:
                    raise RuntimeError("Stored image is empty.")
                return data, content_type
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                last_error = exc
        raise RuntimeError("Unable to retrieve the stored Cloudinary image.") from last_error

    path = Path(value)
    data = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return data, content_type


def delete_image(file_path):
    """Delete a stored image, supporting authenticated and legacy Cloudinary assets."""
    if str(file_path).startswith("cloudinary://"):
        public_id = str(file_path)[len("cloudinary://") :]
        result = cloudinary.uploader.destroy(
            public_id, resource_type="image", type="authenticated"
        )
        if result.get("result") == "not found":
            cloudinary.uploader.destroy(public_id, resource_type="image", type="upload")
        return

    path = Path(file_path)
    if path.exists():
        path.unlink()
