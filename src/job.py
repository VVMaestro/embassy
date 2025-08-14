from logging import Logger
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.action_chains import ActionChains

def process(logger: Logger):
    driver: WebDriver | None = None

    try:
        # Опции Chrome для headless-режима
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Безголовый режим
        chrome_options.add_argument("--no-sandbox")  # Требуется для запуска в контейнерах/серверах
        chrome_options.add_argument("--disable-dev-shm-usage")  # Для избежания ошибок памяти

        # Путь к ChromeDriver (уточните путь на вашем сервере)
        logger.debug('\nУстанавливаю путь до chromedriver\n')

        # Инициализация драйвера
        driver = webdriver.Chrome(options=chrome_options)
        actions = ActionChains(driver)
        driver.set_window_size(1920, 1080)

        prefer_dates = {'2025-8-16', '2025-8-17'}

        # Открытие страницы
        driver.get("https://pieraksts.mfa.gov.lv/en/moscow/index")

        logger.info(f"\nОткрыта страница: {driver.title}\n")
        logger.info(f"\nlocated to {driver.current_url}\n")

        form = driver.find_element(By.TAG_NAME, "form")

        name_input = form.find_element(By.ID, "Persons[0][first_name]")

        logger.info(f"\nname input discovered: {name_input.get_dom_attribute('id')}\n")

        surname_input = form.find_element(By.ID, "Persons[0][last_name]")

        logger.info(f"\nsurname input discovered: {surname_input.get_dom_attribute('id')}\n")

        email_input = form.find_element(By.ID, "e_mail")

        logger.info(f"\nemail input discovered: {email_input.get_dom_attribute('id')}\n")

        email_repeat_input = form.find_element(By.ID, "e_mail_repeat")

        logger.info(f"\nemail repeat input discovered: {email_repeat_input.get_dom_attribute('id')}\n")

        phone_input = form.find_element(By.ID, "phone")

        logger.info(f"\nphone input discovered: {phone_input.get_dom_attribute('id')}\n")

        first_step_submit_btn = form.find_element(By.ID, "step1-next-btn").find_element(By.TAG_NAME, "button")

        logger.info(f"\nfirst step submit button discovered: {first_step_submit_btn.get_dom_attribute('name')}\n")

        name_input.send_keys("Ирина")
        surname_input.send_keys("Панова")
        email_input.send_keys("bmaecmpo@gmail.com")
        email_repeat_input.send_keys("bmaecmpo@gmail.com")
        phone_input.send_keys("+79224757702")

        WebDriverWait(driver, 10).until(expected_conditions.element_to_be_clickable(first_step_submit_btn)).click()

        logger.info(f"\nlocated to {driver.current_url}\n")

        WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.ID, "mfa-form2")))

        second_step_form = driver.find_element(By.ID, "mfa-form2")

        select = second_step_form.find_element(By.XPATH, '//div/div/section/div/div/p[text()="Select service"]')

        logger.info(f"\nsecond step select discovered: {select.get_attribute('class')}\n")

        WebDriverWait(driver, 10).until(expected_conditions.element_to_be_clickable(select)).click()

        visa_option = second_step_form.find_element(By.XPATH, '//div/div/section/div/div[contains(@class, "services--wrapper")]/div/label[text()="Processing a visa"]')
        actions.scroll_to_element(visa_option).perform()

        logger.info(f"\nvisa option discovered: {visa_option.text}\n")

        WebDriverWait(driver, 10).until(expected_conditions.element_to_be_clickable(visa_option)).click()

        description = second_step_form.find_element(By.XPATH, '//div/div/section/div/div[contains(@class, "services--wrapper")]/section[@class="description active"]')

        logger.info(f"\ndescription element was discovered: {description.get_attribute('class')}\n")

        driver.execute_script('arguments[0].scrollTo(0, arguments[0].scrollHeight);', description)

        confirmation = description.find_element(By.CLASS_NAME, 'form-checkbox')

        logger.info(f"\nconfirmation check discovered: {confirmation.get_attribute('class')}\n")

        actions.move_to_element(confirmation)

        WebDriverWait(driver, 5).until(expected_conditions.element_to_be_clickable(confirmation)).click()

        add_button = description.find_element(By.CLASS_NAME, 'description-button')

        logger.info(f"\nadd button discovered: {add_button.text}\n")

        WebDriverWait(driver, 10).until(expected_conditions.element_to_be_clickable(add_button)).click()

        next_step_button = second_step_form.find_element(By.CLASS_NAME, 'btn-next-step')

        logger.info(f"\nnext step button discovered: {next_step_button.text}\n")

        WebDriverWait(driver, 10).until(expected_conditions.element_to_be_clickable(next_step_button)).click()

        calendar = (WebDriverWait(driver, 10)
            .until(expected_conditions.presence_of_element_located((By.ID, 'calendar-daygrid'))))

        logger.info(f"\ncalendar discovered: {calendar.get_attribute('id')}\n")

        next_month_button = driver.find_element(By.CLASS_NAME, 'calendar-next')

        logger.info(f"\nnext month button discovered: {next_month_button.get_attribute('aria-label')}\n")

        _today_point = WebDriverWait(calendar, 10).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, 'cal-today')))

        calendar_rows = calendar.find_elements(By.TAG_NAME, 'tr')

        chosen_date = find_date_in_rows(calendar_rows, prefer_dates, logger)

        if chosen_date is None:
            WebDriverWait(driver, 10).until(expected_conditions.element_to_be_clickable(next_step_button)).click()

            _today_point = WebDriverWait(calendar, 10).until(expected_conditions.presence_of_element_located((By.CLASS_NAME, 'cal-today')))

            calendar_rows = calendar.find_elements(By.TAG_NAME, 'tr')

            chosen_date = find_date_in_rows(calendar_rows, prefer_dates, logger)

        if chosen_date is not None:
            WebDriverWait(driver, 10).until(expected_conditions.element_to_be_clickable(chosen_date)).click()

            step_3_next = WebDriverWait(driver, 10).until(expected_conditions.visibility_of_element_located((By.ID, 'step3-next-btn')))
            step_3_next_btn = step_3_next.find_element(By.CLASS_NAME, 'btn-next-step')

            WebDriverWait(driver, 10).until(expected_conditions.element_to_be_clickable(step_3_next_btn)).click()

            driver.save_screenshot('test.png')

        else:
            logger.info(f"Date was not chosen")


    except Exception as e:
        raise e
    finally:
        if driver is not None:
            driver.quit()


def find_date_in_rows(rows: list[WebElement], prefer_dates: set[str], logger: Logger) -> WebElement | None:
    chosen_date: WebElement | None = None
    available_dates = set()

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, 'td')

        for col in cols:
            col_class = col.get_attribute('class')
            col_date = col.get_attribute('data-date')

            logger.info(f"Class of a col is {col_class}")

            if col_class == 'dot--grey':
                available_dates.add(col_date)
                logger.info(f"Date of a col is {col_date}")

                if col_date in prefer_dates:
                    logger.info(f"Date was found - {col_date}")
                    chosen_date = col

                    break

        if chosen_date is not None:
            break

    logger.info(f"Available was - {available_dates}")

    return chosen_date


def job_func(logger: Logger):
    try:
        logger.info('I am here.')

        process(logger)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        logger.info('Quit')