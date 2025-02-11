import logging
import os
from logging.handlers import RotatingFileHandler

# Создаём директорию для логов, если её нет
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Пути для файлов логов
info_log_file = os.path.join(log_dir, "info.log")
error_log_file = os.path.join(log_dir, "error.log")

# Настройка логгера
logger = logging.getLogger("MyLogger")
logger.setLevel(logging.DEBUG)  # Устанавливаем минимальный уровень для логгера

# Форматирование логов
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Обработчик для INFO и DEBUG
info_handler = RotatingFileHandler(info_log_file, maxBytes=20 * 1024 * 1024, backupCount=100, encoding='utf-8')
info_handler.setFormatter(formatter)
info_handler.setLevel(logging.INFO)

# Обработчик для WARNING, ERROR, CRITICAL
error_handler = RotatingFileHandler(error_log_file, maxBytes=20 * 1024 * 1024, backupCount=5, encoding='utf-8')
error_handler.setFormatter(formatter)
error_handler.setLevel(logging.WARNING)

# Обработчик для консоли (по желанию)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Добавляем обработчики к логгеру
logger.addHandler(info_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)
