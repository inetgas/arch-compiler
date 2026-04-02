#!/usr/bin/env python3
"""Tests for sec-auth-* pattern selection based on nfr.security.auth value."""
import subprocess
import yaml
from pathlib import Path
import tempfile


def _compile(spec_content: str) -> list[str]:
    """Compile a spec string and return selected pattern IDs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_file = Path(tmpdir) / "spec.yaml"
        spec_file.write_text(spec_content)
        result = subprocess.run(
            ["python3", "tools/archcompiler.py", str(spec_file), "-o", tmpdir],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Compiler failed:\n{result.stderr}"
        selected = yaml.safe_load((Path(tmpdir) / "selected-patterns.yaml").read_text())
        return [p["id"] for p in selected]


AUTH_PATTERNS = {
    "sec-auth-api-key",
    "sec-auth-jwt-stateless",
    "sec-auth-oauth2-oidc",
    "sec-auth-password",
    "sec-auth-saml-sso",
    "sec-auth-session-cookies",
    "sec-auth-mtls-service-mesh",
}


def _selected_auth_patterns(selected_ids: list[str]) -> set[str]:
    return {pid for pid in selected_ids if pid in AUTH_PATTERNS}


def _auth_spec(auth_value: str, platform: str = "api") -> str:
    return f"""project:
  name: Test
  domain: test
functional:
  summary: Test
constraints:
  platform: {platform}
  cloud: agnostic
  language: agnostic
nfr:
  security:
    auth: {auth_value}
"""


def test_api_key_selects_only_sec_auth_api_key():
    """auth: api_key selects exactly sec-auth-api-key and no other auth pattern."""
    selected = _compile(_auth_spec("api_key"))
    auth_selected = _selected_auth_patterns(selected)
    assert "sec-auth-api-key" in auth_selected, "sec-auth-api-key must be selected for auth: api_key"
    assert auth_selected == {"sec-auth-api-key"}, f"Only sec-auth-api-key should be selected, got: {auth_selected}"


def test_jwt_selects_only_sec_auth_jwt_stateless():
    """auth: jwt selects exactly sec-auth-jwt-stateless and no other auth pattern."""
    selected = _compile(_auth_spec("jwt"))
    auth_selected = _selected_auth_patterns(selected)
    assert "sec-auth-jwt-stateless" in auth_selected, "sec-auth-jwt-stateless must be selected for auth: jwt"
    assert auth_selected == {"sec-auth-jwt-stateless"}, f"Only sec-auth-jwt-stateless should be selected, got: {auth_selected}"


def test_oauth2_selects_only_sec_auth_oauth2_oidc():
    """auth: oauth2_oidc selects exactly sec-auth-oauth2-oidc and no other auth pattern."""
    selected = _compile(_auth_spec("oauth2_oidc"))
    auth_selected = _selected_auth_patterns(selected)
    assert "sec-auth-oauth2-oidc" in auth_selected
    assert auth_selected == {"sec-auth-oauth2-oidc"}, f"Got: {auth_selected}"


def test_password_selects_only_sec_auth_password():
    """auth: password selects exactly sec-auth-password and no other auth pattern."""
    selected = _compile(_auth_spec("password", platform="web"))
    auth_selected = _selected_auth_patterns(selected)
    assert "sec-auth-password" in auth_selected
    assert auth_selected == {"sec-auth-password"}, f"Got: {auth_selected}"


def test_saml_selects_only_sec_auth_saml_sso():
    """auth: saml selects exactly sec-auth-saml-sso and no other auth pattern."""
    spec = _auth_spec("saml", platform="web") + "    audit_logging: true\n"
    selected = _compile(spec)
    auth_selected = _selected_auth_patterns(selected)
    assert "sec-auth-saml-sso" in auth_selected
    assert auth_selected == {"sec-auth-saml-sso"}, f"Got: {auth_selected}"


def test_mtls_selects_only_sec_auth_mtls():
    """auth: mtls selects exactly sec-auth-mtls-service-mesh and no other auth pattern."""
    selected = _compile(_auth_spec("mtls"))
    auth_selected = _selected_auth_patterns(selected)
    assert "sec-auth-mtls-service-mesh" in auth_selected
    assert auth_selected == {"sec-auth-mtls-service-mesh"}, f"Got: {auth_selected}"


def test_no_auth_selects_no_auth_patterns():
    """auth: n/a selects no sec-auth-* patterns."""
    selected = _compile(_auth_spec("n/a"))
    auth_selected = _selected_auth_patterns(selected)
    assert auth_selected == set(), f"No auth patterns should be selected for auth: n/a, got: {auth_selected}"


def test_session_cookies_only_for_web_platform():
    """sec-auth-session-cookies is only selected for platform: web."""
    # API platform - should NOT select session cookies
    api_selected = _selected_auth_patterns(_compile(_auth_spec("n/a", platform="api")))
    assert "sec-auth-session-cookies" not in api_selected, "session-cookies must not be selected for platform: api"

    # Web platform with n/a auth - SHOULD select session cookies
    web_selected = _selected_auth_patterns(_compile(_auth_spec("n/a", platform="web")))
    assert "sec-auth-session-cookies" in web_selected, "session-cookies must be selected for platform: web"


def test_password_excluded_for_api_platform():
    """sec-auth-password is only suitable for human-user platforms, excluded for API."""
    selected = _compile(_auth_spec("password", platform="api"))
    auth_selected = _selected_auth_patterns(selected)
    assert "sec-auth-password" not in auth_selected, "password auth must not be selected for platform: api"


def test_saml_excluded_for_api_platform():
    """sec-auth-saml-sso is only suitable for human-user platforms, excluded for API."""
    selected = _compile(_auth_spec("saml", platform="api"))
    auth_selected = _selected_auth_patterns(selected)
    assert "sec-auth-saml-sso" not in auth_selected, "saml-sso auth must not be selected for platform: api"


def test_jwt_accepted_by_schema():
    """jwt must be a valid value for nfr.security.auth (compiler accepts it without error)."""
    selected = _compile(_auth_spec("jwt"))
    assert isinstance(selected, list), "Compiler must accept auth: jwt without error"
