# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import os
import requests
import pandas as pd
from datetime import timedelta
import datetime
import json
import time
from tqdm import tqdm
from dataclasses import dataclass



    # --- Константы API ---
BASE_URL = None  # Базовый URL
PER_PAGE = 100
MAX_VACANCIES_TO_PROCESS = 2000
session = None

# --- Параметры поиска ---
#SEARCH_TEXT = "Менеджер проекта"
#vacancy_array = np.array(["RPA аналитик", "Финансовый аналитик", "Бизнес аналитик", "Системный аналитик", "Менеджер проекта", "Руководитель проекта" ])
#vacancy = "Менеджер проекта"
#AREA_ID = "113" #Россия — 113 Москва — 1 Санкт-Петербург — 2 Московская область — 2019
#PERIOD = 7 #Период сбора вакансий

@dataclass
class HHConfig:
    base_url: str
    access_token: str | None = None
    email: str | None = None
    per_page: int = 100
    max_vacancies: int = 2000
    timeout: int = 10

def _get_vacancy_quantity(vacancy, PERIOD, AREA_ID, page=0, ):

    search_query = vacancy.strip()
    if not search_query:
        print("Ошибка: Поисковый запрос (vacancy) не может быть пустым.")
        return None, 0, 0
    params = {
        'text': search_query,
        'date_from': datetime.date.today()- timedelta(days=PERIOD),
        'area': AREA_ID,
        'per_page': PER_PAGE,
        'page': page,
        'only_with_salary': False,
    }

    print(f"Запрос для получения количества вакансий с {datetime.date.today()- timedelta(days=PERIOD)} по текущую дату, период: {PERIOD} дней")
    try:
        # Используем сессию
        response = session.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        vacancy_ids = [item['id'] for item in data.get('items', []) if 'id' in item]
        total_found = data.get('found', 0)
        pages_available = data.get('pages', 0)
        if vacancy_ids is None:
            print("Не удалось получить ID с первой страницы. Завершение.")
            return
        if not vacancy_ids:
            print("На первой странице не найдено ID вакансий. Завершение.")
            return
        print(f"Найдено вакансий (всего): {total_found}")
        return total_found, pages_available
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе списка ID вакансий: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status: {e.response.status_code}, Body: {e.response.text[:200]}...") # Покажем часть ответа
        return None, 0, 0
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON при запросе списка ID: {e}")
        print(f"Полученный текст: {response.text[:200]}...")
        return None, 0, 0

def _get_vacancy_ids_per_date(vacancy, date, page, PERIOD, AREA_ID):
    search_query = vacancy.strip()
    if not search_query:
        print("Ошибка: Поисковый запрос (vacancy) не может быть пустым.")
        return None, 0, 0
    if date != 'none':
        params = {
            'text': search_query,
            'date_from': date,
            'date_to': date,
            'area': AREA_ID,
            'per_page': PER_PAGE,
            'page': page,
            'only_with_salary': False,
        }
    else:
        params = {
            'text': search_query,
            'date_from': datetime.date.today() - timedelta(days=PERIOD),
            'area': AREA_ID,
            'per_page': PER_PAGE,
            'page': page,
            'only_with_salary': False,
        }

    #print(f"Запрос страницы {page} для получения ID")
    try:
        # Используем сессию
        response = session.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        vacancy_ids = [item['id'] for item in data.get('items', []) if 'id' in item]
        total_found = data.get('found', 0)
        pages_available = data.get('pages', 0)
        if vacancy_ids is None:
            print("Не удалось получить ID с первой страницы. Завершение.")
            return None
        if not vacancy_ids:
            print("На первой странице не найдено ID вакансий. Завершение.")
            return None
        #print(f"Найдено вакансий (всего): {total_found}, доступно страниц {pages_available} ")
        return vacancy_ids, total_found, pages_available
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе списка ID вакансий: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status: {e.response.status_code}, Body: {e.response.text[:200]}...") # Покажем часть ответа
        return None, 0, 0
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON при запросе списка ID: {e}")
        print(f"Полученный текст: {response.text[:200]}...")
        return None, 0, 0

