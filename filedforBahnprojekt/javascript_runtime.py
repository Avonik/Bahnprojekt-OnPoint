import os
import shutil
from pathlib import Path


def resolve_javascript_runtime(project_dir):
    """Resolve the runtime used for DB API requests, preferring Bun in auto mode."""
    configured_runtime = os.getenv("NODE_EXECUTABLE", "auto").strip()
    # Older deployments used NODE_EXECUTABLE=node from the previous example
    # configuration. Treat that legacy value like auto so updating the code and
    # npm dependencies is sufficient to activate the workaround.
    if configured_runtime and configured_runtime.lower() not in {"auto", "node"}:
        return configured_runtime

    project_dir = Path(project_dir).resolve()
    bundled_candidates = [
        project_dir / "my-app" / "node_modules" / "bun" / "bin" / "bun.exe",
        project_dir / "my-app" / "node_modules" / "bun" / "bin" / "bun",
        project_dir / "my-app" / "node_modules" / ".bin" / "bun.exe",
        project_dir / "my-app" / "node_modules" / ".bin" / "bun",
    ]
    for bundled_bun in bundled_candidates:
        if bundled_bun.is_file():
            return str(bundled_bun)

    system_bun = shutil.which("bun")
    if system_bun:
        return system_bun

    # Keep a legacy fallback for environments where dependencies have not yet
    # been reinstalled. DB currently blocks Node's network fingerprint, though,
    # so normal deployments should install the package-provided Bun runtime.
    return shutil.which("node") or "node"
