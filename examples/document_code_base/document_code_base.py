#!/usr/bin/env python

import argparse
import typing

from pathlib import Path


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


def document_file(
    content: str,
    filepath: Path,
) -> typing.Optional[str]:

    return content


def document_directory(
    files: dict,
    readmes: dict,
    original_readme: typing.Optional[str] = None,
) -> typing.Optional[str]:

    return original_readme


# --------- FILE PROCESSING --------------------------------------------------


def process_files(dir_path: Path, depth: int):
    # Now process the files within this directory
    files = {}
    for f in dir_path.glob("*.py"):
        print(f"{'  ' * (depth+1)}{f}")

        content = f.read_text(encoding="utf-8")

        new_content = document_file(content, f)
        if new_content:
            f.write_text(new_content, encoding="utf-8")
            files[f] = new_content
        else:
            files[f] = content

    return files


def traverse_and_document(dir_path: Path, depth: int):
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
        traverse_and_document(subdir, depth + 1)

    # Now process the files within this directory
    files = process_files(dir_path, depth)

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
    readme = document_directory(files, readmes, original_readme)
    if readme:
        f = dir_path / "README.md"
        f.write_text(readme, encoding="utf-8")

    return


def main():
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
    traverse_and_document(args.root_dir, 0)


if __name__ == "__main__":
    main()
