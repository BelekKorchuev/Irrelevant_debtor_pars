import os
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import psycopg2
from datetime import timedelta
# import logger
from logScript import logger

load_dotenv(dotenv_path='.env')

db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")

# Функция для подключения к базе данных PostgreSQL
def get_db_connection():
    try:
        connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        return connection
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}")
        return None

def save_in_db(data):
    try:
        conn = get_db_connection()
        # Создаем курсор
        cursor = conn.cursor()

        # SQL-запрос для вставки данных
        insert_query = """
            INSERT INTO irrelevant_debtor (
                дата, ссылка_сообщения, Полное_имя, должник_ссылка_ЕФРСБ, Инн_Должника
            ) VALUES (
                %s, %s, %s, %s, %s
            )
        """

        values = (
            data.get('дата'), data.get('сообщение_ссылка'), data.get('Полное_имя'), data.get('должник_ссылка'), data.get('ИНН')
        )

        # Выполняем запрос с передачей данных из словаря
        cursor.execute(insert_query, values)

        # Фиксируем изменения
        conn.commit()

        logger.info(f"Данные успешно добавлены в базу для {data['ИНН']}")
    except Exception as e:
        logger.error(f"Ошибка вставки данных в базу для {data['ИНН']}: {e}")
        conn.rollback()
        return {'ИНН': {data.get('ИНН')},
                'Должник ссылка': data.get('должник_ссылка'),
                'Причина': 'Такой должник уже есть или другая ошибка'}
    finally:
        cursor.close()
        conn.close()  # Закрытие соединения

# Получаем список всех дней между начальной и конечной датами
def get_dates_range(start_date, end_date):
    current_date = start_date
    dates = []
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    return dates

def choose_act_type(driver, act_type):
    try:
        select_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_cphBody_ddlCourtDecisionType")))
        select = Select(select_element)
        select.select_by_visible_text(act_type)
        logger.info(f'Выбрал тип акта: {act_type}')
    except Exception as e:
        logger.error(f'не получилось выбрать тип акта: {e}')

def select_date_range(driver, current_date):
    try:
        # нужно в интерфейсе принимать даты которые пользователь введет
        begin_date = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_cphBody_cldrBeginDate_tbSelectedDate")))
        begin_date.clear()
        begin_date.send_keys(current_date.strftime("%d.%m.%Y"))

        time.sleep(2)

        end_date = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ctl00_cphBody_cldrEndDate_tbSelectedDate")))
        end_date.clear()
        end_date.send_keys(current_date.strftime("%d.%m.%Y"))
    except Exception as e:
        logger.error(f'не получилось выбрать дату: {e}')

def message_type_selecter(driver, current_date, act_type):
    try:
        link = "https://old.bankrot.fedresurs.ru/Messages.aspx"

        try:
            driver.get(link)
        except WebDriverException as e:
            logger.error(f'не получилось открыть ссылку в message_type_selecter: {e}')
            return None

        search_message_type = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.ID, 'ctl00_cphBody_mdsMessageType_tbSelectedText')))
        search_message_type.click()

        time.sleep(3)

        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@src, 'MessageTypeSelect')]")))
        logger.info('переключился на iframe')

        time.sleep(3)

        message_type = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="ctl00_BodyPlaceHolder_MessageTypeTree"]/ul/li[1]/div/span[2]')))
        message_type.click()
        logger.info('кликнул на кнопуку сообщения ')

        time.sleep(3)

        driver.switch_to.default_content()
        logger.info('переключился на основную окошку ')

        choose_act_type(driver, act_type)

        select_date_range(driver, current_date)

        # Ожидание и клик по кнопке "Поиск"
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_cphBody_ibMessagesSearch")))
        search_button.click()
        logger.info('кликнул на кнопуку поиск в главном окошке ')

    except Exception as e:
        logger.error(f'Не получилось выбрать тип акта: {e}')
        return None

