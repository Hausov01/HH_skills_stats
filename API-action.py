# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import os
import requests
import pandas as pd
from collections import Counter
from datetime import timedelta
import datetime
import numpy as np
import json
import time
from tqdm import tqdm

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
            print(f"Завершена обработка дня {i} ({datetime.date.today() - timedelta(days=i)}). Получено {processed_ids_count} ID (всего собрано {all_processed_ids_count})")

    if not all_vacancy_ids:
        print("Не удалось собрать ID вакансий.")
        return

    print("-" * 30)
    print(f"Сбор ID завершен. Собрано ID для обработки: {len(all_vacancy_ids)}")
    return all_vacancy_ids

def get_vacancy_details(vacancy_id, number):
    details_url = f"{BASE_URL}/{vacancy_id}"
    #print(f"  Запрос деталей для вакансии ID: {vacancy_id}, № {number}")
    try:
        # Используем ту же сессию с заголовками
        response = session.get(details_url)
        response.raise_for_status()
        data = response.json()
        if data.get('key_skills', []) is None:
            print('нет навыков')
            return
        else:
            return response.json()
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

all_skills = []
count = 0
processed_details_count = 0
non_skills = 0

for vac in vacancy_array:
    if __name__ == "__main__":
        print("--- Этап 1: Сбор ID вакансий ---")
        print("Поиск по вакансии: ", vac)
        all_vacancy_ids = get_vacancy_ids(vac)
        print("\n--- Этап 2: Получение деталей вакансий и извлечение навыков --- ", vac)
        for id in tqdm(all_vacancy_ids):
            vacancy_details = get_vacancy_details(id, count)
            count +=1
            time.sleep(0.25)
            if vacancy_details: # Если детали получены успешно
                # Извлекаем ключевые навыки (key_skills)
                key_skills = vacancy_details.get('key_skills', [])
                if len(key_skills) != 0:
                    processed_details_count += 1
                    for skill_dict in key_skills:
                        skill_name = skill_dict.get('name')
                        if skill_name:
                             all_skills.append(skill_name)
                else:
                    non_skills +=1
                    #print('  В вакансии не указаны навыки - пропуск')
            else: print('  Ошибка получения деталей вакансии')
        print(f"Обработано вакансий в процентном отношении: {(processed_details_count/len(all_vacancy_ids))*100}...")

        print(f"Обработка деталей завершена. Всего обработано: {processed_details_count}")
        print(f"Общее количество извлеченных 'упоминаний' навыков: {len(all_skills)}")
        print(f"Общее количество вакансий без навыков {non_skills}")
        if not all_skills:
            print("Не найдено ни одного навыка в обработанных вакансиях.")
        print("-" * 30)

        print("---Этап 3:Анализ навыков---")
        # (Этот блок остается без изменений)
        skill_counts = Counter(all_skills)
        skills_df = pd.DataFrame(skill_counts.items(), columns=['Навык', 'Количество'])
        total_skill_mentions = skills_df['Количество'].sum()
        if total_skill_mentions > 0:
            skills_df['Процент'] = (skills_df['Количество'] / total_skill_mentions) * 100
            skills_df['Процент'] = skills_df['Процент'].map('{:.2f}%'.format)
        else:
            skills_df['Процент'] = '0.00%'  # На случай, если skills все же пустые

        skills_df = skills_df.sort_values(by='Количество', ascending=False).reset_index(drop=True)

        # --- Вывод результатов ---
        print("-" * 30)
        print(f"Топ {min(30, len(skills_df))} навыков для '{vacancy}':")
        print(skills_df.head(30).to_string())

        # --- Сохранение в CSV (опционально) ---
        try:
            output_filename = f"data/hh_skills_{vacancy.lower().replace(' ', '_')}_{AREA_ID}.csv"
            skills_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            print("-" * 30)
            print(f"Результаты сохранены в файл: {output_filename}")
        except Exception as e:
            print(f"\nНе удалось сохранить файл: {e}")

        print('\n\n\n')