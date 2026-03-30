import logging
import os
import unittest
from unittest.mock import MagicMock, patch

from selenium.webdriver.common.by import By

from src.job import (
    classify_step4_error_text,
    ensure_final_checkbox_selected,
    extract_step4_error_text_from_html,
    format_timeout_window,
    get_manual_captcha_timeout_sec,
    make_fourth_step,
    notify_manual_captcha_required,
    wait_for_final_submission_result,
    wait_for_manual_captcha_solution,
)
from src.run_outcome import RunOutcome


class FakeElement:
    def __init__(
        self,
        *,
        text="",
        attributes=None,
        displayed=True,
        selected=False,
        raise_on_click=None,
        on_click=None,
    ):
        self.text = text
        self.attributes = attributes or {}
        self.displayed = displayed
        self.selected = selected
        self.raise_on_click = raise_on_click
        self.on_click = on_click
        self.clicked = 0
        self.children = {}

    def add_child(self, by, value, child):
        self.children.setdefault((by, value), []).append(child)
        return child

    def find_element(self, by, value):
        matches = self.find_elements(by, value)
        if not matches:
            raise LookupError(f"Element not found for {(by, value)}")
        return matches[0]

    def find_elements(self, by, value):
        return list(self.children.get((by, value), []))

    def get_attribute(self, name):
        return self.attributes.get(name)

    def get_dom_attribute(self, name):
        return self.attributes.get(name)

    def is_displayed(self):
        return self.displayed

    def is_selected(self):
        return self.selected

    def click(self):
        self.clicked += 1
        if self.raise_on_click:
            raise self.raise_on_click
        if self.on_click:
            self.on_click(self)


class FakeDriver:
    def __init__(self, final_forms=None, current_url="https://example.test/step4"):
        self.current_url = current_url
        self.final_forms = final_forms or []
        self.executed_scripts = []

    def execute_script(self, script, *args):
        self.executed_scripts.append((script, args))

        if "arguments[0].checked = true" in script:
            args[0].selected = True

    def find_elements(self, by, value):
        if by == By.ID and value == "mfa-form4":
            return list(self.final_forms)
        return []


