"""Tests for WWW redirect aliases."""

from app.www_redirects import WWW_REDIRECTS


def test_alias_redirects_present():
    assert WWW_REDIRECTS["super"] == "/superokazje"
    assert WWW_REDIRECTS["tools"] == "/narzedzia"
    assert WWW_REDIRECTS["cycles"] == "/cykle"


def test_no_identity_redirect_loops():
    for src, dst in WWW_REDIRECTS.items():
        assert f"/{src}" != dst, f"identity redirect loop: {src} -> {dst}"
