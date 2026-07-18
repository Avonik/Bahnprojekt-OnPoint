import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from javascript_runtime import resolve_javascript_runtime


class JavascriptRuntimeTests(unittest.TestCase):
    def test_auto_detects_linux_npm_bun_binary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            bun_path = (
                project_dir
                / "my-app"
                / "node_modules"
                / "bun"
                / "bin"
                / "bun"
            )
            bun_path.parent.mkdir(parents=True)
            bun_path.write_bytes(b"")

            with patch.dict(os.environ, {"NODE_EXECUTABLE": "auto"}):
                self.assertEqual(
                    resolve_javascript_runtime(project_dir),
                    str(bun_path),
                )


if __name__ == "__main__":
    unittest.main()
