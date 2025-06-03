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
token = os.getenv("HH_API_TOKEN")
email = os.getenv("email")

# --- Параметры поиска ---
SEARCH_TEXT = "Менеджер проекта"
vacancy_array = np.array(["Менеджер проекта", "RPA аналитик", "Бизнес аналитик", "Руководитель проекта",
                          "Системный аналитик", "Финансовый аналитик"])
vacancy = "Менеджер проекта"
AREA_ID = "113" #Россия — 113 Москва — 1 Санкт-Петербург — 2 Московская область — 2019
PER_PAGE = 20 #100 #20
MAX_VACANCIES_TO_PROCESS = 100 #2000 # 100

# --- Токен доступа ---
ACCESS_TOKEN = token

# --- Константы API ---
BASE_URL = "https://api.hh.ru/vacancies" # Базовый URL

# --- Глобальная сессия для переиспользования соединения ---
session = requests.Session()
session.headers.update({'User-Agent': 'YourApp/1.0 (' + email + ')'})
if ACCESS_TOKEN:
    session.headers.update({'Authorization': f'Bearer {ACCESS_TOKEN}'})\

# константы
non_skills = 0

def get_vacancy_ids(vacancy, page=0, ):
    """
    Выполняет запрос к API HH.ru для получения страницы с ID вакансий.
    """
    search_query = vacancy.strip()
    if not search_query:
        print("Ошибка: Поисковый запрос (vacancy) не может быть пустым.")
        return None, 0, 0

    params = {
        'text': search_query,
        'date_from': datetime.date.today()- timedelta(days=14),
        'area': AREA_ID,
        'per_page': PER_PAGE,
        'page': page,
        'only_with_salary': False,
        # 'fields': 'id' # Можно попробовать запросить только ID, если API поддерживает
    }

    print(f"Запрос страницы {page} для получения ID...")
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

def get_vacancy_details(vacancy_id, number):
    """
    Выполняет запрос к API HH.ru для получения детальной информации о вакансии.
    """
    details_url = f"{BASE_URL}/{vacancy_id}"
    print(f"  Запрос деталей для вакансии ID: {vacancy_id}, № {number}")
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


def main(vacancy):
    """
    Основная функция: получает ID вакансий, затем детали, извлекает навыки, считает статистику.
    """
    all_vacancy_ids = []
    processed_ids_count = 0
    page = 0

    # --- Получение ID вакансий ---
    print("--- Этап 1: Сбор ID вакансий ---")
    # Получаем первую страницу, чтобы узнать общее количество
    initial_ids, total_vacancies_found, pages_available = get_vacancy_ids(vacancy, page)
    if initial_ids is None:
        print("Не удалось получить ID с первой страницы. Завершение.")
        return

    if not initial_ids:
        print("На первой странице не найдено ID вакансий. Завершение.")
        return

    # Учитываем лимит API (2000) и пользовательский лимит
    max_vacancies_effective = min(total_vacancies_found, MAX_VACANCIES_TO_PROCESS, 2000)
    max_pages_to_fetch = math.ceil(max_vacancies_effective / PER_PAGE)
    # API отдает не более 20 страниц (индексы 0-19)
    max_pages_to_fetch = min(max_pages_to_fetch, 20)

    print(f"Найдено вакансий (всего): {total_vacancies_found}")
    #print(f"Доступно страниц для API: {pages_available}")
    print(f"Будет обработано вакансий (с учетом лимитов): ~{max_vacancies_effective}")
    #print(f"Максимум страниц для запроса ID: {max_pages_to_fetch}")
    print("-" * 30)

    all_vacancy_ids.extend(initial_ids)
    processed_ids_count += len(initial_ids)
    page += 1

    while page < max_pages_to_fetch and processed_ids_count < max_vacancies_effective :
        vacancy_ids, _, _ = get_vacancy_ids(vacancy, page)
        if vacancy_ids is None: # Ошибка при запросе страницы
             page += 1
             time.sleep(0.5) # Пауза перед следующей попыткой
             continue
        if not vacancy_ids:
            print(f"На странице {page} больше нет ID, завершаем сбор ID.")
            break

        # Добавляем ID, но не больше, чем заданный лимит
        ids_to_add = max_vacancies_effective - processed_ids_count
        all_vacancy_ids.extend(vacancy_ids[:ids_to_add])
        added_count = len(vacancy_ids[:ids_to_add])
        processed_ids_count += added_count

        print(f"Получено {added_count} ID (всего собрано {processed_ids_count})...")

        page += 1
        # Пауза между запросами списка ID
        time.sleep(0.25)

    print("-" * 30)
    print(f"Сбор ID завершен. Собрано ID для обработки: {len(all_vacancy_ids)}")

    if not all_vacancy_ids:
        print("Не удалось собрать ID вакансий.")
        return

    # --- Этап 2: Получение деталей и извлечение навыков ---
    print("\n--- Этап 2: Получение деталей вакансий и извлечение навыков --- ", vacancy)
    all_skills = []
    processed_details_count = 0

    for vacancy_id in all_vacancy_ids:
        vacancy_details = get_vacancy_details(vacancy_id, processed_details_count)

        if vacancy_details: # Если детали получены успешно
            processed_details_count += 1
            # Извлекаем ключевые навыки (key_skills)
            key_skills = vacancy_details.get('key_skills', [])
            if key_skills:
                for skill_dict in key_skills:
                    skill_name = skill_dict.get('name')
                    if skill_name:
                         all_skills.append(skill_name)
        else: print('   Ошибка или нет навыков, пропуск')

            # Отладочный вывод первой вакансии с навыками (если нужно)
            # if processed_details_count == 1 and key_skills:
            #    print("\n--- Структура первой ВАКАНСИИ С НАВЫКАМИ ---")
            #    print(json.dumps(vacancy_details, indent=4, ensure_ascii=False))
            #    print("--- Конец структуры ---")

        # Важно! Пауза МЕЖДУ запросами ДЕТАЛЕЙ вакансий
        # Запросы деталей более частые, делаем паузу чуть больше,
        # особенно если нет токена с высоким лимитом
        time.sleep(0.3) # Можно увеличить до 0.5 или 1.0, если возникают ошибки 403 (Forbidden)

        # Обновление прогресса (например, каждые 50 вакансий)
        if processed_details_count % 50 == 0:
             print(f"Обработано деталей: {processed_details_count}/{len(all_vacancy_ids)}...")


    print("-" * 30)
    print(f"Обработка деталей завершена. Всего обработано: {processed_details_count}")
    print(f"Общее количество извлеченных 'упоминаний' навыков: {len(all_skills)}")

    if not all_skills:
        print("Не найдено ни одного навыка в обработанных вакансиях.")
        # На этом этапе стоит проверить, есть ли вообще поле key_skills в детальных ответах,
        # если результат все еще 0. Можно раскомментировать отладочный вывод выше.
        return

    # --- Анализ и подсчет навыков с использованием Pandas ---
    print("Анализ навыков...")
    # (Этот блок остается без изменений)
    skill_counts = Counter(all_skills)
    skills_df = pd.DataFrame(skill_counts.items(), columns=['Навык', 'Количество'])
    total_skill_mentions = skills_df['Количество'].sum()
    if total_skill_mentions > 0:
         skills_df['Процент'] = (skills_df['Количество'] / total_skill_mentions) * 100
         skills_df['Процент'] = skills_df['Процент'].map('{:.2f}%'.format)
    else:
         skills_df['Процент'] = '0.00%' # На случай, если skills все же пустые

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

for i in vacancy_array:
    if __name__ == "__main__":
        print("Поиск по вакансии: ", i)
        main(i)