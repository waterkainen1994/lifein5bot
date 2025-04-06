import csv
import os
from datetime import datetime

# Путь к файлу CSV
CSV_FILE = "analytics.csv"

# Инициализация CSV-файла с заголовками, если он не существует
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "Имя пользователя",
                "Логин",
                "Нажатия /start",
                "Сгенерированные прогнозы",
                "Оплаты",
                "Время использования (мин)",
                "Последнее обновление"
            ])

# Чтение данных из CSV
def read_analytics_data():
    init_csv()
    data = []
    with open(CSV_FILE, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        data = list(reader)
    return data

# Запись или обновление данных в CSV
def update_analytics_data(username, user_id, start_count=0, forecast_count=0, payment_count=0, usage_time=0):
    data = read_analytics_data()
    
    # Проверяем, есть ли пользователь в таблице
    user_row = None
    for i, row in enumerate(data[1:], start=1):  # Пропускаем заголовок
        if row and row[1] == str(user_id):  # Сравниваем user_id (логин)
            user_row = i
            break
    
    # Текущая дата и время для столбца "Последнее обновление"
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if user_row is not None:
        # Обновляем существующую строку
        current_data = data[user_row]
        new_start_count = int(current_data[2]) + start_count
        new_forecast_count = int(current_data[3]) + forecast_count
        new_payment_count = int(current_data[4]) + payment_count
        new_usage_time = float(current_data[5]) + usage_time
        data[user_row] = [
            username,
            str(user_id),
            str(new_start_count),
            str(new_forecast_count),
            str(new_payment_count),
            str(new_usage_time),
            last_updated
        ]
    else:
        # Добавляем новую строку
        new_row = [
            username,
            str(user_id),
            str(start_count),
            str(forecast_count),
            str(payment_count),
            str(usage_time),
            last_updated
        ]
        data.append(new_row)
    
    # Перезаписываем CSV-файл
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(data)
