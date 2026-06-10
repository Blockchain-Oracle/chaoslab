"""Shared test bootstrap for phoenix-audit-agent.

macOS + Homebrew: WeasyPrint loads Pango via cffi `dlopen`, which does not
search /opt/homebrew/lib by default on Apple Silicon. Setting the fallback
path here (before any deferred `import weasyprint`) makes the PDF renderer
tests run on dev machines with `brew install pango`; Linux CI and the
Docker image get the libraries via apt and ignore this.
"""

from __future__ import annotations

import os
import sys

if sys.platform == "darwin":
    _brew_lib = "/opt/homebrew/lib"
    if os.path.isdir(_brew_lib):
        existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        if _brew_lib not in existing.split(":"):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                f"{existing}:{_brew_lib}" if existing else _brew_lib
            )
