from parsing_hh import ParsingHH
from pprint import pprint

if __name__ == '__main__':
    search_url = 'https://spb.hh.ru/search/vacancy'  # ссылка поиска
    search_text = 'Python'  # Текст поиска
    currency = 'RUR'  # Валюта з/п
    search_word = ['Django', 'Flask']  # Ключевые слов
    salary_usd = False  # З/П только в валюте $/€ (True or False)
    quantity_limit = 10  # Ограничение глубины поиска (колличество страниц) (0 - безограничений)

    hh = ParsingHH(search_text=search_text,
                   search_url=search_url,
                   currency=currency,
                   search_word=search_word,
                   salary_usd=salary_usd,
                   quantity_limit=quantity_limit)
    hh.get_vacancy()
