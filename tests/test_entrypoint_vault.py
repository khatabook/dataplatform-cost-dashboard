from __future__ import annotations

import os
import subprocess
from pathlib import Path

ENTRYPOINT = Path(__file__).resolve().parents[1] / "scripts" / "entrypoint.sh"


def _run(secrets: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    secrets_path = Path(os.environ.get("TMPDIR", "/tmp")) / f"vault-test-{os.getpid()}.txt"
    secrets_path.write_text(secrets)
    try:
        return subprocess.run(
            [
                "bash",
                str(ENTRYPOINT),
                "bash",
                "-lc",
                'printf "%s|%s|%s" "$DATABASE_URL" "$SNOWFLAKE_USER" "$SNOWFLAKE_PASSWORD"',
            ],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "VAULT_SECRETS_FILE": str(secrets_path),
                "PARSED_SECRETS_FILE": str(secrets_path) + ".parsed",
                **(env or {}),
            },
            check=False,
        )
    finally:
        secrets_path.unlink(missing_ok=True)
        Path(str(secrets_path) + ".parsed").unlink(missing_ok=True)


def test_entrypoint_exports_key_value_secrets():
    result = _run(
        "\n".join(
            [
                "DATABASE_URL=postgresql://cost:cost@db/cost",
                "SNOWFLAKE_USER=cost_reader",
                "SNOWFLAKE_PASSWORD=s3cret",
            ]
        )
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith(
        "postgresql://cost:cost@db/cost|cost_reader|s3cret"
    )


def test_entrypoint_exports_go_map_secrets():
    result = _run(
        "data: map[DATABASE_URL:postgresql://cost:cost@db:5432/cost "
        "SNOWFLAKE_USER:cost_reader SNOWFLAKE_PASSWORD:s3cret]"
    )
    assert result.returncode == 0, result.stderr
    assert "postgresql://cost:cost@db:5432/cost" in result.stdout
    assert "cost_reader" in result.stdout
    assert "s3cret" in result.stdout


def test_entrypoint_skips_missing_vault_file():
    result = subprocess.run(
        ["bash", str(ENTRYPOINT), "bash", "-lc", 'echo ok-$DATABASE_URL'],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "VAULT_SECRETS_FILE": "/tmp/does-not-exist-vault-secrets.txt",
            "DATABASE_URL": "from-env",
        },
        check=False,
    )
    assert result.returncode == 0
    assert "ok-from-env" in result.stdout
