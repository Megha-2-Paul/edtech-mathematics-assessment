from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage


def test_local_answer_image_uses_configured_folder_and_can_be_read_and_deleted(
    monkeypatch, tmp_path
):
    from exam_platform import media

    monkeypatch.setattr(media, "CLOUDINARY_ENABLED", False)
    upload = FileStorage(stream=BytesIO(b"test-image-bytes"), filename="answer.png")

    stored_path = media.store_image(upload, "attempt_page_1.png", upload_folder=tmp_path)

    assert str(stored_path).startswith(str(tmp_path))
    assert (tmp_path / "attempt_page_1.png").read_bytes() == b"test-image-bytes"
    data, content_type = media.read_stored_image(stored_path, upload_folder=tmp_path)
    assert data == b"test-image-bytes"
    assert content_type == "image/png"

    media.delete_image(stored_path, upload_folder=tmp_path)
    assert not (tmp_path / "attempt_page_1.png").exists()


def test_local_image_reader_rejects_paths_outside_private_upload_root(tmp_path):
    from exam_platform import media

    outside = tmp_path.parent / "not-private.png"
    outside.write_bytes(b"should not be read")
    with pytest.raises(PermissionError):
        media.read_stored_image(outside, upload_folder=tmp_path)
    with pytest.raises(PermissionError):
        media.delete_image(outside, upload_folder=tmp_path)