class Step4HelpersTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test.step4")

    def test_extract_step4_error_text_from_fixture_html(self):
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "pagehtml_step4_error.html",
        )
        with open(fixture_path, encoding="utf-8") as handle:
            page_html = handle.read()

        error_text = extract_step4_error_text_from_html(page_html)

        self.assertEqual(error_text, "The verification code is incorrect.")

    def test_classify_step4_error_text_detects_captcha_failure(self):
        outcome = classify_step4_error_text("The verification code is incorrect.")

        self.assertEqual(outcome, RunOutcome.CAPTCHA_FAILED)

    def test_ensure_final_checkbox_selected_uses_wrapper_click(self):
        checkbox = FakeElement(attributes={"id": "personal-data"})
        wrapper_checkbox = FakeElement(
            attributes={"class": "form-checkbox"},
            on_click=lambda _: setattr(checkbox, "selected", True),
        )
        gdpr_wrapper = FakeElement()
        gdpr_wrapper.add_child(By.CLASS_NAME, "form-checkbox", wrapper_checkbox)

        final_form = FakeElement(attributes={"id": "mfa-form4"})
        final_form.add_child(By.ID, "personal-data", checkbox)
        final_form.add_child(By.ID, "gdpr", gdpr_wrapper)
        driver = FakeDriver([final_form])

        ensure_final_checkbox_selected(driver, final_form, self.logger)

        self.assertTrue(checkbox.is_selected())
        self.assertEqual(wrapper_checkbox.clicked, 1)

    def test_ensure_final_checkbox_selected_uses_js_fallback(self):
        checkbox = FakeElement(attributes={"id": "personal-data"})
        wrapper_checkbox = FakeElement(attributes={"class": "form-checkbox"})
        gdpr_wrapper = FakeElement()
        gdpr_wrapper.add_child(By.CLASS_NAME, "form-checkbox", wrapper_checkbox)

        final_form = FakeElement(attributes={"id": "mfa-form4"})
        final_form.add_child(By.ID, "personal-data", checkbox)
        final_form.add_child(By.ID, "gdpr", gdpr_wrapper)
        driver = FakeDriver([final_form])

        ensure_final_checkbox_selected(driver, final_form, self.logger)

        self.assertTrue(checkbox.is_selected())
        self.assertTrue(
            any("arguments[0].checked = true" in script for script, _ in driver.executed_scripts)
        )

    @patch("src.job.time.sleep", lambda *_: None)
    def test_wait_for_manual_captcha_solution_detects_new_token(self):
        with patch(
            "src.job.get_recaptcha_response_value",
            side_effect=["", "", "token-123"],
        ), patch("src.job.time.monotonic", side_effect=[0, 1, 2, 3]):
            token = wait_for_manual_captcha_solution(MagicMock(), timeout_sec=10)

        self.assertEqual(token, "token-123")

    @patch("src.job.time.sleep", lambda *_: None)
    def test_wait_for_manual_captcha_solution_times_out_without_token(self):
        with patch(
            "src.job.get_recaptcha_response_value",
            return_value="",
        ), patch("src.job.time.monotonic", side_effect=[0, 10, 10]):
            token = wait_for_manual_captcha_solution(MagicMock(), timeout_sec=10)

        self.assertIsNone(token)

    def test_notify_manual_captcha_required_sends_message_and_snapshot(self):
        driver = FakeDriver()
        with patch("src.job.asyncio.run") as run_mock, patch(
            "src.job.notify_bot_with_message", new=MagicMock(return_value=None)
        ), patch("src.job.make_screenshot") as screenshot_mock:
            notify_manual_captcha_required(driver, self.logger, attempt=1, timeout_sec=600)

        run_mock.assert_called_once()
        screenshot_mock.assert_called_once()
        self.assertIn("Manual captcha required", screenshot_mock.call_args.kwargs["caption"])

    @patch("src.job.time.sleep", lambda *_: None)
    def test_wait_for_final_submission_result_detects_captcha_error(self):
        question = FakeElement(text="The verification code is incorrect.")
        notification = FakeElement()
        notification.add_child(By.CLASS_NAME, "text--question", question)
        final_form = FakeElement(attributes={"id": "mfa-form4"})
        final_form.add_child(By.CLASS_NAME, "info-notification", notification)
        driver = FakeDriver([final_form])

        outcome, error_text = wait_for_final_submission_result(driver, driver.current_url)

        self.assertEqual(outcome, RunOutcome.CAPTCHA_FAILED)
        self.assertEqual(error_text, "The verification code is incorrect.")

    @patch("src.job.time.sleep", lambda *_: None)
    def test_wait_for_final_submission_result_detects_generic_error(self):
        question = FakeElement(text="Fill in empty fields")
        notification = FakeElement()
        notification.add_child(By.CLASS_NAME, "text--question", question)
        final_form = FakeElement(attributes={"id": "mfa-form4"})
        final_form.add_child(By.CLASS_NAME, "info-notification", notification)
        driver = FakeDriver([final_form])

        outcome, error_text = wait_for_final_submission_result(driver, driver.current_url)

        self.assertEqual(outcome, RunOutcome.FAILED)
        self.assertEqual(error_text, "Fill in empty fields")

    def test_make_fourth_step_submits_after_manual_captcha_solve(self):
        approve_button = FakeElement(text="Approve")
        final_form = FakeElement(attributes={"id": "mfa-form4"})
        final_form.add_child(By.CLASS_NAME, "btn-next-step", approve_button)
        driver = FakeDriver([final_form])
        wait_results = [final_form, final_form, approve_button]

        def fake_wait(*args, **kwargs):
            del args, kwargs

            class _Wait:
                def until(self, condition):
                    del condition
                    return wait_results.pop(0)

            return _Wait()

        with patch("src.job.WebDriverWait", side_effect=fake_wait), patch(
            "src.job.get_captcha_provider", return_value="manual"
        ), patch("src.job.get_manual_captcha_timeout_sec", return_value=600), patch(
            "src.job.ensure_final_checkbox_selected"
        ), patch(
            "src.job.has_recaptcha_widget", return_value=True
        ), patch(
            "src.job.notify_manual_captcha_required"
        ), patch(
            "src.job.wait_for_manual_captcha_solution", return_value="token-123"
        ), patch(
            "src.job.wait_for_final_submission_result",
            return_value=(RunOutcome.APPROVED, None),
        ), patch("src.job.make_screenshot"):
            outcome = make_fourth_step(driver, self.logger)

        self.assertEqual(outcome, RunOutcome.APPROVED)
        self.assertEqual(approve_button.clicked, 1)

    def test_make_fourth_step_returns_captcha_failed_when_manual_timeout_expires(self):
        final_form = FakeElement(attributes={"id": "mfa-form4"})
        driver = FakeDriver([final_form])
        wait_results = [final_form, final_form]

        def fake_wait(*args, **kwargs):
            del args, kwargs

            class _Wait:
                def until(self, condition):
                    del condition
                    return wait_results.pop(0)

            return _Wait()

        with patch("src.job.WebDriverWait", side_effect=fake_wait), patch(
            "src.job.get_captcha_provider", return_value="manual"
        ), patch("src.job.get_manual_captcha_timeout_sec", return_value=600), patch(
            "src.job.ensure_final_checkbox_selected"
        ), patch(
            "src.job.has_recaptcha_widget", return_value=True
        ), patch(
            "src.job.notify_manual_captcha_required"
        ), patch(
            "src.job.wait_for_manual_captcha_solution", return_value=None
        ), patch("src.job.make_screenshot"), patch(
            "src.job.notify_step4_failure"
        ) as notify_failure_mock:
            outcome = make_fourth_step(driver, self.logger)

        self.assertEqual(outcome, RunOutcome.CAPTCHA_FAILED)
        notify_failure_mock.assert_called_once()

    def test_format_timeout_window_formats_minutes(self):
        self.assertEqual(format_timeout_window(600), "10m")

    def test_get_manual_captcha_timeout_sec_validates_value(self):
        with patch.dict(os.environ, {"CAPTCHA_MANUAL_TIMEOUT_SEC": "0"}, clear=False):
            with self.assertRaises(ValueError):
                get_manual_captcha_timeout_sec()


if __name__ == "__main__":
    unittest.main()

