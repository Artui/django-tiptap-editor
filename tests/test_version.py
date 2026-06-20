from __future__ import annotations

import django_tiptap_editor
from django_tiptap_editor.version import __version__


def test_version_is_a_nonempty_string() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_package_reexports_version() -> None:
    assert django_tiptap_editor.__version__ == __version__