#Сбор данных по дням о кол-во вакансий за период
def _get_vacancy_ids(vacancy, PERIOD, AREA_ID):
    page = 0
    all_processed_ids_count = 0
    all_vacancy_ids = []
    PER_PAGE = 100  # 100 #20
    MAX_VACANCIES_TO_PROCESS = 2000  # 2000

    max_found, max_pages = _get_vacancy_quantity(vacancy, PERIOD, AREA_ID, page)
    if max_found >= MAX_VACANCIES_TO_PROCESS:
        day_collection = (pd.date_range
        (
            start=datetime.date.today() - timedelta(days=PERIOD),
            end=datetime.date.today(),
            freq='D').strftime('%Y-%m-%d').tolist()
        )
        for date in tqdm(day_collection):
            page = 0
            processed_ids_count = 0
            _, total_found, pages_available = _get_vacancy_ids_per_date(vacancy, date, page, PERIOD, AREA_ID)
            #print(f'Получение id от {datetime.date.today() - timedelta(days=i)}, всего найдено {total_found} вакансий')
            if total_found >2000:
                print('Ошибка: превышение лимита вакансий - больше 2000 вакансий за день')
                exit()
            else:
                while page < pages_available and processed_ids_count < total_found :
                    vacancy_ids, _, _ = _get_vacancy_ids_per_date(vacancy, date, page, PERIOD, AREA_ID)
                    if vacancy_ids is None: # Ошибка при запросе страницы
                         page += 1
                         print("Ошибка при запросе страницы")
                         time.sleep(0.5) # Пауза перед следующей попыткой
                    if not vacancy_ids:
                        print(f"На странице {page} больше нет ID, завершаем сбор ID.")
                        break
                    # Добавляем ID, но не больше, чем заданный лимит
                    ids_to_add = total_found - processed_ids_count
                    all_vacancy_ids.extend(vacancy_ids)
                    added_count = len(vacancy_ids[:ids_to_add])
                    processed_ids_count += added_count

                    page += 1
                    # Пауза между запросами списка ID
                    time.sleep(0.25)
            all_processed_ids_count += processed_ids_count
            #print(f"Завершена обработка дня {i} ({datetime.date.today() - timedelta(days=i)}). Получено {processed_ids_count} ID (всего собрано {all_processed_ids_count})")
    #Если найдено вакансий сверх лимита выполняется пагинация
    else:
        page = 0
        processed_ids_count = 0
        _, total_found, pages_available = _get_vacancy_ids_per_date(vacancy, 'none', page, PERIOD, AREA_ID)
        print(f'Получение всех id, всего найдено {total_found} вакансий')
        if total_found > 2000:
            print('Ошибка: превышение лимита вакансий - больше 2000 вакансий за день')
            exit()
        else:
            while page < pages_available and processed_ids_count < total_found:
                vacancy_ids, _, _ = _get_vacancy_ids_per_date(vacancy, 'none', page, PERIOD, AREA_ID)
                if vacancy_ids is None:  # Ошибка при запросе страницы
                    page += 1
                    print("Ошибка при запросе страницы")
                    time.sleep(0.5)  # Пауза перед следующей попыткой
                if not vacancy_ids:
                    print(f"На странице {page} больше нет ID, завершаем сбор ID.")
                    break
                # Добавляем ID, но не больше, чем заданный лимит
                ids_to_add = total_found - processed_ids_count
                all_vacancy_ids.extend(vacancy_ids)
                added_count = len(vacancy_ids[:ids_to_add])
                processed_ids_count += added_count

                page += 1
                # Пауза между запросами списка ID
                time.sleep(0.25)
            print(f"Завершена обработка всех вакансий. Получено {processed_ids_count} ID (всего собрано {all_processed_ids_count})")

    if not all_vacancy_ids:
        print("Не удалось собрать ID вакансий.")
        return

    print("-" * 30)
    print(f"Сбор ID завершен. Собрано ID для обработки: {len(all_vacancy_ids)}")
    return all_vacancy_ids

#Получение данных по вакансиям по их собранным id
def _get_vacancy_details(vacancy_id):
    details_url = f"{BASE_URL}/{vacancy_id}"
    #print(f"  Запрос деталей для вакансии ID: {vacancy_id}, № {number}")
    try:
        # Используем ту же сессию с заголовками
        response = session.get(details_url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"  Ошибка при запросе деталей для ID {vacancy_id}: {e}")
        # Обработка специфичных ошибок (404 Not Found - вакансия удалена/архивирована)
        if hasattr(e, 'response') and e.response is not None:
             if e.response.status_code == 404:
                 print(f"  Вакансия {vacancy_id} не найдена (возможно, удалена).")
             elif e.response.status_code == 403:
                 print(f"  Доступ к вакансии {vacancy_id} запрещен (403). Проверьте токен/права.")
             else:
                 print(f"  Status: {e.response.status_code}, Body: {e.response.text[:200]}...")
        return None
    except json.JSONDecodeError as e:
        print(f"  Ошибка декодирования JSON для деталей ID {vacancy_id}: {e}")
        print(f"  Полученный текст: {response.text[:200]}...")
        return None

# импорт из .env
def configure(env_path):
    """Загружает переменные из .env, если путь указан."""
    if env_path:
        load_dotenv(dotenv_path=env_path)

def create_session(env_path=".env"):
    configure(env_path)
    token = os.getenv("ACCESS_TOKEN")
    email = os.getenv("email")
    BASE_URL = os.getenv("BASE_URL")

    # --- Токен доступа ---
    ACCESS_TOKEN = token

    # --- Глобальная сессия для переиспользования соединения ---
    global session
    global BASE_URL
    session = requests.Session()
    session.headers.update({'User-Agent': 'YourApp/1.0 (' + email + ')'})
    if ACCESS_TOKEN:
        session.headers.update({'Authorization': f'Bearer {ACCESS_TOKEN}'})
    return session


def external_request(AREA_ID, PERIOD, vacancy):
    count = 0
    results = []

    print("--- Этап 1: Сбор ID вакансий ---")
    print("Поиск по вакансии: ", vacancy)
    all_vacancy_ids = _get_vacancy_ids(vacancy, PERIOD, AREA_ID)
    print("\n--- Этап 2: Получение деталей вакансий и извлечение навыков --- ", vacancy)
    for id in tqdm(all_vacancy_ids):
        vacancy_details = _get_vacancy_details(id)
        count +=1
        time.sleep(0.25)
        if vacancy_details: # Если детали получены успешно
            results.append(vacancy_details)
        else:
            print("Ошибка получения деталей вакансии")
    final_json = json.dumps(results, ensure_ascii=False, indent=2)
    with open('output.json', 'w', encoding='utf-8') as f:
        f.write(final_json)
    return final_json

__all__ = ['external_request', 'create_session']

if __name__ == "__main__":
    print("Прямой запуск не предусмотрен")