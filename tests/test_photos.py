from pathlib import Path

from mediahub.photos import scan_photos


def test_scan_photos_finds_images_only(tmp_path):
    photos = tmp_path / "photos"
    photos.mkdir()
    (photos / "a.jpg").write_bytes(b"jpg")
    (photos / "b.PNG").write_bytes(b"png")
    (photos / "c.webp").write_bytes(b"webp")
    (photos / "movie.mp4").write_bytes(b"video")
    (photos / "clip.mkv").write_bytes(b"video")
    (photos / ".hidden.jpg").write_bytes(b"jpg")

    found, warnings = scan_photos([str(photos)])
    assert warnings == []
    assert [Path(path).name for path in found] == ["a.jpg", "b.PNG", "c.webp"]


def test_scan_photos_recurses_and_dedupes(tmp_path):
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (nested / "photo.jpeg").write_bytes(b"jpg")

    found, warnings = scan_photos([str(root), str(root)])
    assert warnings == []
    assert len(found) == 1


def test_scan_photos_warns_missing_folder(tmp_path):
    found, warnings = scan_photos([str(tmp_path / "missing")])
    assert found == []
    assert warnings and "fotomapp finns inte" in warnings[0]


def test_scan_photos_without_folders():
    found, warnings = scan_photos([])
    assert found == []
    assert warnings == []
