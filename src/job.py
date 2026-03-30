import asyncio
import html
import os
import re
import time
from datetime import date, datetime
from logging import Logger

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select, WebDriverWait

from chrome_with_cleanup import ChromeWithFullCleanup
from run_outcome import RunOutcome


def process(logger: Logger, driver: WebDriver) -> RunOutcome:
    with ChromeWithFullCleanup(
        logger=logger,
        driver=driver,
    ) as local_driver:
        try:
            local_driver.switch_to.new_window("tab")
            local_driver.get("https://pieraksts.mfa.gov.lv/en/moscow/index")
            logger.info(f"Page was open: {local_driver.title}")
            make_first_step(local_driver, logger)
            make_second_step(local_driver, logger)
            if make_third_step(local_driver, logger):
                return make_fourth_step(local_driver, logger)
            return RunOutcome.NO_SLOT
        except Exception as e:
            raise e
        finally:
            logger.info("Quit")

            if bool(os.getenv("SCREENSHOT_AFTER", 0)):
                make_screenshot(local_driver, logger)


def make_first_step(driver: WebDriver, logger: Logger):
    form = WebDriverWait(driver, 10).until(
        expected_conditions.presence_of_element_located((By.TAG_NAME, "form"))
    )

    name_input = form.find_element(By.ID, "Persons[0][first_name]")

    logger.info(f"name input discovered: {name_input.get_dom_attribute('id')}")

    surname_input = form.find_element(By.ID, "Persons[0][last_name]")

    logger.info(f"surname input discovered: {surname_input.get_dom_attribute('id')}")

    email_input = form.find_element(By.ID, "e_mail")

    logger.info(f"email input discovered: {email_input.get_dom_attribute('id')}")

    email_repeat_input = form.find_element(By.ID, "e_mail_repeat")

    logger.info(
        f"email repeat input discovered: {email_repeat_input.get_dom_attribute('id')}"
    )

    phone_input = form.find_element(By.ID, "phone")

    logger.info(f"phone input discovered: {phone_input.get_dom_attribute('id')}")

    first_step_submit_btn = form.find_element(By.ID, "step1-next-btn").find_element(
        By.TAG_NAME, "button"
    )

    logger.info(
        f"first step submit button discovered: {first_step_submit_btn.get_dom_attribute('class')}"
    )

    user_data = os.getenv("USER_FORM_DATA")

    if user_data is None:
        raise ValueError("USER_FORM_DATA environment variable is not set")

    name, surname, email, phone = user_data.split(",")

    name_input.clear()
    name_input.send_keys(name)

    surname_input.clear()
    surname_input.send_keys(surname)

    email_input.clear()
    email_input.send_keys(email)

    email_repeat_input.clear()
    email_repeat_input.send_keys(email)

    phone_input.clear()
    phone_input.send_keys(phone)

    WebDriverWait(driver, 10).until(
        expected_conditions.element_to_be_clickable(first_step_submit_btn)
    ).click()

    logger.info(f"located to {driver.current_url}")


