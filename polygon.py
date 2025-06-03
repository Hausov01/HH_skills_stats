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
PER_PAGE = 1 #100
MAX_VACANCIES_TO_PROCESS = 1 #2000

# --- Токен доступа ---
ACCESS_TOKEN = token

# --- Константы API ---
BASE_URL = "https://api.hh.ru/vacancies" # Базовый URL

# --- Глобальная сессия для переиспользования соединения ---
session = requests.Session()
session.headers.update({'User-Agent': 'YourApp/1.0 (' + email + ')'})
if ACCESS_TOKEN:
    session.headers.update({'Authorization': f'Bearer {ACCESS_TOKEN}'})

all_vacancy_ids = []
processed_ids_count = 0
page = 0

def main(vacancy):
    search_query = vacancy.strip()
    if not search_query:
        print("Ошибка: Поисковый запрос (vacancy) не может быть пустым.")
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

    # Используем сессию
    response = session.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()
    with open("response_ids.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    vacancy_ids = [item['id'] for item in data.get('items', []) if 'id' in item]
    print(vacancy_ids[0])


    details_url = f"{BASE_URL}/{vacancy_ids[0]}"
    print(details_url)

    response = session.get(details_url)
    response.raise_for_status()
    data = response.json()
    #print(data)
    skills = data.get('key_skills', [])
    if skills is None:
        print('None')
    else:
        print('!None')
    print(skills)
    print(type(skills))
    for skill in skills:
        print(skill.get('name'))
    with open("response_data.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

for i in vacancy_array:
    if __name__ == "__main__":
        print("Поиск по вакансии: ", i)
        main(i)