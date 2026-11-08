#!/usr/bin/env python3

import argparse
import html
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote


GUIDE_DIR = Path(__file__).resolve().parent / "user_guide"
CONTAINER = '<div class="outer-container">'
VERSION_NAV = re.compile(r'^    <nav id="guide-version-links">.*?</nav>\n', re.MULTILINE)
PUBLIC_GUIDE_URL = "https://koreader.rocks/user_guide/"


def relative_url(target, directory):
    return quote(os.path.relpath(target, directory).replace(os.sep, "/"), safe="/")


def main():
    parser = argparse.ArgumentParser(description="Archive the current user guide and its translations.")
    parser.add_argument("output_folder", type=Path, help="new archive directory, for example user_guide/25.03")
    args = parser.parse_args()
    destination = args.output_folder.resolve()

    if destination.exists():
        parser.error(f"destination already exists: {destination}")
    if destination == GUIDE_DIR or destination in GUIDE_DIR.parents:
        parser.error("destination must not contain the current guide")
    if destination.is_relative_to(GUIDE_DIR / "pictures"):
        parser.error("destination must not be inside the pictures directory")

    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", "user_guide/*.html"],
        cwd=GUIDE_DIR.parent,
        check=True,
        capture_output=True,
    )
    pages = sorted(
        page for name in os.fsdecode(tracked.stdout).split("\0") if name
        if (page := GUIDE_DIR.parent / name).parent == GUIDE_DIR
    )
    if not pages or not (GUIDE_DIR / "en.html").is_file():
        parser.error("current guide pages not found")

    contents = {page: page.read_text(encoding="utf-8") for page in pages}
    for page, content in contents.items():
        if content.count(CONTAINER) != 1:
            parser.error(f"expected one guide container in {page}")

    destination.mkdir(parents=True)
    shutil.copytree(GUIDE_DIR / "pictures", destination / "pictures")
    favicon = GUIDE_DIR / "favicon.ico"
    if favicon.exists():
        shutil.copy2(favicon, destination / favicon.name)

    version = html.escape(destination.name)
    for page, content in contents.items():
        archived = VERSION_NAV.sub("", content)
        archived = archived.replace(PUBLIC_GUIDE_URL, "./")
        current_url = relative_url(page, destination)
        archive_nav = (
            f'\n    <nav id="guide-version-links">Archived version: {version} | '
            f'<a href="{html.escape(current_url, quote=True)}">Current guide</a></nav>'
        )
        archived = archived.replace(CONTAINER, CONTAINER + archive_nav, 1)
        (destination / page.name).write_text(archived, encoding="utf-8")

    for page, content in contents.items():
        if page.is_symlink():
            continue
        archive_url = relative_url(destination, GUIDE_DIR) + "/"
        link = f'<a href="{html.escape(archive_url, quote=True)}">{version}</a>'
        match = VERSION_NAV.search(content)
        if match:
            navigation = match.group().replace("</nav>", f" | {link}</nav>")
            updated = content[:match.start()] + navigation + content[match.end():]
        else:
            navigation = f'\n    <nav id="guide-version-links">Previous versions: {link}</nav>'
            updated = content.replace(CONTAINER, CONTAINER + navigation, 1)
        page.write_text(updated, encoding="utf-8")

    print(f"Archived {len(pages)} guide pages in {destination}")


if __name__ == "__main__":
    main()