"""Media storage helpers for local development and temporary cloud deployment."""

import os
from pathlib import Path
from urllib.parse import urlparse

CLOUDINARY_ENABLED = bool(os.getenv("CLOUDINARY_URL"))

if CLOUDINARY_ENABLED:
    import cloudinary
    import cloudinary.uploader
    from cloudinary import CloudinaryImage

    cloudinary.config(secure=True)


def store_image(file_obj, filename):
    """Store an uploaded image and return the value persisted in answer_images.file_path."""
    if CLOUDINARY_ENABLED:
        stem = Path(filename).stem
        public_id = f"improvia/answers/{stem}"
        result = cloudinary.uploader.upload(
            file_obj,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
        )
        return f"cloudinary://{result['public_id']}"

    upload_folder = Path(os.getenv("UPLOAD_FOLDER", "uploads"))
    upload_folder.mkdir(parents=True, exist_ok=True)
    destination = upload_folder / Path(filename).name
    file_obj.save(destination)
    return str(destination)


def media_url(file_path):
    """Return a browser-accessible URL for a stored media reference."""
    if str(file_path).startswith("cloudinary://"):
        public_id = str(file_path)[len("cloudinary://") :]
        return CloudinaryImage(public_id).build(secure=True)
    return None


def delete_image(file_path):
    """Delete a stored image when possible."""
    if str(file_path).startswith("cloudinary://"):
        public_id = str(file_path)[len("cloudinary://") :]
        cloudinary.uploader.destroy(public_id, resource_type="image")
        return

    path = Path(file_path)
    if path.exists():
        path.unlink()
