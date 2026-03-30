import os
import unittest
from unittest.mock import patch

from src.job import get_captcha_provider, get_manual_captcha_timeout_sec


class ManualCaptchaConfigTests(unittest.TestCase):
    def test_get_captcha_provider_defaults_to_manual(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_captcha_provider(), "manual")

    def test_get_captcha_provider_normalizes_env_value(self):
        with patch.dict(os.environ, {"CAPTCHA_PROVIDER": " Manual "}, clear=False):
            self.assertEqual(get_captcha_provider(), "manual")

    def test_get_manual_captcha_timeout_uses_default_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_manual_captcha_timeout_sec(), 600)

    def test_get_manual_captcha_timeout_reads_env_value(self):
        with patch.dict(
            os.environ,
            {"CAPTCHA_MANUAL_TIMEOUT_SEC": "120"},
            clear=False,
        ):
            self.assertEqual(get_manual_captcha_timeout_sec(), 120)


if __name__ == "__main__":
    unittest.main()
