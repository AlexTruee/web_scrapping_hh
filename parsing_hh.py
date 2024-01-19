import json
import re
import time
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bs4 import BeautifulSoup
from tqdm import tqdm
from fake_headers import Headers

logging.basicConfig(level=logging.INFO)


class ParsingHH:
    def __init__(self, search_text=None,
                 search_word=None,
                 search_url=None,
                 currency='RUR',
                 salary_usd=False,
                 quantity_limit=0) -> None:

        self.search_text = search_text
        self.search_url = search_url
        self.currency = currency
        self.search_word = search_word
        self.salary_usd = salary_usd
        self.quantity_limit = quantity_limit

    # Функция для создания рандомных заголовков
    def get_headers(self) -> dict:
        headers = Headers(os="win", headers=True).generate()
        headers.update({
            'accept-language': 'ru,en;q=0.9'
        })
        return headers

    # Функция создания сессии
    def retry_session(self,
                      retries=5,
                      backoff_factor=0.3,
                      status_forcelist=(500, 502, 504),
                      session=None,
                      ) -> any:
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update(self.get_headers())
        return session

    # Функция формирования параметров
    def get_params(self, pg=None) -> dict:
        params = {
            'L_save_area': 'true',
            'text': self.search_text,
            'excluded_text': '',
            'area': [
                '1',
                '2',
            ],
            'salary': '',
            'experience': 'doesNotMatter',
            'order_by': 'relevance',
            'search_period': '0',
            'currency_code': self.currency,
            'items_on_page': '20',
        }

        if pg is not None:
            params.update(
                {
                    'page': pg
                }
            )
        return params

    # Функция приготовления супа
    def get_soup(self, session, url, params=None) -> BeautifulSoup | None:
        time.sleep(1)
        data = session.get(url, params=params)
        if data.status_code != 200:
            logging.error(f'Страница {data.url} / статус код: {data.status_code}')
            return
        return BeautifulSoup(data.content, 'lxml')

    # Функция получения ссылок на страницы с вакансиями
    def get_links(self) -> list | None:
        session = self.retry_session()
        params = self.get_params()
        soup = self.get_soup(session, self.search_url, params=params)
        if not soup:
            return
        page_count = int(soup.find('div', attrs={'class': 'pager'}).find_all('span', recursive=False)[-1].
                         find('a').find('span').text)

        links_vacancy = []

        logging.info('Собираем ссылки на вакансии')

        if self.quantity_limit != 0 and self.quantity_limit <= page_count:
            page_count = self.quantity_limit

        for index in tqdm(range(page_count), position=0, leave=True,
                          bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
            params = self.get_params(pg=index)
            soup = self.get_soup(session, self.search_url, params=params)
            div_data = soup.find_all('div', class_='vacancy-serp-item-body__main-info')
            a_links = []
            for _ in tqdm(div_data, colour='yellow', position=0, leave=True,
                          bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
                a = _.find('span', attrs={'data-page-analytics-event': 'vacancy_search_suitable_item'}).find('a')
                a_links.append(a.attrs['href'].split('?')[0])
                # time.sleep(1)
            links_vacancy += a_links
        # Записываем полученные ссылки в файл
        # with open('links.txt', 'w', encoding='utf-8') as f:
        #     for line in links_vacancy:
        #         f.write(line + '\n')
        # logging.info(f'Ссылки собраны и сохранены в файл. Собрано {len(links_vacancy)} ссылок')
        return links_vacancy

    # Функция получения информации по вакансии
    def get_vacancy_info(self, soup) -> tuple | None:
        try:
            div_description = soup.find('div', attrs={'class': 'vacancy-description'})
            data_qa_description = soup.find('div', attrs={'data-qa': 'vacancy-description'})
            if div_description:
                vacancy_description = div_description.text
            else:
                vacancy_description = data_qa_description.text
            vacancy_title = soup.find('h1').text

            company_name = soup.find('span', class_='vacancy-company-name').text
            company_name = ' '.join(company_name.split())  # Исключаем попадание символа пробела в формате &nbsp
            company_town = soup.find(['span', 'p'], attrs={'data-qa': ['vacancy-view-raw-address',
                                                                       'vacancy-view-location']}).text.split(',')[0]
            if not self.search_word:
                return vacancy_title, company_name, company_town
            if any(ele.lower() in vacancy_description.lower() for ele in self.search_word):
                return vacancy_title, company_name, company_town
            return
        except Exception as e:
            logging.error(e)
            return

    # Функция получения информации по зарплате
    def get_vacancy_salary(self, soup) -> str:
        vacancy_salary = soup.find('div', attrs={'data-qa': 'vacancy-salary'})
        if vacancy_salary:
            salary_from = re.match(r'(от)(\s\d*\s\d*)', vacancy_salary.text)
            salary_before = re.match(r'(до)(\s\d*\s\d*)', vacancy_salary.text)
            salary_currencies = re.search(r'\₽|\$|\€', vacancy_salary.text).group(0)

            if salary_from and salary_before:
                salary = f'{"".join(salary_from.group(2).split())}-{"".join(salary_before.group(2).split())} ' \
                         f'{salary_currencies}'
            elif salary_from:
                salary = f'от {"".join(salary_from.group(2).split())} {salary_currencies}'
            else:
                salary = f'до {"".join(salary_before.group(2).split())} {salary_currencies}'
        else:
            salary = 'по договоренности'
        return salary

    # Основная функция формирования списка подходящих вакансий
    def get_vacancy(self) -> None:
        # Код для обработки вакансий через файл
        # self.get_links()
        # with open('links.txt', 'r') as f:
        #     links_vacancy = [line.rstrip() for line in f]
        links_vacancy = self.get_links()
        session = self.retry_session()
        vacancy_list = []

        logging.info('Рассматриваем вакансии')

        for link in tqdm(links_vacancy, colour='green', position=0, leave=True,
                         bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}'):
            # print(link)
            soup = self.get_soup(session, link)
            if not soup:
                continue

            salary = self.get_vacancy_salary(soup)

            if self.salary_usd:
                if not any(ele.lower() in salary for ele in ['$', '€']):
                    continue
            vacancy_info = self.get_vacancy_info(soup)

            if not vacancy_info:
                continue

            vacancy_list.append(
                {
                    'Ссылка': link,
                    'Зарплата': salary,
                    # 'Наименование вакансии': vacancy_info[0],
                    'Наименование компании': vacancy_info[1],
                    'Город': vacancy_info[2]
                }
            )

        logging.info(f'Просмотренно вакансий: {len(links_vacancy)}')
        logging.info(f'Найдено подходящих вакансий: {len(vacancy_list)}')

        if vacancy_list:
            with open('vacancy_data.json', 'w', encoding='utf-8') as fj:
                json.dump(vacancy_list, fj, ensure_ascii=False, indent=4)
            logging.info(f'Вакансии сохранены в json файл')
