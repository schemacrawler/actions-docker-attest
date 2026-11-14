#!/usr/bin/env python3
"""Update GitHub release notes with Docker image provenance information."""

import json
import os
import re
import sys
from pathlib import Path


def main() -> None:
    """Read release JSON, update with provenance section, and write updated notes."""
    work_dir = Path(os.environ["WORK_DIR"])

    # Read the release JSON
    release = json.loads(
        (work_dir / "release.json").read_text(encoding="utf-8")
    )
    body = release.get("body") or ""

    # Get provenance information from environment
    image = os.environ["IMAGE_NAME"]
    digest = os.environ["DIGEST"]
    outcome = os.environ["ATTESTATION_OUTCOME"]
    url = os.environ.get("ATTESTATION_URL", "")

    # Define marker delimiters
    start = "<!-- docker-image-provenance:start -->"
    end = "<!-- docker-image-provenance:end -->"

    # Build the new provenance section
    lines = [
        start,
        "## Docker Image Provenance",
        "",
        f"**Image Reference:** `{image}@{digest}`",
        "",
        f"**Digest:** `{digest}`",
        "",
    ]

    if outcome == "success":
        lines.append("**Attestation Status:** Signed provenance available")
        if url:
            lines.extend(["", f"[View attestation]({url})"])
    else:
        lines.append(
            "**Attestation Status:** Attestation was not completed "
            "for this image"
        )

    lines.append(end)
    new_section = "\n".join(lines)

    # Validate marker counts
    if body.count(start) != body.count(end) or body.count(start) > 1:
        raise SystemExit(
            "Unexpected provenance markers; refusing to modify notes."
        )

    # Replace or prepend the provenance section
    if start in body:
        pattern = re.escape(start) + r".*?" + re.escape(end)
        updated, count = re.subn(
            pattern,
            lambda match: new_section,
            body,
            count=1,
            flags=re.DOTALL,
        )
        if count != 1:
            raise SystemExit(
                "Invalid provenance marker order; notes unchanged."
            )
    elif body:
        updated = new_section + "\n\n" + body
    else:
        updated = new_section + "\n"

    # Write the updated notes to file
    (work_dir / "updated-notes.md").write_text(
        updated,
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