def make_second_step(driver: WebDriver, logger: Logger):
    logger.info("Starting second step")

    actions = ActionChains(driver)

    WebDriverWait(driver, 10).until(
        expected_conditions.presence_of_element_located((By.ID, "mfa-form2"))
    )

    second_step_form = driver.find_element(By.ID, "mfa-form2")

    logger.info("Second step form found")

    select = second_step_form.find_element(
        By.XPATH, '//div/div/section/div/div/p[text()="Select service"]'
    )

    logger.info(f"second step select discovered: {select.get_attribute('class')}")

    WebDriverWait(driver, 10).until(
        expected_conditions.element_to_be_clickable(select)
    ).click()

    visa_option = second_step_form.find_element(
        By.XPATH,
        '//div/div/section/div/div[contains(@class, "services--wrapper")]/div/label[text()="Processing a visa"]',
    )
    actions.scroll_to_element(visa_option).perform()

    logger.info(f"visa option discovered: {visa_option.text}")

    WebDriverWait(driver, 10).until(
        expected_conditions.element_to_be_clickable(visa_option)
    ).click()

    description = second_step_form.find_element(
        By.XPATH,
        '//div/div/section/div/div[contains(@class, "services--wrapper")]/section[@class="description active"]',
    )

    logger.info(
        f"description element was discovered: {description.get_attribute('class')}"
    )

    driver.execute_script(
        "arguments[0].scrollTo(0, arguments[0].scrollHeight);", description
    )

    confirmation = description.find_element(By.CLASS_NAME, "form-checkbox")

    logger.info(f"confirmation check discovered: {confirmation.get_attribute('class')}")

    actions.move_to_element(confirmation)

    WebDriverWait(driver, 5).until(
        expected_conditions.element_to_be_clickable(confirmation)
    ).click()

    add_button = description.find_element(By.CLASS_NAME, "description-button")

    logger.info(f"add button discovered: {add_button.text}")

    WebDriverWait(driver, 10).until(
        expected_conditions.element_to_be_clickable(add_button)
    ).click()

    next_step_button = second_step_form.find_element(By.CLASS_NAME, "btn-next-step")

    logger.info(f"next step button discovered: {next_step_button.text}")

    WebDriverWait(driver, 10).until(
        expected_conditions.element_to_be_clickable(next_step_button)
    ).click()


def make_third_step(driver: WebDriver, logger: Logger) -> bool:
    prefer_dates = get_prefer_dates()

    logger.info(f"prefer_dates: {prefer_dates}")

    calendar = WebDriverWait(driver, 10).until(
        expected_conditions.presence_of_element_located((By.ID, "calendar-daygrid"))
    )

    logger.info(f"calendar discovered: {calendar.get_attribute('id')}")

    next_month_button = driver.find_element(By.CLASS_NAME, "calendar-next")

    logger.info(
        f"next month button discovered: {next_month_button.get_attribute('aria-label')}"
    )

    WebDriverWait(calendar, 10).until(
        expected_conditions.presence_of_element_located((By.CLASS_NAME, "cal-today"))
    )

    calendar_rows = calendar.find_elements(By.TAG_NAME, "tr")

    chosen_date = find_date_in_rows(calendar_rows, prefer_dates, logger)

    if chosen_date is None:
        logger.info("Available date is not found on first page, trying next page")

        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable(next_month_button)
        ).click()

        WebDriverWait(calendar, 10).until_not(
            expected_conditions.presence_of_element_located(
                (By.CLASS_NAME, "cal-today")
            )
        )

        next_calendar = WebDriverWait(driver, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "calendar-daygrid"))
        )

        logger.info(f"Calendar discovered: {next_calendar.get_attribute('id')}")

        next_calendar_rows = next_calendar.find_elements(By.TAG_NAME, "tr")

        chosen_date = find_date_in_rows(next_calendar_rows, prefer_dates, logger)

    if chosen_date is not None:
        logger.info("Available date was found!")

        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable(chosen_date)
        ).click()

        # Select preferred time (after 12:00 if available, otherwise earlier)
        try:
            choose_time_after_noon(driver, logger, min_hour=12)
        except Exception as e:
            # If time select is not found / not ready, continue with default time
            logger.warning(f"Could not select time automatically: {e}")

        step_3_next = WebDriverWait(driver, 10).until(
            expected_conditions.visibility_of_element_located((By.ID, "step3-next-btn"))
        )
        step_3_next_btn = step_3_next.find_element(By.CLASS_NAME, "btn-next-step")

        make_screenshot(driver, logger, "Time selected")

        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable(step_3_next_btn)
        ).click()

        WebDriverWait(driver, 10).until(
            expected_conditions.invisibility_of_element(step_3_next_btn)
        )

        make_screenshot(driver, logger, "Step 3 Successed")
        return True
    else:
        logger.info("Date was not chosen")
        return False


