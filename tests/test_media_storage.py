from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage


def test_local_answer_image_uses_configured_folder_and_can_be_read_and_deleted(
    monkeypatch, tmp_path
):
    from exam_platform import media

    monkeypatch.setattr(media, "CLOUDINARY_ENABLED", False)
    upload = FileStorage(stream=BytesIO(b"test-image-bytes"), filename="answer.png")

    stored_path = media.store_image(
        upload,
        "attempt_page_1.png",
        upload_folder=tmp_path,
    )

    assert str(stored_path).startswith(str(tmp_path))
    assert (tmp_path / "attempt_page_1.png").read_bytes() == b"test-image-bytes"

    data, content_type = media.read_stored_image(
        stored_path, upload_folder=tmp_path
    )
    assert data == b"test-image-bytes"
    assert content_type == "image/png"

    media.delete_image(stored_path, upload_folder=tmp_path)
    assert not (tmp_path / "attempt_page_1.png").exists()


def test_read_rejects_file_outside_upload_folder(tmp_path):
    from exam_platform import media

    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"outside-image")

    with pytest.raises(ValueError, match="outside the configured upload folder"):
        media.read_stored_image(outside_file, upload_folder=upload_folder)


def test_delete_rejects_file_outside_upload_folder(tmp_path):
    from exam_platform import media

    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"outside-image")

    with pytest.raises(ValueError, match="outside the configured upload folder"):
        media.delete_image(outside_file, upload_folder=upload_folder)

    assert outside_file.read_bytes() == b"outside-image"


def test_read_rejects_directory_traversal(tmp_path):
    from exam_platform import media

    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"outside-image")

    traversal_path = upload_folder / ".." / "outside.png"

    with pytest.raises(ValueError, match="outside the configured upload folder"):
        media.read_stored_image(traversal_path, upload_folder=upload_folder)


def test_delete_rejects_directory_traversal(tmp_path):
    from exam_platform import media

    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"outside-image")

    traversal_path = upload_folder / ".." / "outside.png"

    with pytest.raises(ValueError, match="outside the configured upload folder"):
        media.delete_image(traversal_path, upload_folder=upload_folder)

    assert outside_file.read_bytes() == b"outside-image"


def test_read_and_delete_reject_symlink_to_outside_file(tmp_path):
    from exam_platform import media

    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"outside-image")

    symlink_path = upload_folder / "linked.png"

    try:
        symlink_path.symlink_to(outside_file)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlink creation is unavailable: {exc}")

    with pytest.raises(ValueError, match="outside the configured upload folder"):
        media.read_stored_image(symlink_path, upload_folder=upload_folder)

    with pytest.raises(ValueError, match="outside the configured upload folder"):
        media.delete_image(symlink_path, upload_folder=upload_folder)

    assert outside_file.read_bytes() == b"outside-image"
    assert symlink_path.is_symlink()


def test_read_and_delete_reject_upload_folder_itself(tmp_path):
    from exam_platform import media

    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()

    with pytest.raises(ValueError, match="not a valid upload file"):
        media.read_stored_image(upload_folder, upload_folder=upload_folder)

    with pytest.raises(ValueError, match="not a valid upload file"):
        media.delete_image(upload_folder, upload_folder=upload_folder)