# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import os
import requests
import pandas as pd
from collections import Counter
import time
import math
from datetime import timedelta
import datetime
import numpy as np
import json

# импорт из .env
load_dotenv()
token = os.getenv("ACCESS_TOKEN")
email = os.getenv("email")

# --- Параметры поиска ---
SEARCH_TEXT = "Менеджер проекта"
vacancy_array = np.array(["Менеджер проекта", "RPA аналитик", "Бизнес аналитик", "Руководитель проекта",
                          "Системный аналитик", "Финансовый аналитик"])
vacancy = "Менеджер проекта"
AREA_ID = "113" #Россия — 113 Москва — 1 Санкт-Петербург — 2 Московская область — 2019
PER_PAGE = 100 #100 #20
MAX_VACANCIES_TO_PROCESS = 2000 #2000

# --- Токен доступа ---
ACCESS_TOKEN = token

# --- Константы API ---
BASE_URL = "https://api.hh.ru/vacancies" # Базовый URL

# --- Глобальная сессия для переиспользования соединения ---
session = requests.Session()
session.headers.update({'User-Agent': 'YourApp/1.0 (' + email + ')'})
if ACCESS_TOKEN:
    session.headers.update({'Authorization': f'Bearer {ACCESS_TOKEN}'})\


def get_vacancy_quantity(vacancy, page=0, ):
    search_query = vacancy.strip()
    if not search_query:
        print("Ошибка: Поисковый запрос (vacancy) не может быть пустым.")
        return None, 0, 0
    params = {
        'text': search_query,
        'date_from': datetime.date.today()- timedelta(days=28),
        'area': AREA_ID,
        'per_page': PER_PAGE,
        'page': page,
        'only_with_salary': False,
    }

    print(f"Запрос для получения количества вакансий с {datetime.date.today()- timedelta(days=28)} по текущую дату")
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

def get_vacancy_id_per_date(vacancy, date, page):
    search_query = vacancy.strip()
    if not search_query:
        print("Ошибка: Поисковый запрос (vacancy) не может быть пустым.")
        return None, 0, 0
    params = {
        'text': search_query,
        'date_from': date,
        'date_to': date,
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
            return
        if not vacancy_ids:
            print("На первой странице не найдено ID вакансий. Завершение.")
            return
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

def get_vacancy_ids(vacancy):
    page = 0
    all_processed_ids_count = 0
    all_vacancy_ids = []

    max_found, max_pages= get_vacancy_quantity(vacancy, page)
    if max_found >= MAX_VACANCIES_TO_PROCESS:
        for i in range(0,28):
            page = 0
            processed_ids_count = 0
            date = datetime.date.today() - timedelta(days=i)
            _, total_found, pages_available = get_vacancy_id_per_date(vacancy, date, page)
            print(f'Получение id от {datetime.date.today() - timedelta(days=i)}, всего найдено {total_found} вакансий')
            if total_found >2000:
                print('Ошибка: превышение лимита вакансий - больше 2000 вакансий за день')
                exit
            else:
                while page < pages_available and processed_ids_count < total_found :
                    vacancy_ids, _, _ = get_vacancy_id_per_date(vacancy, date, page)
                    if vacancy_ids is None: # Ошибка при запросе страницы
                         page += 1
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
            print(f"Завершена обработка {datetime.date.today() - timedelta(days=i)}. Получено {processed_ids_count} ID (всего собрано {all_processed_ids_count})")

    if not all_vacancy_ids:
        print("Не удалось собрать ID вакансий.")
        return

    print("-" * 30)
    print(f"Сбор ID завершен. Собрано ID для обработки: {len(all_vacancy_ids)}")
    return all_vacancy_ids



for i in vacancy_array:
    if __name__ == "__main__":
        print("Поиск по вакансии: ", i)
        all_vacancy_ids = get_vacancy_ids(i)
        print(all_vacancy_ids)
        print('\n\n\n')