"""Convention guard: root .env must only contain NEXT_PUBLIC_* keys.

The project's root .env is read ONLY by docker-compose for Next.js build-time
public values. Backend secrets live in backend/.env; frontend runtime values
live in frontend/.env and frontend/.env.local.

If anyone re-adds a non-NEXT_PUBLIC_* variable to root .env, this test fails
with a clear pointer to the offending line. This makes "drift" structurally
impossible to reintroduce silently.

Note: .env is gitignored, so these tests skip gracefully in CI where the
file doesn't exist. They still enforce the convention locally.
"""
from pathlib import Path

import pytest

from backend.config import BACKEND_DIR


ROOT_ENV = BACKEND_DIR.parent / ".env"
ALLOWED_PREFIXES = ("NEXT_PUBLIC_",)

_NO_ENV_REASON = "root .env not present (expected in CI; create one locally for this guard)"


def _parse_env(path: Path) -> list[tuple[int, str, str]]:
    """Return (line_no, key, value) for every KEY=VALUE line. Skip blanks and comments."""
    parsed: list[tuple[int, str, str]] = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        parsed.append((n, key.strip(), value))
    return parsed


@pytest.mark.skipif(not ROOT_ENV.exists(), reason=_NO_ENV_REASON)
def test_root_env_file_exists() -> None:
    assert ROOT_ENV.exists(), f"root .env not found at {ROOT_ENV}"


@pytest.mark.skipif(not ROOT_ENV.exists(), reason=_NO_ENV_REASON)
def test_root_env_only_holds_next_public_keys() -> None:
    entries = _parse_env(ROOT_ENV)
    assert entries, (
        "root .env has no variables; at least NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID "
        "is required by docker-compose (see docker-compose.yml frontend build args)"
    )
    violations = [
        (n, k) for n, k, _ in entries
        if not any(k.startswith(p) for p in ALLOWED_PREFIXES)
    ]
    assert not violations, (
        "root .env contains keys that violate the convention "
        "(must start with NEXT_PUBLIC_):\n"
        + "\n".join(f"  line {n}: {k}" for n, k in violations)
        + "\nMove backend-shaped config to backend/.env and frontend runtime "
        "values to frontend/.env."
    )


@pytest.mark.skipif(not ROOT_ENV.exists(), reason=_NO_ENV_REASON)
def test_root_env_has_required_walletconnect_project_id() -> None:
    entries = dict((k, v) for _, k, v in _parse_env(ROOT_ENV))
    assert "NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID" in entries, (
        "docker-compose requires NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID in root .env "
        "(see the `:?` operator in docker-compose.yml frontend build args)"
    )
    assert entries["NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID"].strip(), (
        "NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID is set but empty"
    )
