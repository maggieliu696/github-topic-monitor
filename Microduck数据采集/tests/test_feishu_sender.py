import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "feishu" / "send_digest.py"
SPEC = importlib.util.spec_from_file_location("feishu_sender", SOURCE)
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class FeishuSenderTests(unittest.TestCase):
    def test_card_keeps_public_links_and_removes_local_targets(self):
        source = "# 日报\n\n[公开](https://github.com/example/repo) [本地](</tmp/日报.md>)"
        content = S.card_payload(source)["card"]["elements"][0]["content"]
        self.assertIn("[公开](https://github.com/example/repo)", content)
        self.assertIn("本地", content)
        self.assertNotIn("/tmp/日报.md", content)

    def test_signature_is_stable(self):
        self.assertEqual(S.signature("1599360473", "secret"), S.signature("1599360473", "secret"))
        self.assertNotEqual(S.signature("1599360473", "secret"), S.signature("1599360474", "secret"))

    def test_only_official_webhook_is_allowed(self):
        S.validate_webhook("https://open.feishu.cn/open-apis/bot/v2/hook/example")
        for value in ["http://open.feishu.cn/open-apis/bot/v2/hook/x", "https://example.com/open-apis/bot/v2/hook/x", "https://open.feishu.cn/other"]:
            with self.assertRaises(ValueError):
                S.validate_webhook(value)


if __name__ == "__main__":
    unittest.main()