def make_fourth_step(driver: WebDriver, logger: Logger) -> RunOutcome:
    logger.info("Starting fourth step")

    try:
        final_form = WebDriverWait(driver, 10).until(
            expected_conditions.presence_of_element_located((By.ID, "mfa-form4"))
        )
        logger.info(f"Fourth step form found: {final_form.get_attribute('id')}")
        captcha_provider = get_captcha_provider()
        if captcha_provider != "manual":
            raise RuntimeError(
                f"Unsupported CAPTCHA_PROVIDER value: {captcha_provider}. Only 'manual' is supported."
            )

        final_page_url = driver.current_url
        manual_timeout_sec = get_manual_captcha_timeout_sec()

        for attempt in range(1, 3):
            final_form = WebDriverWait(driver, 10).until(
                expected_conditions.presence_of_element_located((By.ID, "mfa-form4"))
            )

            ensure_final_checkbox_selected(driver, final_form, logger)

            if attempt == 1:
                make_screenshot(driver, logger, "Checkbox selected")

            if has_recaptcha_widget(final_form):
                previous_token = ""
                if attempt > 1:
                    previous_token = get_recaptcha_response_value(driver)
                notify_manual_captcha_required(
                    driver,
                    logger,
                    attempt=attempt,
                    timeout_sec=manual_timeout_sec,
                )
                solved_token = wait_for_manual_captcha_solution(
                    driver,
                    timeout_sec=manual_timeout_sec,
                    previous_token=previous_token,
                )

                if not solved_token:
                    error_text = (
                        "Manual captcha was not solved within "
                        f"{format_timeout_window(manual_timeout_sec)}"
                    )
                    logger.warning(error_text)
                    notify_step4_failure(logger, error_text)
                    make_screenshot(driver, logger, caption=error_text)
                    return RunOutcome.CAPTCHA_FAILED

            approve_button = final_form.find_element(By.CLASS_NAME, "btn-next-step")
            logger.info(f"approve button discovered: {approve_button.text}")

            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", approve_button
            )
            WebDriverWait(driver, 10).until(
                expected_conditions.element_to_be_clickable(approve_button)
            ).click()

            logger.info("Approve button clicked on attempt %s", attempt)
            make_screenshot(driver, logger, f"Approve button clicked (attempt {attempt})")

            outcome, error_text = wait_for_final_submission_result(driver, final_page_url)

            if outcome == RunOutcome.APPROVED:
                logger.info("Final submission progressed away from step 4")
                make_screenshot(
                    driver,
                    logger,
                    caption=f"Approve succeeded at {datetime.now():%Y-%m-%d %H:%M:%S}",
                )
                return outcome

            logger.warning(
                "Fourth step stayed on page after attempt %s: %s",
                attempt,
                error_text or outcome.value,
            )

            if outcome == RunOutcome.CAPTCHA_FAILED and attempt == 1:
                logger.warning(
                    "Captcha verification failed after manual solve; waiting for a refreshed captcha"
                )
                continue

            notify_step4_failure(logger, error_text or outcome.value)
            make_screenshot(
                driver,
                logger,
                caption=f"Fourth step failed: {error_text or outcome.value}",
            )
            return outcome

        raise RuntimeError("Fourth step finished without returning an outcome")
    except Exception as error:
        if isinstance(error, TimeoutException):
            logger.error(f"Fourth step timed out: {error}")
        else:
            logger.error("Fourth step failed with error: %s", error)

        notify_step4_failure(logger, str(error))
        make_screenshot(driver, logger)
        raise


