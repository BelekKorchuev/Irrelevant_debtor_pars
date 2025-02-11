from datetime import datetime

from Parsing import message_type_selecter, from_end_parsing, message_parsing, get_dates_range
from logScript import logger
from webdriver import create_webdriver, restart_driver, is_browser_alive

beginning_time = "05.02.2025"
ending_time = "10.02.2025"
act = 'о завершении конкурсного производства'

begin_date = datetime.strptime(beginning_time, "%d.%m.%Y")
end_date = datetime.strptime(ending_time, "%d.%m.%Y")


def main():
    while True:
        driver = create_webdriver()  # Инициализация WebDriver

        # Получаем список всех дней между начальной и конечной датами
        dates_to_parse = get_dates_range(begin_date, end_date)  # Список дат
        logger.info(dates_to_parse)

        # Обход всех страниц при старте
        logger.info("Запускаем полный парсинг всех страниц.")

        for current_date in dates_to_parse:
            try:
                # Проверка, нужно ли перезапустить драйвер
                if not is_browser_alive(driver):
                    logger.warning("Браузер перестал отвечать. Перезапуск...")
                    driver = restart_driver(driver)
                    continue

                # переход на страницу, выбор определенного тип сообщений, выбор периода
                soup = message_type_selecter(driver, current_date, act)

                #  парсинг начиная с последней страницы
                list_dic = from_end_parsing(driver, soup)

                message_parsing(driver, list_dic)

            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                driver = restart_driver(driver)  # Перезапустите WebDriver
        else:
            logger.info(f'Парсинг завершен')
            break
if __name__ == "__main__":
    main()
