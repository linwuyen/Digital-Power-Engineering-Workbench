import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from server import WorkbenchHandler


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True)
    return result.stdout.strip()


def make_repo(root: Path, *, baseline: bool = False) -> str:
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Status API Test")
    (root / "file.txt").write_text("one\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-m", "initial")
    sha = git(root, "rev-parse", "HEAD")
    if baseline:
        (root / "CURRENT_PRODUCT_BASELINE.md").write_text(
            "FINAL / GOLDEN firmware SHA:\n"
            f"{sha}\n\n"
            "Pinned release ref:\nrelease/final-test\n",
            encoding="utf-8",
        )
        git(root, "add", "CURRENT_PRODUCT_BASELINE.md")
        git(root, "commit", "-m", "baseline declaration")
    return git(root, "rev-parse", "HEAD")


class StatusApiTests(unittest.TestCase):
    def start_server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    def test_summary_is_live_and_query_cannot_override_backend_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            agent = base / "agent"; agent.mkdir()
            firmware = base / "firmware"; firmware.mkdir()
            make_repo(agent)
            expected_sha = make_repo(firmware, baseline=True)
            env = {
                "ASR5K_AGENT_ROOT": str(agent),
                "ASR5K_FIRMWARE_ROOT": str(firmware),
            }
            with patch.dict(os.environ, env, clear=False):
                server, thread = self.start_server()
                try:
                    host, port = server.server_address
                    url = f"http://{host}:{port}/api/status/summary?firmware_root=/tmp/attacker"
                    with urlopen(url, timeout=3) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(payload["mode"], "LIVE")
                    self.assertEqual(payload["execution_plane"]["sha"], expected_sha)
                    self.assertEqual(Path(payload["execution_plane"]["path"]), firmware.resolve())
                finally:
                    server.shutdown(); server.server_close(); thread.join(timeout=3)

    def test_evidence_endpoint_is_read_only_get(self):
        server, thread = self.start_server()
        try:
            host, port = server.server_address
            with urlopen(f"http://{host}:{port}/api/status/evidence", timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["mode"], "LIVE")
            request = Request(
                f"http://{host}:{port}/api/status/summary",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as ctx:
                urlopen(request, timeout=3)
            self.assertEqual(ctx.exception.code, 404)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
