import requests
import time
from dataclasses import dataclass
from typing import Any, Dict
import math

__all__ = ['external_request', 'create_session']

if __name__ == "__main__":
    print("Прямой запуск не предусмотрен")

@dataclass
class HHConfig:
    per_page: int = 100
    max_vacancies: int = 2000
    timeout: tuple = (3, 10)

@dataclass
class SearchParams:
    period: int
    area_id: str
    vacancy: str
    base_url: str
    access_token: str
    email: str

def create_session(search_config: SearchParams):
    session = requests.Session()
    headers = {
        'User-Agent': f'HH-API-Client/1.0 ({search_config.email})' if search_config.email else 'HH-API-Client/1.0'
    }
    if search_config.access_token:
        headers['Authorization'] = f'Bearer {search_config.access_token}'
    session.headers.update(headers)
    return session

def external_request(session, search_config: SearchParams):
    count = 0
    results = []

    if session is None:
        raise RuntimeError("Session not initialized. Call create_session() first.")

    print("--- Этап 1: Сбор ID вакансий ---")
    print("Поиск по вакансии: ", search_config.vacancy)
    all_vacancy_ids = _get_all_vacancy_ids(session, search_config)
    print('-'*30)
    print(all_vacancy_ids)
    all_data= _get_all_vacancy_details(session, all_vacancy_ids, search_config)
    print(all_data)
    return all_data


def _get_all_vacancy_ids(session, search_config: SearchParams):
    hhconfig = HHConfig()
    all_vacancy_ids=[]
    print('запрос для получения кол-во станиц')
    params = {
        'text': search_config.vacancy,
        'period': search_config.period,
        'area': search_config.area_id,
        'per_page': hhconfig.per_page,
        'page': 0
    }
    data = _request(session, search_config.base_url, params, hhconfig.timeout)
    total_found = data.get('found', 0)
    pages_available = data.get('pages', 0)
    print(total_found, pages_available)
    total_found = min(total_found, hhconfig.max_vacancies)
    pages_available = math.ceil(total_found / hhconfig.per_page)
    print(total_found, pages_available)
    for i in range(pages_available):
        print("page", i)
        params = {
            'text': search_config.vacancy,
            'period': search_config.period,
            'area': search_config.area_id,
            'per_page': hhconfig.per_page,
            'page': i
        }
        seen = set()
        data = _request(session, search_config.base_url, params, hhconfig.timeout)
        vacancy_ids = [item['id'] for item in data.get('items', []) if 'id' in item]
        print(vacancy_ids)
        for item in vacancy_ids:
            if len(all_vacancy_ids) >= hhconfig.max_vacancies:
                return all_vacancy_ids
            if item not in seen:
                seen.add(item)
                all_vacancy_ids.append(item)
    return all_vacancy_ids

def _get_all_vacancy_details(session, all_vacancy_ids, search_config: SearchParams):
    hhconfig = HHConfig()
    all_data = []
    for vacancy_id in all_vacancy_ids:
        details_url = f"{search_config.base_url}/{vacancy_id}"
        data = _request(session, details_url, None, hhconfig.timeout)
        #print(data)
        all_data.append(data)
    return all_data




def _request(session: requests.Session, url: str, params: dict | None, timeout, max_retries: int = 3) -> Dict[str, Any]:
    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, timeout=timeout)

            # --- 429 ---
            if response.status_code == 429:
                sleep_time = 2 ** attempt
                print(f"Rate limit hit. Retry in {sleep_time}s")
                time.sleep(sleep_time)
                continue

            response.raise_for_status()

            return response.json()

        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt+1}")
        except requests.exceptions.ConnectionError:
            print(f"Connection error on attempt {attempt+1}")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {e}")
            raise
        except ValueError:
            print("Invalid JSON response")
            raise

        time.sleep(2 ** attempt)

    raise RuntimeError("Max retries exceeded")