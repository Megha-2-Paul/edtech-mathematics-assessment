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
    """Store answer images in authenticated cloud storage or a private local folder."""
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

    upload_folder = Path(upload_folder or os.getenv("UPLOAD_FOLDER", Path(__file__).resolve().parent.parent / "uploads")).resolve()
    upload_folder.mkdir(parents=True, exist_ok=True)
    destination = upload_folder / Path(filename).name
    file_obj.save(destination)
    return str(destination)


def media_url(file_path):
    """Do not expose direct media-provider URLs; use an access-checked proxy route."""
    return None


def _resolve_local_path(file_path, upload_folder=None):
    """Reject local media references outside the configured private upload root."""
    root = Path(
        upload_folder
        or os.getenv("UPLOAD_FOLDER", Path(__file__).resolve().parent.parent / "uploads")
    ).resolve()
    path = Path(file_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PermissionError("Stored image path is outside the private upload directory.") from exc
    return path


def read_stored_image(file_path, upload_folder=None):
    """Read answer image bytes only from the configured root or authenticated cloud delivery.

    Legacy Cloudinary assets that are accessible only through public delivery are
    deliberately not used as a fallback. They must be migrated to authenticated
    delivery before they can be served through this private proxy.
    """
    value = str(file_path or "")
    if value.startswith("cloudinary://"):
        public_id = value[len("cloudinary://") :]
        try:
            url, _ = cloudinary_url(
                public_id,
                resource_type="image",
                type="authenticated",
                secure=True,
                sign_url=True,
            )
            with urlopen(url, timeout=15) as response:
                data = response.read()
                content_type = response.headers.get_content_type()
            if not data:
                raise RuntimeError("Stored image is empty.")
            return data, content_type
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                "Unable to retrieve the image through authenticated Cloudinary delivery."
            ) from exc

    path = _resolve_local_path(value, upload_folder=upload_folder)
    data = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return data, content_type


def delete_image(file_path, upload_folder=None):
    """Delete stored answer images from cloud or within the configured local root."""
    if str(file_path).startswith("cloudinary://"):
        public_id = str(file_path)[len("cloudinary://") :]
        result = cloudinary.uploader.destroy(
            public_id, resource_type="image", type="authenticated"
        )
        if result.get("result") == "not found":
            cloudinary.uploader.destroy(public_id, resource_type="image", type="upload")
        return

    path = _resolve_local_path(file_path, upload_folder=upload_folder)
    if path.exists():
        path.unlink()
