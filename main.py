import sys
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import logging
import atexit
import os
from Parsing import message_type_selecter, from_end_parsing, message_parsing, get_dates_range
from webdriver import create_webdriver, restart_driver, is_browser_alive
from logScript import logger
import requests

def check_internet_connection():
    try:
        response = requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record) + '\n'
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, msg)
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)


class ParsingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Парсер судебных актов")
        self.running = False

        self.setup_ui()
        self.setup_logging()

        atexit.register(self.cleanup_logs)

    def setup_ui(self):

        main_frame = tk.Frame(self.root)
        main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="Выберите тип акта:").grid(row=0, column=0, sticky='w')
        self.combo_act = ttk.Combobox(left_frame, values=[
            "о завершении конкурсного производства",
            "о завершении реализации имущества гражданина",
            "о прекращении производства по делу",
            "определение о прекращении производства по делу",
            "определение о завершении реализации имущества гражданина"
        ])
        self.combo_act.grid(row=0, column=1, padx=5, pady=5)
        self.combo_act.current(0)

        tk.Label(left_frame, text="Начальная дата:").grid(row=1, column=0, sticky='w')
        self.start_date = DateEntry(left_frame, date_pattern='dd.MM.yyyy')
        self.start_date.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(left_frame, text="Конечная дата:").grid(row=2, column=0, sticky='w')
        self.end_date = DateEntry(left_frame, date_pattern='dd.MM.yyyy')
        self.end_date.grid(row=2, column=1, padx=5, pady=5)

        self.start_button = tk.Button(left_frame, text="Запустить парсинг", command=self.start_parsing)
        self.start_button.grid(row=3, column=0, pady=10)

        self.stop_button = tk.Button(left_frame, text="Остановить", command=self.stop_parsing, state=tk.DISABLED)
        self.stop_button.grid(row=3, column=1, pady=10)

        self.progress_label = tk.Label(left_frame, text="Прогресс выполнения: 0%")
        self.progress_label.grid(row=4, column=0, columnspan=2)

        self.progress_bar = ttk.Progressbar(left_frame, length=200, mode='determinate')
        self.progress_bar.grid(row=5, column=0, columnspan=2, pady=5)

        tk.Label(right_frame, text="Логи:").pack(anchor='w')
        self.log_text = tk.Text(right_frame, height=20, width=50, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if self.running:
            if messagebox.askyesno("Выход", "Парсинг запущен. Выйти?"):
                self.stop_parsing()
        self.root.destroy()

    def setup_logging(self):
        self.text_handler = TextHandler(self.log_text)
        logger.addHandler(self.text_handler)

    def cleanup_logs(self):
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def start_parsing(self):
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        act_type = self.combo_act.get()
        start_date = datetime.strptime(self.start_date.get(), "%d.%m.%Y")
        end_date = datetime.strptime(self.end_date.get(), "%d.%m.%Y")

        self.progress_bar['value'] = 0
        self.progress_label.config(text="Прогресс выполнения: 0%")
        logger.info("Запуск парсинга...")

        threading.Thread(target=self.run_parsing, args=(start_date, end_date, act_type), daemon=True).start()

    def run_parsing(self, start_date, end_date, act_type):
        try:
            missing_data = []
            try:
                self.driver = create_webdriver()
            except Exception as e:
                logger.error(f"Не удалось запустить WebDriver: {e}")
                self.stop_parsing()
                return
            dates_to_parse = get_dates_range(start_date, end_date)
            total_dates = len(dates_to_parse)

            for i, current_date in enumerate(dates_to_parse):

                if not self.running:
                    break

                # Проверка интернет-соединения перед началом парсинга
                while not check_internet_connection():
                    logger.warning("Нет подключения к интернету. Ожидание восстановления...")
                    time.sleep(10)  # Проверяем каждые 10 секунд
                try:
                    if not is_browser_alive(self.driver):
                        logger.warning("Браузер неактивен, перезапуск...")
                        self.driver = restart_driver(self.driver)

                    message_type_selecter(self.driver, current_date, act_type)
                    time.sleep(4)
                    list_dic = from_end_parsing(self.driver)
                    if list_dic is None:
                        logger.error(f'Текушая дата: {current_date}, причина: ошибка в from_end_parsing, акт: {act_type}')
                        continue
                    if list_dic:
                        data = message_parsing(self.driver, list_dic, act_type)
                        if data is False:
                            logger.error(f'Текушая дата: {current_date}, причина: ошибка в message_parsing, акт: {act_type}')
                            continue

                    logger.info(f"Парсинг завершен для {current_date.strftime('%d.%m.%Y')}")
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    self.driver = restart_driver(self.driver)

                new_progress = int(((i + 1) / total_dates) * 100)
                if new_progress > self.progress_bar['value'] + 4:  # Обновление каждые 5%
                    self.progress_bar['value'] = new_progress
                    self.progress_label.config(text=f"Прогресс выполнения: {new_progress}%")

            self.progress_bar['value'] = 100
            self.show_completion_message()
        finally:
            if self.driver:
                self.driver.quit()
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def show_completion_message(self):
        self.progress_label.config(text="Готово!")
        messagebox.showinfo("Парсинг завершен", "Парсинг успешно завершен!")
        self.current_date_label.config(text="Текущая дата: Не выбрана")

    def stop_parsing(self):
        logger.info("Остановка парсинга...")
        self.running = False
        self.stop_button.config(state=tk.DISABLED)
        self.start_button.config(state=tk.NORMAL)

        if self.driver:
            logger.info("Закрытие браузера...")
            self.driver.quit()
            self.driver = None

        self.progress_bar['value'] = 0
        self.progress_label.config(text="Остановлено")
        logger.info("Парсинг остановлен.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ParsingApp(root)
    root.mainloop()

# def main():
#     while True:
#         driver = create_webdriver()  # Инициализация WebDriver
#
#         # Получаем список всех дней между начальной и конечной датами
#         dates_to_parse = get_dates_range(begin_date, end_date)  # Список дат
#         logger.info(dates_to_parse)
#
#         # Обход всех страниц при старте
#         logger.info("Запускаем полный парсинг всех страниц.")
#
#         for current_date in dates_to_parse:
#             try:
#                 # Проверка, нужно ли перезапустить драйвер
#                 if not is_browser_alive(driver):
#                     logger.warning("Браузер перестал отвечать. Перезапуск...")
#                     driver = restart_driver(driver)
#                     continue
#
#                 # переход на страницу, выбор определенного тип сообщений, выбор периода
#                 message_type_selecter(driver, current_date, act)
#
#                 time.sleep(4)
#
#                 #  парсинг начиная с последней страницы
#                 list_dic = from_end_parsing(driver)
#
#                 message_parsing(driver, list_dic)
#
#             except Exception as e:
#                 logger.error(f"Ошибка в основном цикле: {e}")
#                 driver = restart_driver(driver)  # Перезапустите WebDriver
#         else:
#             logger.info(f'Парсинг завершен')
#             break
