#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import os
import argparse
import typing
import asyncio

from pathlib import Path

from reasonchip.utils import LocalRunner


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")

if not OPENAI_API_KEY or not OPENAI_ORG_ID:
    raise ValueError(
        "Please set the OPENAI_API_KEY and OPENAI_ORG_ID environment variables."
    )


# Directories to ignore during traversal
IGNORED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
}


def should_ignore_dir(dir_name):
    return dir_name in IGNORED_DIRS or dir_name.startswith(".")


# --------- REASONING --------------------------------------------------------

local_runner = LocalRunner(
    collections=[str(Path(__file__).resolve().parent / "workflows")],
)


async def document_file(filename: str, content: str) -> typing.Optional[str]:
    rc = await local_runner.run(
        pipeline="document_file",
        variables={
            "params": {
                "filename": filename,
                "content": content,
            },
            "secrets": {
                "openai": {
                    "api_key": OPENAI_API_KEY,
                    "org_id": OPENAI_ORG_ID,
                }
            },
        },
    )

    print(f"Received response: {rc}")

    status = rc["status"]

    if status == "ERROR":
        error_message = rc["error_message"]
        raise RuntimeError(error_message)

    if status == "UNCHANGED":
        return None

    assert status == "CHANGED"

    content = rc["content"]
    return content


async def document_directory(
    files: dict,
    readmes: dict,
    original_readme: typing.Optional[str] = None,
) -> typing.Optional[str]:

    rc = await local_runner.run(
        pipeline="document_path",
        variables={
            "params": {
                "files": files,
                "readmes": readmes,
                "original_readme": original_readme or "",
            },
            "secrets": {
                "openai": {
                    "api_key": OPENAI_API_KEY,
                    "org_id": OPENAI_ORG_ID,
                }
            },
        },
    )

    print(f"Received response: {rc}")

    status = rc["status"]

    if status == "ERROR":
        error_message = rc["error_message"]
        raise RuntimeError(error_message)

    if status == "UNCHANGED":
        return None

    assert status == "CHANGED"

    content = rc["content"]
    return content


# --------- FILE PROCESSING --------------------------------------------------


async def process_files(dir_path: Path, depth: int):
    # Now process the files within this directory
    files = {}
    for f in dir_path.glob("*.py"):
        print(f"{'  ' * (depth+1)}{f}")

        content = f.read_text(encoding="utf-8")

        new_content = await document_file(f.name, content)
        if new_content:
            f.write_text(new_content, encoding="utf-8")
            files[f] = new_content
        else:
            files[f] = content

    return files


async def traverse_and_document(dir_path: Path, depth: int):
    # Print the current directory being processed
    print(f"{'  ' * depth}{dir_path}/")

    # Discover all the subdirectories
    subdirs = [
        d
        for d in dir_path.iterdir()
        if d.is_dir() and not should_ignore_dir(d.name)
    ]

    # Deep dive subdirectories first so they are documented
    for subdir in subdirs:
        await traverse_and_document(subdir, depth + 1)

    # Now process the files within this directory
    files = await process_files(dir_path, depth)

    # Now load all the README.md files in the subdirectories
    readmes = {}
    for p in subdirs:
        f = p / "README.md"
        if f.exists():
            readmes[p] = f.read_text(encoding="utf-8")

    # And load the README.md file in this directory, if it exists
    f = dir_path / "README.md"
    if f.exists():
        original_readme = f.read_text(encoding="utf-8")
    else:
        original_readme = None

    # Now we process the README.md for this directory
    readme = await document_directory(files, readmes, original_readme)
    if readme:
        f = dir_path / "README.md"
        f.write_text(readme, encoding="utf-8")

    return


async def main():
    # Parse the arguments
    parser = argparse.ArgumentParser(
        description="Recursively document a python codebase.",
    )
    parser.add_argument(
        "root_dir",
        type=Path,
        help="Root directory from which to start traversal",
    )
    args = parser.parse_args()

    # Begin traversal and documentation
    await traverse_and_document(args.root_dir, 0)


if __name__ == "__main__":
    asyncio.run(main())
