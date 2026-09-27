import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_git_leak_check_passes_on_main_tree():
    subprocess.run(["bash", "scripts/git-leak-check.sh"], cwd=ROOT, check=True)


def _tracked_copy(files: dict[str, str]) -> Path:
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
    scripts = tmp / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts" / "git-leak-check.sh", scripts / "git-leak-check.sh")
    for name, body in files.items():
        path = tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", *files], cwd=tmp, check=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=tmp, check=True, capture_output=True, env=env)
    return tmp


def test_leak_check_fails_when_a_private_path_is_tracked():
    for files, needle in (
        ({"PLAN.md": "plan"}, "PLAN.md"),
        ({"private/profile.yaml": "name: ada"}, "profile.yaml"),
        ({"private/notes.yaml": "x"}, "private/"),
    ):
        repo = _tracked_copy(files)
        result = subprocess.run(
            ["bash", "scripts/git-leak-check.sh"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert needle in result.stderr


def test_leak_check_allows_the_example_profile_only():
    repo = _tracked_copy({"private/profile.example.yaml": "name: ada"})
    subprocess.run(["bash", "scripts/git-leak-check.sh"], cwd=repo, check=True)


RETIRED_PUBLIC_GITLAB = "git@gitlab.com:meine-group4/kaufen-oder-mieten.git"


def test_publish_script_pushes_main_to_github_only():
    body = (ROOT / "scripts" / "publish.sh").read_text(encoding="utf-8")
    assert "git push github main" in body
    assert "git push origin main" not in body
    assert "git push github private" not in body
    assert "release-version.sh" in body
    assert RETIRED_PUBLIC_GITLAB in body


def _git_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }


def test_release_version_bumps_once_and_retry_skips():
    tmp = Path(tempfile.mkdtemp())
    try:
        subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
        scripts = tmp / "scripts"
        scripts.mkdir()
        shutil.copy(ROOT / "scripts" / "release-version.sh", scripts / "release-version.sh")
        (tmp / "pyproject.toml").write_text('version = "0.1.0"\n', encoding="utf-8")
        env = _git_env()
        subprocess.run(["git", "add", "pyproject.toml"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: fixture"],
            cwd=tmp,
            check=True,
            capture_output=True,
            env=env,
        )
        subprocess.run(["bash", "scripts/release-version.sh"], cwd=tmp, check=True)
        text = (tmp / "pyproject.toml").read_text(encoding="utf-8")
        assert 'version = "0.1.1"' in text
        log = subprocess.check_output(["git", "log", "-1", "--format=%s"], cwd=tmp, text=True).strip()
        assert log == "chore: release 0.1.1"
        subprocess.run(["bash", "scripts/release-version.sh"], cwd=tmp, check=True)
        assert (tmp / "pyproject.toml").read_text(encoding="utf-8") == text
        count = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=tmp, text=True).strip()
        assert count == "2"
    finally:
        shutil.rmtree(tmp)


def _publish_fixture() -> Path:
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp, check=True, capture_output=True)
    scripts = tmp / "scripts"
    scripts.mkdir()
    for name in ("publish.sh", "git-leak-check.sh", "release-version.sh"):
        shutil.copy(ROOT / "scripts" / name, scripts / name)
    example = tmp / "private" / "profile.example.yaml"
    example.parent.mkdir()
    example.write_text("name: ada\n", encoding="utf-8")
    (tmp / "src" / "backend").mkdir(parents=True)
    (tmp / "pyproject.toml").write_text('version = "0.1.0"\n', encoding="utf-8")
    pytest_bin = tmp / ".venv" / "bin" / "pytest"
    pytest_bin.parent.mkdir(parents=True)
    pytest_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    pytest_bin.chmod(0o755)
    env = _git_env()
    subprocess.run(["git", "add", "pyproject.toml", "private/profile.example.yaml"], cwd=tmp, check=True)
    subprocess.run(["git", "commit", "-m", "feat: fixture"], cwd=tmp, check=True, capture_output=True, env=env)
    return tmp


def test_publish_refuses_retired_gitlab_on_any_remote_and_does_not_push():
    tmp = _publish_fixture()
    bare = Path(tempfile.mkdtemp())
    try:
        subprocess.run(["git", "init", "--bare"], cwd=bare, check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "github", str(bare)], cwd=tmp, check=True)
        subprocess.run(
            ["git", "remote", "add", "old", RETIRED_PUBLIC_GITLAB],
            cwd=tmp,
            check=True,
        )
        result = subprocess.run(
            ["bash", "scripts/publish.sh"],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "refused" in result.stderr.lower()
        heads = subprocess.run(["git", "rev-parse", "--verify", "refs/heads/main"], cwd=bare, capture_output=True)
        assert heads.returncode != 0
    finally:
        shutil.rmtree(tmp)
        shutil.rmtree(bare)


def test_publish_pushes_main_to_github_without_an_origin_remote():
    tmp = _publish_fixture()
    bare = Path(tempfile.mkdtemp())
    other = Path(tempfile.mkdtemp())
    try:
        subprocess.run(["git", "init", "--bare"], cwd=bare, check=True, capture_output=True)
        subprocess.run(["git", "init", "--bare"], cwd=other, check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "github", str(bare)], cwd=tmp, check=True)
        subprocess.run(["git", "remote", "add", "mirror", str(other)], cwd=tmp, check=True)
        subprocess.run(["bash", "scripts/publish.sh"], cwd=tmp, check=True)
        github_head = subprocess.check_output(["git", "rev-parse", "refs/heads/main"], cwd=bare, text=True).strip()
        local_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp, text=True).strip()
        assert github_head == local_head
        other_head = subprocess.run(["git", "rev-parse", "--verify", "refs/heads/main"], cwd=other, capture_output=True)
        assert other_head.returncode != 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(bare, ignore_errors=True)
        shutil.rmtree(other, ignore_errors=True)


def test_backup_refuses_the_retired_public_gitlab_url():
    result = subprocess.run(
        ["bash", "scripts/backup.sh"],
        cwd=ROOT,
        env={**os.environ, "BUY_VS_RENT_BACKUP_REMOTE": RETIRED_PUBLIC_GITLAB},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "refused" in (result.stderr + result.stdout).lower()


def test_backup_refuses_the_public_github_url():
    try:
        github = subprocess.check_output(["git", "remote", "get-url", "github"], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        pytest.skip("no github remote configured")
    result = subprocess.run(
        ["bash", "scripts/backup.sh"],
        cwd=ROOT,
        env={**os.environ, "BUY_VS_RENT_BACKUP_REMOTE": github},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "refused" in (result.stderr + result.stdout).lower()
