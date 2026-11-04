"""Tests for scripts/generate_images.py against a local fake OpenRouter. No network, no real key.
Run: python3 -m unittest discover -s tests -v"""
import base64
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw

SPEC = importlib.util.spec_from_file_location(
    "generate_images", Path(__file__).resolve().parent.parent / "scripts" / "generate_images.py"
)
gi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gi)

TEST_KEY = "sk-or-TESTKEY-do-not-leak"


def png_b64() -> str:
    im = Image.new("L", (900, 1200), 255)
    ImageDraw.Draw(im).ellipse([200, 300, 700, 800], outline=0, width=12)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


class FakeOpenRouter(BaseHTTPRequestHandler):
    # class-level knobs, reset per test
    fail_first = 0          # number of initial POSTs that return 502
    bad_subject = None      # prompt substring that gets a 400
    cost = 0.03
    seen = []
    lock = threading.Lock()

    def log_message(self, *a):
        pass

    def _send(self, code, obj, headers=None):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/endpoints"):
            self._send(200, {"id": "fake/model", "endpoints": [{"provider_slug": "fake", "pricing": [
                {"billable": "output_image", "unit": "image", "cost_usd": self.cost}]}]})
        else:
            self._send(404, {"error": "nope"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n))
        with FakeOpenRouter.lock:
            FakeOpenRouter.seen.append({"auth": self.headers.get("Authorization"), "payload": payload})
            if FakeOpenRouter.fail_first > 0:
                FakeOpenRouter.fail_first -= 1
                return self._send(502, {"error": "bad gateway"}, {"Retry-After": "0"})
        if self.path != "/api/v1/images":
            return self._send(404, {"error": "nope"})
        if FakeOpenRouter.bad_subject and FakeOpenRouter.bad_subject in payload["prompt"]:
            return self._send(400, {"error": {"message": f"rejected for key {TEST_KEY}"}})
        self._send(200, {"created": 1, "data": [{"b64_json": png_b64(), "media_type": "image/png"}],
                         "usage": {"cost": FakeOpenRouter.cost}})


class GenerateImagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenRouter)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        FakeOpenRouter.fail_first = 0
        FakeOpenRouter.bad_subject = None
        FakeOpenRouter.cost = 0.03
        FakeOpenRouter.seen = []
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.subjects = self.dir / "subjects.txt"
        self.subjects.write_text("# animals\nA happy fox\nA sleepy owl\n\nA smiling turtle\nA brave lion\n")
        self.out = self.dir / "out"
        self._env = dict(os.environ)
        os.environ["OPENROUTER_BASE_URL"] = f"http://127.0.0.1:{self.port}/api/v1"
        os.environ["OPENROUTER_API_KEY"] = TEST_KEY
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = gi.main(argv)
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def gen(self, *extra):
        return self.run_cli(["generate", str(self.subjects), "-o", str(self.out), "--model", "fake/model",
                             "--workers", "1", *extra])

    def test_subjects_skip_comments_and_blanks(self):
        self.assertEqual(gi.read_subjects(self.subjects), ["A happy fox", "A sleepy owl", "A smiling turtle", "A brave lion"])

    def test_generates_files_in_order_with_ledger(self):
        code, so, se = self.gen()
        self.assertEqual(code, 0, se)
        names = sorted(p.name for p in self.out.glob("*.png"))
        self.assertEqual(names, ["01_a-happy-fox.png", "02_a-sleepy-owl.png",
                                 "03_a-smiling-turtle.png", "04_a-brave-lion.png"])
        lines = (self.out / "ledger.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertAlmostEqual(sum(json.loads(l)["cost_usd"] for l in lines), 0.12)
        Image.open(self.out / names[0]).verify()  # valid image

    def test_request_shape(self):
        self.gen("--quality", "low")
        p = FakeOpenRouter.seen[0]
        self.assertEqual(p["auth"], f"Bearer {TEST_KEY}")
        self.assertEqual(p["payload"]["model"], "fake/model")
        self.assertEqual(p["payload"]["aspect_ratio"], "3:4")
        self.assertEqual(p["payload"]["quality"], "low")
        self.assertIn("A happy fox", p["payload"]["prompt"])
        self.assertIn("No shading", p["payload"]["prompt"])

    def test_retries_on_502_then_succeeds(self):
        FakeOpenRouter.fail_first = 2
        orig = gi.post_image
        gi.post_image = lambda *a, **k: orig(*a, **{**k, "sleep": lambda s: None})
        try:
            code, so, se = self.gen("--max-images", "1")
        finally:
            gi.post_image = orig
        self.assertEqual(code, 0, se)
        self.assertEqual(len(list(self.out.glob("*.png"))), 1)
        self.assertEqual(len(FakeOpenRouter.seen), 3)  # 2 failures + 1 success

    def test_resume_skips_existing(self):
        self.gen("--max-images", "2")
        self.assertEqual(len(FakeOpenRouter.seen), 2)
        self.gen()
        self.assertEqual(len(FakeOpenRouter.seen), 4)  # only the 2 missing ones were requested
        self.assertEqual(len(list(self.out.glob("*.png"))), 4)

    def test_budget_stops_before_overspending(self):
        # cost 0.03 each, budget 0.07: two images fit (0.06); a third would need 0.09
        code, so, se = self.gen("--budget", "0.07")
        self.assertEqual(len(list(self.out.glob("*.png"))), 2)
        self.assertIn("not run (budget)", so)
        spent = sum(json.loads(l)["cost_usd"] for l in (self.out / "ledger.jsonl").read_text().splitlines())
        self.assertLessEqual(spent, 0.07)

    def test_one_rejected_prompt_does_not_stop_the_run_or_leak_key(self):
        FakeOpenRouter.bad_subject = "sleepy owl"
        code, so, se = self.gen()
        self.assertEqual(code, 0)
        self.assertEqual(len(list(self.out.glob("*.png"))), 3)
        self.assertIn("1 failed", so)
        self.assertIn("HTTP 400", so)
        everything = so + se + (self.out / "ledger.jsonl").read_text()
        self.assertNotIn(TEST_KEY, everything)

    def test_missing_key_is_a_clear_error(self):
        os.environ.pop("OPENROUTER_API_KEY")
        code, so, se = self.gen()
        self.assertIn("OPENROUTER_API_KEY", str(code) + se)
        self.assertFalse(self.out.exists())

    def test_dry_run_needs_no_key_and_makes_no_requests(self):
        os.environ.pop("OPENROUTER_API_KEY")
        code, so, se = self.run_cli(["generate", str(self.subjects), "-o", str(self.out), "--model", "fake/model",
                                     "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("4 images", so)
        self.assertEqual(FakeOpenRouter.seen, [])

    def test_variants_naming(self):
        self.gen("--variants", "2", "--max-images", "2")
        names = sorted(p.name for p in self.out.glob("*.png"))
        self.assertEqual(names, ["01_a-happy-fox_v1.png", "01_a-happy-fox_v2.png"])

    def test_models_listing(self):
        code, so, se = self.run_cli(["models", "fake/model"])
        self.assertEqual(code, 0)
        self.assertIn("$0.03/image", so)

    def test_ext_sniffing(self):
        self.assertEqual(gi.ext_for("image/svg+xml", b""), ".svg")
        self.assertEqual(gi.ext_for(None, b"\x89PNG\r\n\x1a\n...."), ".png")
        self.assertEqual(gi.ext_for(None, b"\xff\xd8\xff\xe0"), ".jpg")

    def test_price_hint_formats(self):
        self.assertEqual(gi.price_hint([{"billable": "output_image", "unit": "megapixel", "cost_usd": 0.03}]), "$0.03/megapixel")
        self.assertEqual(gi.price_hint([{"billable": "output_image", "unit": "image", "cost_usd": 0.041, "variant": "768"}]),
                         "$0.041/image (768)")

    def test_bakeoff_end_to_end(self):
        code, so, se = self.run_cli(["bakeoff", str(self.subjects), "--models", "fake/a,fake/b", "-o",
                                     str(self.out), "--count", "2", "--workers", "1", "--budget", "1"])
        self.assertEqual(code, 0, se)
        report = (self.out / "bakeoff_report.md").read_text()
        self.assertIn("fake/a", report)
        self.assertIn("fake/b", report)
        self.assertTrue((self.out / "contact_fake_a.png").exists())


if __name__ == "__main__":
    unittest.main()
