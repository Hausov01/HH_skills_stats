from dotenv import load_dotenv
import requests
import os # Для примера с переменными окружения

load_dotenv()
# Теперь можно получить токен
token_id = os.getenv("token_id")
token_secret = os.getenv("token_secret")


# --- Ваши учетные данные ---
# ЗАМЕНИТЕ НА ВАШИ РЕАЛЬНЫЕ ДАННЫЕ
# ЛУЧШЕ ИСПОЛЬЗОВАТЬ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ИЛИ CONFIG ФАЙЛЫ
client_id = os.environ.get('HH_CLIENT_ID', token_id)
client_secret = os.environ.get('HH_CLIENT_SECRET', token_secret)

# --- URL для получения токена (ПРОВЕРЬТЕ В ДОКУМЕНТАЦИИ HH!) ---
token_url = 'https://hh.ru/oauth/token' # Пример! Уточните в документации!

# --- Данные для POST-запроса ---
data = {
    'grant_type': 'client_credentials',
    'client_id': client_id,
    'client_secret': client_secret
}

# --- Заголовки ---
# Обычно для этого запроса не нужен 'Authorization',
# но может требоваться 'Content-Type'
headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
}

print(f"Запрос токена на {token_url}...")

try:
    response = requests.post(token_url, data=data, headers=headers)
    response.raise_for_status() # Проверка на ошибки HTTP (4xx, 5xx)

    token_data = response.json()
    access_token = token_data.get('access_token')

    if access_token:
        print("Токен успешно получен!")
        print(f"Access Token: {access_token}")
        # Здесь вы можете сохранить токен для использования в основном скрипте
        # Например, записать в переменную или временный файл
        # ВАЖНО: Не выводите токен в логи в реальных системах!
    else:
        print("Ошибка: 'access_token' не найден в ответе.")
        print("Ответ сервера:", response.text)

except requests.exceptions.RequestException as e:
    print(f"Ошибка при запросе токена: {e}")
    if e.response is not None:
        print(f"Статус код: {e.response.status_code}")
        print(f"Ответ сервера: {e.response.text}")