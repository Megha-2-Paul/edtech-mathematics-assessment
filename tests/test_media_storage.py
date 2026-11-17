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


def test_cloudinary_image_uses_authenticated_https_delivery(monkeypatch):
    from exam_platform import media

    captured = {}

    def fake_cloudinary_url(public_id, **kwargs):
        captured["public_id"] = public_id
        captured["kwargs"] = kwargs
        return "https://res.cloudinary.com/example/image/upload/signed-image", {}

    class FakeHeaders:
        def get_content_type(self):
            return "image/png"

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"cloudinary-image-bytes"

    def fake_urlopen(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(media, "CLOUDINARY_ENABLED", True)
    monkeypatch.setattr(
        media, "cloudinary_url", fake_cloudinary_url, raising=False
    )
    monkeypatch.setattr(media, "urlopen", fake_urlopen)

    data, content_type = media.read_stored_image(
        "cloudinary://improvia/answers/answer-001"
    )

    assert data == b"cloudinary-image-bytes"
    assert content_type == "image/png"
    assert captured["public_id"] == "improvia/answers/answer-001"
    assert captured["url"].startswith("https://")
    assert captured["timeout"] == 15
    assert captured["kwargs"] == {
        "resource_type": "image",
        "type": "authenticated",
        "secure": True,
        "sign_url": True,
    }


def test_cloudinary_read_fails_when_provider_is_disabled(monkeypatch):
    from exam_platform import media

    monkeypatch.setattr(media, "CLOUDINARY_ENABLED", False)
    with pytest.raises(RuntimeError, match="Cloudinary is not configured"):
        media.read_stored_image("cloudinary://improvia/answers/disabled-001")


def test_cloudinary_delete_fails_when_provider_is_disabled(monkeypatch):
    from exam_platform import media

    monkeypatch.setattr(media, "CLOUDINARY_ENABLED", False)
    with pytest.raises(RuntimeError, match="Cloudinary is not configured"):
        media.delete_image("cloudinary://improvia/answers/disabled-002")


def test_cloudinary_image_retrieval_failure_raises_runtime_error(monkeypatch):
    from urllib.error import URLError

    from exam_platform import media

    def fake_cloudinary_url(public_id, **kwargs):
        return "https://res.cloudinary.com/example/signed-image", {}

    def fake_urlopen(url, timeout):
        raise URLError("Simulated network failure")

    monkeypatch.setattr(media, "CLOUDINARY_ENABLED", True)
    monkeypatch.setattr(
        media, "cloudinary_url", fake_cloudinary_url, raising=False
    )
    monkeypatch.setattr(media, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Unable to retrieve"):
        media.read_stored_image("cloudinary://improvia/answers/answer-002")


def test_cloudinary_image_rejects_empty_response(monkeypatch):
    from exam_platform import media

    def fake_cloudinary_url(public_id, **kwargs):
        return "https://res.cloudinary.com/example/signed-image", {}

    class FakeHeaders:
        def get_content_type(self):
            return "image/png"

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b""

    def fake_urlopen(url, timeout):
        return FakeResponse()

    monkeypatch.setattr(media, "CLOUDINARY_ENABLED", True)
    monkeypatch.setattr(
        media, "cloudinary_url", fake_cloudinary_url, raising=False
    )
    monkeypatch.setattr(media, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Stored image is empty"):
        media.read_stored_image("cloudinary://improvia/answers/answer-003")