def ensure_final_checkbox_selected(
    driver: WebDriver, final_form: WebElement, logger: Logger
):
    checkbox = final_form.find_element(By.ID, "personal-data")
    logger.info(f"final step checkbox discovered: {checkbox.get_dom_attribute('id')}")

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)

    if checkbox.is_selected():
        logger.info("Final step checkbox already selected")
        return

    try:
        checkbox.click()
    except Exception as checkbox_error:
        logger.warning("Direct checkbox click failed: %s", checkbox_error)

    if checkbox.is_selected():
        logger.info("Final step checkbox selected via direct click")
        return

    try:
        gdpr_wrapper = final_form.find_element(By.ID, "gdpr")
        confirmation = gdpr_wrapper.find_element(By.CLASS_NAME, "form-checkbox")
        logger.info(
            "Falling back to checkbox wrapper click: %s",
            confirmation.get_attribute("class"),
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", confirmation
        )
        confirmation.click()
    except Exception as confirmation_error:
        logger.warning("Checkbox wrapper click failed: %s", confirmation_error)

    if checkbox.is_selected():
        logger.info("Final step checkbox selected via wrapper click")
        return

    logger.warning("Falling back to JS checkbox selection")
    driver.execute_script(
        """
        arguments[0].checked = true;
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """,
        checkbox,
    )

    if not checkbox.is_selected():
        raise RuntimeError("Final step checkbox could not be selected")

    logger.info("Final step checkbox confirmed")


def has_recaptcha_widget(final_form: WebElement) -> bool:
    return bool(final_form.find_elements(By.ID, "recaptcha-v2"))


def get_captcha_provider() -> str:
    provider = (os.getenv("CAPTCHA_PROVIDER") or "manual").strip().lower()
    return provider or "manual"


def get_manual_captcha_timeout_sec() -> int:
    timeout_sec = int(os.getenv("CAPTCHA_MANUAL_TIMEOUT_SEC", "600"))
    if timeout_sec <= 0:
        raise ValueError("CAPTCHA_MANUAL_TIMEOUT_SEC must be greater than 0")
    return timeout_sec


def format_timeout_window(timeout_sec: int) -> str:
    minutes, seconds = divmod(timeout_sec, 60)
    if minutes and seconds:
        return f"{minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m"
    return f"{seconds}s"


def notify_manual_captcha_required(
    driver: WebDriver,
    logger: Logger,
    attempt: int,
    timeout_sec: int,
):
    if attempt == 1:
        message = (
            "Manual reCAPTCHA required on step 4.\n\n"
            "Open the visible Chrome window on this machine, solve the captcha there, "
            f"and wait up to {format_timeout_window(timeout_sec)}. "
            "The bot will click Approve automatically."
        )
        caption = "Manual captcha required"
    else:
        message = (
            "Step 4 needs the captcha to be solved again.\n\n"
            "Please refresh or solve the captcha again in the visible Chrome window. "
            f"The bot will keep waiting for up to {format_timeout_window(timeout_sec)} "
            "before the second submit attempt."
        )
        caption = "Manual captcha required again"

    asyncio.run(notify_bot_with_message(message, logger))
    make_screenshot(driver, logger, caption=caption)


def get_recaptcha_response_value(driver: WebDriver) -> str:
    final_forms = driver.find_elements(By.ID, "mfa-form4")
    if not final_forms:
        return ""

    try:
        response_field = final_forms[0].find_element(By.ID, "g-recaptcha-response")
    except Exception:
        return ""

    return (
        response_field.get_attribute("value")
        or response_field.get_attribute("innerHTML")
        or response_field.text
        or ""
    ).strip()


def wait_for_manual_captcha_solution(
    driver: WebDriver,
    timeout_sec: float,
    poll_interval_sec: float = 0.5,
    previous_token: str = "",
) -> str | None:
    deadline = time.monotonic() + timeout_sec
    previous_token = (previous_token or "").strip()

    while time.monotonic() < deadline:
        current_token = get_recaptcha_response_value(driver)
        if current_token and current_token != previous_token:
            return current_token

        time.sleep(poll_interval_sec)

    current_token = get_recaptcha_response_value(driver)
    if current_token and current_token != previous_token:
        return current_token

    return None


