"""Preview the next stable tag, or push it explicitly with --push."""

from __future__ import annotations

import argparse
import json
import re
import subprocess

REPO = "happydasch/nspanel_haui"
MASTER_REF = "refs/heads/master"
MANIFEST = "custom_components/nspanel_haui/manifest.json"


def command(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def remote_ref(remote: str, ref: str) -> str:
    return command("git", "ls-remote", "--refs", remote, ref).split("\t", 1)[0]


def remote_is_canonical(url: str) -> bool:
    """Whether a remote URL pushes to the canonical repository."""
    return url.lower().removesuffix(".git") in {
        f"https://github.com/{REPO}",
        f"git@github.com:{REPO}",
        f"ssh://git@github.com/{REPO}",
    }


def publish(*, push: str | None) -> None:
    remote = command("git", "remote", "get-url", "--push", "origin")
    if not remote_is_canonical(remote):
        raise ValueError(f"origin must push to github.com/{REPO}")

    commit = remote_ref(remote, MASTER_REF)
    if not commit:
        raise ValueError("origin has no master branch")
    command("git", "fetch", "--no-tags", remote, commit)
    version = json.loads(command("git", "show", f"{commit}:{MANIFEST}"))["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError(f"master's manifest does not contain a stable version: {version!r}")
    tag = f"v{version}"
    tag_ref = f"refs/tags/{tag}"
    if remote_ref(remote, tag_ref):
        raise ValueError(f"{tag} is already on origin")

    runs = json.loads(
        command(
            "gh",
            "run",
            "list",
            "--repo",
            REPO,
            "--workflow",
            "ci.yml",
            "--branch",
            "master",
            "--event",
            "push",
            "--commit",
            commit,
            "--limit",
            "1",
            "--json",
            "headSha,status,conclusion,url",
        )
    )
    if not runs or runs[0]["headSha"] != commit:
        raise ValueError(f"No master push CI run for {commit}; wait for CI")
    run = runs[0]
    if run["status"] != "completed" or run["conclusion"] != "success":
        raise ValueError(f"Master push CI has not passed for {commit}: {run['url']}")

    print(f"{tag} → {commit} (origin/master)\nCI: {run['url']}", flush=True)
    if push is None:
        print(f"Preview only. Rerun with --push {tag} to publish this version.")
        return
    if push != tag:
        raise ValueError(f"Expected {push}, but origin/master is now {tag}")

    # Check again after CI lookup; tag the verified SHA, never a moving branch ref.
    if remote_ref(remote, MASTER_REF) != commit:
        raise ValueError("origin/master moved during the preflight; run it again")
    local_tag = command("git", "tag", "--list", tag)
    if local_tag:
        if (
            command("git", "cat-file", "-t", tag_ref) != "tag"
            or command("git", "rev-parse", f"{tag_ref}^{{commit}}") != commit
        ):
            raise ValueError(f"Local {tag} is not an annotated tag for {commit}; inspect it first")
    else:
        command("git", "tag", "-a", tag, commit, "-m", f"NSPanel HAUI {version}")
    command("git", "push", "--no-follow-tags", remote, f"{tag_ref}:{tag_ref}")
    print(f"Pushed {tag}; the stable release workflow now builds and publishes it.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", metavar="TAG", help="create and push the previewed tag")
    args = parser.parse_args(argv)
    try:
        publish(push=args.push)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        parser.exit(1, f"Release preflight failed: {detail}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