def     message_parsing(driver, messages):
    try:
        driver.execute_script(f"window.open('');")

        for act in messages:
            data = {}
            url = act['сообщение_ссылка']
            logger.info(f'Переход по ссылке: {url}')

            # Открываем новую вкладку
            new_tab = driver.window_handles[-1]
            driver.switch_to.window(new_tab)

            driver.get(url)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'red_small'))
            )
            # Подождем несколько секунд, чтобы страница полностью загрузилась
            time.sleep(2)

            # Получение HTML-кода страницы
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Основная информация
            table_main = soup.find('table', class_='headInfo')
            if table_main:
                rows = table_main.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        field = cells[0].text.strip()
                        value = cells[1].text.strip()
                        data[field] = value

            # Данные о должнике
            debtor_fl_name = None
            debtor_ul_name = None
            debtor_section = soup.find('div', string="Должник")
            if debtor_section:
                debtor_table = debtor_section.find_next('table')
                if debtor_table:
                    debtor_rows = debtor_table.find_all('tr')
                    for row in debtor_rows:
                        cells = row.find_all('td')
                        if len(cells) == 2:
                            field = cells[0].text.strip()
                            value = cells[1].text.strip()

                            if "ФИО должника" in field:
                                debtor_fl_name = value
                            elif "Наименование должника" in field:
                                debtor_ul_name= value
                            else:
                                data[field] = value

                    if debtor_fl_name is None:
                        data["Полное_имя"] = debtor_ul_name
                    else:
                        data["Полное_имя"] = debtor_fl_name

                    logger.info(f"Полное имя: {data['Полное_имя']}")

            data.update(act)
            logger.info(f'сообщение: {data}')

            save_in_db(data)
    except Exception as e:
        logger.error(f'Не удалось спарсить содержимое сообщения: {e}')
        return None
    finally:
        if len(driver.window_handles) == 2:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])  # Переключаемся на последнюю вкладку
        elif len(driver.window_handles) > 2:
            for handle in driver.window_handles[1:][::-1]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(driver.window_handles[0])

def from_end_parsing(driver):
    try:
        visited_pages = set()
        list_of_messages = []

        while True:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table', class_='bank')
            if table:
                logger.info(f'нашел table')
                # Парсим строки
                rows = table.find_all('tr')
                logger.info(f'нашел tr')
                for row in rows:
                    cells = row.find_all("td")
                    logger.info(f'нашел td. количество ячеек: {len(cells)}')

                    if len(cells) == 5:
                        # Извлекаем данные из ячеек
                        date = cells[0].get_text(strip=True)
                        debtor = cells[2].get_text(strip=True)
                        link_messeges = cells[1].find("a")["href"] if cells[1].find("a") else None
                        link_debtor = cells[2].find("a")["href"] if cells[2].find("a") else None

                        new_messages = {
                            "дата": date,
                            "должник": debtor,
                            "должник_ссылка": f"https://old.bankrot.fedresurs.ru{link_debtor}" if link_debtor else "Нет ссылки",
                            "сообщение_ссылка": f"https://old.bankrot.fedresurs.ru{link_messeges}" if link_messeges else "Нет ссылки",
                        }
                        logger.info(f'лицо сообщения: {new_messages}')

                        list_of_messages.append(new_messages)
                        continue

                logger.info(f'начинаю пагинацию')
                # Если это строка с пагинацией
                pager_tr = soup.find('tr', class_='pager')
                logger.info(f'нашел pager_tr')
                if not pager_tr:
                    logger.info("Таблица пагинации не найдена, завершаем парсинг")
                    break
                pager_table = pager_tr.find_next('table')
                page_elements = pager_table.find_all('a', href=True)
                if not page_elements:
                    logger.info("Ссылки пагинации отсутствуют, завершаем парсинг")
                    break

                for page_element in page_elements:

                    href = page_element['href']
                    page_action = href.split("'")[3] if "'Page$" in href else href  #
                    logger.info(f"Обнаружено действие: {page_action}")

                    if page_action == 'Page$1':
                        logger.info('уже проверял первую страницу')
                        visited_pages.add(page_action)
                        continue

                    if page_action in visited_pages:
                        logger.info(f"Страница {page_action} уже обработана, пропускаем")
                        continue

                    # Проверяем, начинается ли href с нужного JavaScript
                    if "javascript:__doPostBack" in href:
                        try:
                            script = """
                                    var theForm = document.forms['aspnetForm'];
                                    if (!theForm) {
                                        theForm = document.aspnetForm;
                                    }
                                    if (!theForm.onsubmit || (theForm.onsubmit() != false)) {
                                        theForm.__EVENTTARGET.value = arguments[0];
                                        theForm.__EVENTARGUMENT.value = arguments[1];
                                        theForm.submit();
                                    }
                                    """
                            logger.info(f"Клик по элементу пагинации: {page_action}")
                            driver.execute_script(script, 'ctl00$cphBody$gvMessages', page_action)
                            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'html')))
                            time.sleep(3)  # Ожидание загрузки новой страницы
                            visited_pages.add(page_action)
                            break
                        except Exception as e:
                            logger.error(f"Ошибка при клике на элемент пагинации: {e}")
                            return
                else:
                    logger.info("Дополнительных страниц для перехода не найдено")
                    break
            else:
                logger.info(f'не осталось актов ')
                break

        return list_of_messages
    except Exception as e:
        logger.error(f'Ошибка при обработке страницы {driver.current_url}: {e}')
        return None