def wait_for_final_submission_result(
    driver: WebDriver,
    final_page_url: str,
    timeout_sec: float = 20,
    poll_interval_sec: float = 0.5,
) -> tuple[RunOutcome, str | None]:
    deadline = time.monotonic() + timeout_sec

    while time.monotonic() < deadline:
        if has_left_final_step(driver, final_page_url):
            return RunOutcome.APPROVED, None

        error_text = get_visible_step4_error_text(driver)
        if error_text:
            return classify_step4_error_text(error_text), error_text

        time.sleep(poll_interval_sec)

    if has_left_final_step(driver, final_page_url):
        return RunOutcome.APPROVED, None

    error_text = get_visible_step4_error_text(driver)
    if error_text:
        return classify_step4_error_text(error_text), error_text

    raise TimeoutException("Timed out waiting for the fourth-step submission result")


def get_visible_step4_error_text(driver: WebDriver) -> str | None:
    for final_form in driver.find_elements(By.ID, "mfa-form4"):
        if not final_form.is_displayed():
            continue

        for notification in final_form.find_elements(By.CLASS_NAME, "info-notification"):
            if not notification.is_displayed():
                continue

            try:
                question = notification.find_element(By.CLASS_NAME, "text--question")
            except Exception:
                continue

            text = normalize_step4_error_text(question.text)
            if text:
                return text

    return None


