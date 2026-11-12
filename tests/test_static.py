"""Module to test the browser caching of static files"""

import json
import os
import re
from pathlib import Path

from flask import url_for

from collectives.utils.static import (
    UNVERSIONED_MAX_AGE,
    VERSIONED_MAX_AGE,
    static_file_version,
)


def test_static_url_version(app):
    """Test that static URLs carry the version of the file."""
    with app.test_request_context():
        version = static_file_version("js/main.js")
        assert re.fullmatch(r"[0-9a-f]{12}", version)
        assert url_for("static", filename="js/main.js") == (
            f"/static/js/main.js?v={version}"
        )

        # Missing files have no version
        assert static_file_version("js/missing.js") is None
        assert url_for("static", filename="js/missing.js") == "/static/js/missing.js"


def test_versioned_static_cache(app, client):
    """Test that only files requested with their current version are kept forever."""
    with app.test_request_context():
        url = url_for("static", filename="js/main.js")

    response = client.get(url)
    assert response.status_code == 200
    assert response.cache_control.public
    assert response.cache_control.immutable
    assert response.cache_control.max_age == VERSIONED_MAX_AGE

    # Partial content, eg a PDF displayed by the browser
    response = client.get(url, headers={"Range": "bytes=0-9"})
    assert response.status_code == 206
    assert response.cache_control.immutable

    # Outdated version, eg from a page rendered before a deployment
    response = client.get("/static/js/main.js?v=000000000000")
    assert response.status_code == 200
    assert response.cache_control.no_cache
    assert response.cache_control.max_age is None

    # Images with an outdated version are kept for a while
    response = client.get("/static/caf/icon/alpinisme.svg?v=000000000000")
    assert response.cache_control.max_age == UNVERSIONED_MAX_AGE

    # Scripts without version are always checked
    response = client.get("/static/js/main.js")
    assert response.cache_control.no_cache

    # Images without version are kept for a while
    response = client.get("/static/caf/icon/alpinisme.svg")
    assert response.status_code == 200
    assert not response.cache_control.no_cache
    assert response.cache_control.max_age == UNVERSIONED_MAX_AGE


def test_modified_file_version(app):
    """Test that a file modified without restarting gets a new version, even when
    its modification time is preserved."""
    static_file = Path(app.static_folder) / "test-version.txt"
    try:
        static_file.write_text("first")
        with app.test_request_context():
            first_version = static_file_version("test-version.txt")
            stat = os.stat(static_file)

            static_file.write_text("second release")
            os.utime(static_file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            assert static_file_version("test-version.txt") != first_version
    finally:
        static_file.unlink()


def test_uploads_cache(app, client):
    """Test that personal uploads are neither versioned nor cached."""
    avatars = Path(app.static_folder) / "uploads" / "avatars"
    avatars.mkdir(parents=True, exist_ok=True)
    avatar = avatars / "user-test-cache.png"
    try:
        avatar.write_bytes(b"not really a png")
        with app.test_request_context():
            assert static_file_version("uploads/avatars/user-test-cache.png") is None
            url = url_for("static", filename="uploads/avatars/user-test-cache.png")
        assert url == "/static/uploads/avatars/user-test-cache.png"

        response = client.get(url)
        assert response.status_code == 200
        assert response.cache_control.no_cache
        assert not response.cache_control.public
    finally:
        avatar.unlink()


def test_static_importmap(app, user1_client):
    """Test that the import map points modules to their versioned URL."""
    response = user1_client.get(
        "/collectives/", headers={"User-Agent": "Mozilla/5.0 Firefox/131.0"}
    )
    assert response.status_code == 200

    importmap = re.search(
        r'<script type="importmap">(.*?)</script>', response.text, re.S
    ).group(1)
    imports = json.loads(importmap)["imports"]

    with app.test_request_context():
        assert imports["/static/js/api.js"] == url_for("static", filename="js/api.js")
    assert imports["/static/js/api.js"].startswith("/static/js/api.js?v=")
    assert imports["axios"].startswith("https://")
    # Classic scripts are not listed
    assert "/static/js/main.js" not in imports
