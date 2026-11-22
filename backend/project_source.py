"""Read a small operator-published project brief, without launching commands."""

import os
import re
import stat
from pathlib import Path

PROJECT_SOURCE_ID = re.compile(r"[a-zA-Z0-9_-]{1,80}")
MAX_BRIEF_BYTES = 8192


def project_brief(root, project_id):
    if not root or not PROJECT_SOURCE_ID.fullmatch(project_id):
        return ""
    # The operator controls this directory. No path is supplied by a web request.
    path = Path(root) / f"{project_id}.md"
    try:
        with os.fdopen(
            os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb"
        ) as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return ""
            return (
                stream.read(MAX_BRIEF_BYTES).decode("utf-8", errors="replace").strip()
            )
    except OSError:
        return ""
