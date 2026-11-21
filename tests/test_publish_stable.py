from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.release import publish_stable

REPO_URL = f"https://github.com/{publish_stable.REPO}.git"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


@pytest.fixture
def release_repo(tmp_path, monkeypatch):
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Release Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "release@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Release Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "release@example.invalid")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
    git("init", "--quiet", "--bare", str(remote))
    git("init", "--quiet", "--initial-branch=master")
    git("remote", "add", "origin", REPO_URL)
    manifest = Path(publish_stable.MANIFEST)
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"version":"3.2.1"}')
    git("add", str(manifest))
    git("commit", "-qm", "Stable snapshot")
    commit = git("rev-parse", "HEAD")
    git("push", str(remote), "master")
    git("switch", "-qc", "dev")
    manifest.write_text('{"version":"3.2.2.dev1"}')
    git("commit", "-qam", "Unrelated local checkout")

    run = {"headSha": commit, "status": "completed", "conclusion": "success", "url": "https://ci"}
    original = publish_stable.command

    def dispatch(*args):
        if args[0] == "gh":
            assert args[args.index("--commit") + 1] == commit
            assert args[args.index("--event") + 1] == "push"
            assert args[args.index("--workflow") + 1] == "ci.yml"
            return json.dumps([run])
        if args[:4] == ("git", "remote", "get-url", "--push"):
            return original(*args)
        return original(*(str(remote) if arg == REPO_URL else arg for arg in args))

    monkeypatch.setattr(publish_stable, "command", dispatch)
    return remote, commit, run


def test_preview_reads_the_remote_version_without_creating_a_tag(release_repo, capsys):
    remote, commit, _ = release_repo
    assert publish_stable.main([]) == 0
    assert f"v3.2.1 → {commit}" in capsys.readouterr().out
    assert git("tag", "--list") == git("--git-dir", str(remote), "tag", "--list") == ""


def test_push_tags_only_the_green_remote_commit(release_repo):
    remote, commit, _ = release_repo
    assert publish_stable.main(["--push", "v3.2.1"]) == 0
    assert git("--git-dir", str(remote), "cat-file", "-t", "refs/tags/v3.2.1") == "tag"
    assert git("--git-dir", str(remote), "rev-parse", "v3.2.1^{commit}") == commit
    with pytest.raises(SystemExit):
        publish_stable.main(["--push", "v3.2.1"])
    assert git("--git-dir", str(remote), "rev-parse", "v3.2.1^{commit}") == commit


@pytest.mark.parametrize("status, conclusion", [("completed", "failure"), ("in_progress", "")])
def test_push_refuses_without_green_ci(release_repo, status, conclusion):
    remote, _, run = release_repo
    run.update(status=status, conclusion=conclusion)
    with pytest.raises(SystemExit):
        publish_stable.main(["--push", "v3.2.1"])
    assert git("tag", "--list") == git("--git-dir", str(remote), "tag", "--list") == ""


def test_push_requires_the_previewed_version(release_repo):
    remote, _, _ = release_repo
    with pytest.raises(SystemExit):
        publish_stable.main(["--push", "v3.2.0"])
    assert git("tag", "--list") == git("--git-dir", str(remote), "tag", "--list") == ""
