import asyncio
import os
from datetime import date, datetime
from logging import Logger

import telegram
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from chrome_with_cleanup import ChromeWithFullCleanup


def process(logger: Logger, driver: WebDriver):
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
            make_third_step(local_driver, logger)
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


def make_third_step(driver: WebDriver, logger: Logger):
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

        step_3_next = WebDriverWait(driver, 10).until(
            expected_conditions.visibility_of_element_located((By.ID, "step3-next-btn"))
        )
        step_3_next_btn = step_3_next.find_element(By.CLASS_NAME, "btn-next-step")

        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable(step_3_next_btn)
        ).click()

        make_screenshot(driver, logger)
    else:
        logger.info("Date was not chosen")


def get_prefer_dates():
    dates_range = os.environ.get("PREFER_DATES")

    if dates_range is None:
        raise ValueError("Dates range is None")

    date_strings = dates_range.split(",")

    return date.fromisoformat(date_strings[0]), date.fromisoformat(date_strings[1])


def make_screenshot(driver: WebDriver, logger: Logger):
    screenshot = driver.get_screenshot_as_png()
    html = driver.page_source.encode("utf-8")

    asyncio.run(notify_bot_with_screenshot(screenshot, logger, html))


async def notify_bot_with_screenshot(
    screenshot: bytes, logger: Logger, additional_file: bytes | None = None
):
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
        chat_id=bot_user_id, photo=screenshot, caption=f"screen_{datetime.now()}"
    )
    if additional_file:
        await bot.send_document(
            chat_id=bot_user_id, document=additional_file, filename="pagehtml.html"
        )


async def notify_bot_with_message(message: str, logger: Logger):
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

            if col_class is str and "cal-active" in col_class:
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

        process(logger, driver)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        logger.info("Quit")
