#!/usr/bin/env python3
"""Download nanochat data from S3 (DigitalOcean Spaces) and optionally symlink to ~/.cache/nanochat."""

import argparse
import os
import re
import shutil
import subprocess
import sys

S3_BASE = "s3://aneekb/nanochat_run_artifacts/nanochat"
CACHE_LINK = os.path.expanduser("~/.cache/nanochat")
BASE_RUN = "d23"

MINIMAL_DIRS = ["tokenizer/", "eval_bundle/"]


def run_s3cmd(args: list[str], capture=False) -> subprocess.CompletedProcess:
    cmd = ["s3cmd"] + args
    print(f"  -> {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, capture_output=capture, text=capture)


def check_prerequisites():
    if shutil.which("s3cmd") is None:
        sys.exit("Error: s3cmd is not installed. Run: apt install s3cmd -y")
    s3cfg = os.path.expanduser("~/.s3cfg")
    if not os.path.exists(s3cfg):
        sys.exit(f"Error: {s3cfg} not found. Copy your .s3cfg before running this script.")


def find_latest_step() -> str:
    """List base_checkpoints/<run>/ and find the highest step number."""
    prefix = f"{S3_BASE}/base_checkpoints/{BASE_RUN}/"
    result = run_s3cmd(["ls", prefix], capture=True)
    steps = set()
    for line in result.stdout.splitlines():
        m = re.search(r"(?:model|meta|optim)_(\d+)", line)
        if m:
            steps.add(int(m.group(1)))
    if not steps:
        sys.exit(f"Error: no checkpoints found under {prefix}")
    latest = max(steps)
    print(f"  Latest checkpoint step: {latest:06d}")
    return f"{latest:06d}"


def sync_dir(s3_path: str, local_path: str):
    os.makedirs(local_path, exist_ok=True)
    run_s3cmd(["sync", s3_path, local_path + "/"])


def get_file(s3_path: str, local_path: str):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    run_s3cmd(["get", "--skip-existing", s3_path, local_path])


def download_minimal(download_dir: str, dry_run: bool):
    print("\n[minimal] Downloading tokenizer, eval_bundle, and latest base checkpoint...\n")

    step = find_latest_step()
    ckpt_prefix = f"{S3_BASE}/base_checkpoints/{BASE_RUN}"

    tasks = []
    for d in MINIMAL_DIRS:
        tasks.append(("dir", f"{S3_BASE}/{d}", os.path.join(download_dir, d.rstrip("/"))))
    tasks.append(("file",
                   f"{ckpt_prefix}/model_{step}.pt",
                   os.path.join(download_dir, "base_checkpoints", BASE_RUN, f"model_{step}.pt")))
    tasks.append(("file",
                   f"{ckpt_prefix}/meta_{step}.json",
                   os.path.join(download_dir, "base_checkpoints", BASE_RUN, f"meta_{step}.json")))

    if dry_run:
        print("Dry-run — would download:")
        for kind, src, dst in tasks:
            print(f"  [{kind}] {src}  ->  {dst}")
        return

    for kind, src, dst in tasks:
        if kind == "dir":
            sync_dir(src, dst)
        else:
            get_file(src, dst)


def download_all(download_dir: str, dry_run: bool):
    print("\n[all] Downloading entire nanochat S3 folder...\n")
    if dry_run:
        print(f"Dry-run — would sync {S3_BASE}/  ->  {download_dir}/")
        return
    sync_dir(S3_BASE + "/", download_dir)


def download_selective(download_dir: str, paths: list[str], dry_run: bool):
    print(f"\n[selective] Downloading {len(paths)} path(s)...\n")
    for p in paths:
        src = f"{S3_BASE}/{p}"
        dst = os.path.join(download_dir, p.rstrip("/"))
        is_dir = p.endswith("/")
        if dry_run:
            print(f"  Dry-run — would {'sync' if is_dir else 'get'}: {src}  ->  {dst}")
        elif is_dir:
            sync_dir(src, dst)
        else:
            get_file(src, dst)


def setup_symlink(download_dir: str, force: bool):
    download_dir = os.path.realpath(download_dir)
    cache_parent = os.path.dirname(CACHE_LINK)
    os.makedirs(cache_parent, exist_ok=True)

    if os.path.islink(CACHE_LINK):
        existing_target = os.path.realpath(CACHE_LINK)
        if existing_target == download_dir:
            print(f"Symlink already correct: {CACHE_LINK} -> {download_dir}")
            return
        print(f"Removing stale symlink: {CACHE_LINK} -> {existing_target}")
        os.remove(CACHE_LINK)
    elif os.path.exists(CACHE_LINK):
        if not force:
            sys.exit(
                f"Error: {CACHE_LINK} exists and is not a symlink. "
                f"Use --force to remove it, or remove it manually."
            )
        print(f"--force: removing existing directory {CACHE_LINK}")
        shutil.rmtree(CACHE_LINK)

    os.symlink(download_dir, CACHE_LINK)
    print(f"Symlink created: {CACHE_LINK} -> {download_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Download nanochat data from S3 and optionally symlink to ~/.cache/nanochat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  # Minimal download + symlink
  python scripts/download_data.py --minimal -d /workspace/nanochat-data -s

  # Download everything
  python scripts/download_data.py --all -d /workspace/nanochat-data -s

  # Selective: only tokenizer and base_checkpoints
  python scripts/download_data.py -d /workspace/nanochat-data -s tokenizer/ base_checkpoints/

  # Download to ~/.cache/nanochat directly (no symlink needed)
  python scripts/download_data.py --minimal -d ~/.cache/nanochat
""",
    )
    parser.add_argument("-d", "--download-dir", required=True,
                        help="Local directory to download data into")
    parser.add_argument("-s", "--symlink", action="store_true",
                        help="Create symlink: ~/.cache/nanochat -> download-dir")
    parser.add_argument("--force", action="store_true",
                        help="Force-remove ~/.cache/nanochat if it is a real directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without doing it")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--minimal", action="store_true",
                      help="Download only: tokenizer, eval_bundle, latest base checkpoint (model+meta)")
    mode.add_argument("--all", action="store_true",
                      help="Download everything from the S3 nanochat folder")

    parser.add_argument("paths", nargs="*",
                        help="Specific S3 sub-paths to download (e.g. tokenizer/ base_checkpoints/)")

    args = parser.parse_args()

    if not args.minimal and not args.all and not args.paths:
        parser.error("Specify --minimal, --all, or one or more paths to download")
    if (args.minimal or args.all) and args.paths:
        parser.error("Cannot combine --minimal/--all with explicit paths")

    check_prerequisites()

    download_dir = os.path.expanduser(args.download_dir)
    os.makedirs(download_dir, exist_ok=True)

    if args.symlink:
        setup_symlink(download_dir, args.force)

    if args.minimal:
        download_minimal(download_dir, args.dry_run)
    elif args.all:
        download_all(download_dir, args.dry_run)
    else:
        download_selective(download_dir, args.paths, args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