def extract_step4_error_text_from_html(page_html: str) -> str | None:
    match = re.search(
        r'<div[^>]*class="[^"]*info-notification[^"]*"[^>]*>.*?<p[^>]*class="[^"]*text--question[^"]*"[^>]*>(.*?)</p>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None

    text = re.sub(r"<[^>]+>", "", match.group(1))
    return normalize_step4_error_text(html.unescape(text))


def normalize_step4_error_text(error_text: str | None) -> str | None:
    if error_text is None:
        return None

    normalized = " ".join(error_text.split()).strip()
    return normalized or None


def classify_step4_error_text(error_text: str) -> RunOutcome:
    normalized = (error_text or "").lower()
    if "verification code is incorrect" in normalized:
        return RunOutcome.CAPTCHA_FAILED
    return RunOutcome.FAILED


def notify_step4_failure(logger: Logger, error_text: str):
    if not error_text:
        return

    try:
        asyncio.run(notify_bot_with_message(f"Fourth step failed: {error_text}", logger))
    except Exception as notification_error:
        logger.error("Failed to notify step 4 failure: %s", notification_error)


def choose_time_after_noon(driver: WebDriver, logger: Logger, min_hour: int = 12):
    logger.info("Trying to select a preferred time...")

    time_re = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")

    def parse_select(sel_el):
        option_els = sel_el.find_elements(By.TAG_NAME, "option")
        parsed = []
        for opt in option_els:
            text = (opt.text or "").strip()
            m = time_re.match(text)
            if not m:
                continue
            hour = int(m.group(1))
            minute = int(m.group(2))
            parsed.append((hour, minute, text))
        return parsed

    def locate_time_select(drv: WebDriver):
        preferred_selectors = [
            "select[name='ServiceGroups[0][visit_time]']",
            "#services select.time",
            "select.time",
        ]

        for css in preferred_selectors:
            for sel in drv.find_elements(By.CSS_SELECTOR, css):
                try:
                    parsed = parse_select(sel)
                except Exception:
                    continue
                if parsed:
                    return sel, parsed

        # Fallback: any <select> that contains HH:MM options
        for sel in drv.find_elements(By.TAG_NAME, "select"):
            try:
                parsed = parse_select(sel)
            except Exception:
                continue
            if parsed:
                return sel, parsed

        return None, None

    sel, parsed = WebDriverWait(driver, 15).until(lambda d: locate_time_select(d))

    if sel is None or parsed is None:
        return

    # Prefer afternoon times; fallback to earliest time.
    afternoon = sorted(
        [t for t in parsed if t[0] >= min_hour], key=lambda x: (x[0], x[1])
    )
    chosen = (
        afternoon[0] if afternoon else sorted(parsed, key=lambda x: (x[0], x[1]))[0]
    )

    chosen_text = chosen[2]
    logger.info(f"Selecting time option: {chosen_text}")

    Select(sel).select_by_visible_text(chosen_text)


def has_left_final_step(driver: WebDriver, final_page_url: str) -> bool:
    if driver.current_url != final_page_url:
        return True

    final_forms = driver.find_elements(By.ID, "mfa-form4")

    if not final_forms:
        return True

    return not final_forms[0].is_displayed()


def get_prefer_dates():
    dates_range = os.environ.get("PREFER_DATES")

    if dates_range is None:
        raise ValueError("Dates range is None")

    date_strings = dates_range.split(",")

    return date.fromisoformat(date_strings[0]), date.fromisoformat(date_strings[1])


def make_screenshot(driver: WebDriver, logger: Logger, caption: str | None = None):
    screenshot = driver.get_screenshot_as_png()
    html = driver.page_source.encode("utf-8")

    asyncio.run(notify_bot_with_screenshot(screenshot, logger, html, caption))


async def notify_bot_with_screenshot(
    screenshot: bytes,
    logger: Logger,
    additional_file: bytes | None = None,
    caption: str | None = None,
):
    import telegram

    bot_cred = os.environ.get("EMBASSY_BOT")
    bot_user_id = os.environ.get("BOT_USER_ID")

    if bot_cred is None:
        logger.error("Bot credentials is None")
        return

    if bot_user_id is None:
        logger.error("Bot user ID is None")
        return

    bot = telegram.Bot(bot_cred)
    await bot.send_photo(
        chat_id=bot_user_id,
        photo=screenshot,
        caption=caption or f"screen_{datetime.now()}",
    )
    if additional_file:
        await bot.send_document(
            chat_id=bot_user_id, document=additional_file, filename="pagehtml.html"
        )


async def notify_bot_with_message(message: str, logger: Logger):
    import telegram

    bot_cred = os.environ.get("EMBASSY_BOT")
    bot_user_id = os.environ.get("BOT_USER_ID")

    if bot_cred is None:
        logger.error("Bot credentials is None")
        return

    if bot_user_id is None:
        logger.error("Bot user ID is None")
        return

    bot = telegram.Bot(bot_cred)
    await bot.send_message(chat_id=bot_user_id, text=message)


def find_date_in_rows(
    rows: list[WebElement], prefer_dates: tuple[date, date], logger: Logger
) -> WebElement | None:
    chosen_date: WebElement | None = None
    available_dates = set()

    logger.info(f"Rows count is {len(rows)}")

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")

        logger.info(f"Cols count is {len(cols)}")

        for col in cols:
            col_class = col.get_attribute("class")
            col_date = col.get_attribute("data-date")

            logger.info(f"Class of a col is {col_class}")

            if col_date is None or col_date == "":
                logger.error("ColDate is None or empty")
                continue

            current_date = datetime.strptime(col_date, "%Y-%m-%d").date()

            logger.info(f"Date of a col is {current_date}")

            if current_date < prefer_dates[0]:
                logger.info(f"Date {current_date} is less than {prefer_dates[0]}")

            if current_date > prefer_dates[1]:
                logger.info(f"Date {current_date} is greater than {prefer_dates[1]}")

            if col_class is not None and "cal-active" in col_class:
                available_dates.add(current_date)

                logger.info(f"Available date of a col is {current_date}")

                if current_date >= prefer_dates[0] and current_date <= prefer_dates[1]:
                    logger.info(f"Date was found - {col_date}")
                    chosen_date = col

                    break

        if chosen_date is not None:
            break

    if len(available_dates) > 0:
        logger.info(f"Available was - {available_dates}")
        asyncio.run(
            notify_bot_with_message(f"Available was - {available_dates}", logger)
        )

    return chosen_date


def job_func(logger: Logger, driver: WebDriver):
    try:
        logger.info("I am here.")

        outcome = process(logger, driver)
        logger.info("Run outcome: %s", outcome.value)
        return outcome
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return RunOutcome.FAILED
    finally:
        logger.info("Quit")
