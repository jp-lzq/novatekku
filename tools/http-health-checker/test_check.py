import contextlib
import http.server
import tempfile
import threading
import unittest
from pathlib import Path

import check


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ok":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


@contextlib.contextmanager
def server():
    instance = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{instance.server_port}"
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join()


class HealthCheckerTest(unittest.TestCase):
    def test_success(self):
        with server() as base_url:
            result = check.check_url(base_url + "/ok")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["content_type"], "text/plain")

    def test_http_error(self):
        with server() as base_url:
            result = check.check_url(base_url + "/missing")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 404)

    def test_target_file(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "targets.txt"
            filename.write_text("example.com\n# skip\nhttps://example.org\n", encoding="utf-8")
            targets = check.read_targets(["example.com"], filename)
        self.assertEqual(targets, ["https://example.com", "https://example.org"])

    def test_report_escapes_values(self):
        result = {
            "url": "https://example.com/?a=<b>",
            "ok": False,
            "status": None,
            "elapsed_ms": 1.0,
            "error": "bad <value>",
        }
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "report.html"
            check.write_html(filename, [result])
            report = filename.read_text(encoding="utf-8")
        self.assertIn("&lt;b&gt;", report)
        self.assertIn("bad &lt;value&gt;", report)


if __name__ == "__main__":
    unittest.main()
