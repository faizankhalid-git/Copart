import datetime
import datetime as DT
import json
import time

import scrapy
from scrapy import Request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


class CopartSpider(scrapy.Spider):
    name = 'copart'
    custom_settings = {
        'FEED_URI': r'Output/copart.csv',
        'FEED_FORMAT': 'csv',
    }
    url = "https://www.copart.com/public/lots/search-results"

    today_date = DT.date.today()
    today = today_date + DT.timedelta(days=2)
    after_week = today_date + DT.timedelta(days=9)
    # print(today.strftime('%Y-%m-%d'))
    # print(after_week)
    payload = {
        "query": [
            "*"
        ],
        "filter": {
            "ODM": [
                "odometer_reading_received:[0 TO 200000]"
            ],
            "SDAT": [
                f"auction_date_utc:[\"{today.strftime('%Y-%m-%d')}T00:00:00Z\" TO \"{after_week}T23:59:59Z\"]"
            ],
            "TITL": [
                "title_group_code:TITLEGROUP_S"
            ],
            "VEHT": [
                "vehicle_type_code:VEHTYPE_V"
            ],
            "YEAR": [
                "lot_year:[1996 TO 2016]"
            ]
        },
        "sort": [
            "auction_date_type desc",
            "auction_date_utc asc"
        ],
        "page": 0,
        "size": 100,
        "start": 0,
        "watchListOnly": False,
        "freeFormSearch": False,
        "hideImages": False,
        "defaultSort": False,
        "specificRowProvided": False,
        "displayName": "",
        "searchName": "",
        "backUrl": "",
        "includeTagByField": {},
        "rawParams": {}
    }
    headers = {
        'authority': 'www.copart.com',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'access-control-allow-headers': 'Content-Type, X-XSRF-TOKEN',
        'content-type': 'application/json',
        'origin': 'https://www.copart.com',
        'referer': 'https://www.copart.com/lotSearchResults?free=true&query=&searchCriteria=%7B%22query%22:%5B%22*%22%5D,%22filter%22:%7B%22ODM%22:%5B%22odometer_reading_received:%5B0%20TO%20150000%5D%22%5D,%22TITL%22:%5B%22title_group_code:TITLEGROUP_S%22%5D,%22VEHT%22:%5B%22vehicle_type_code:VEHTYPE_V%22%5D,%22YEAR%22:%5B%22lot_year:%5B1996%20TO%202016%5D%22%5D%7D,%22sort%22:%5B%22auction_date_type%20desc%22,%22auction_date_utc%20asc%22%5D,%22watchListOnly%22:false,%22searchName%22:%22%22,%22freeFormSearch%22:false%7D',
        'sec-ch-ua': '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest'
    }
    options = webdriver.ChromeOptions()
    # options.headless = True
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()

    def start_requests(self):
        self.driver.get('https://www.copart.com/login/')
        time.sleep(8)
        self.driver.find_element(By.CSS_SELECTOR, '#username').send_keys('nat7867860@gmail.com')
        self.driver.find_element(By.CSS_SELECTOR, '#password').send_keys('Auto2022')
        self.driver.find_element(By.CSS_SELECTOR, '.panel [data-uname="loginSigninmemberbutton"]').click()
        time.sleep(5)
        yield Request(url=self.url,
                      body=json.dumps(self.payload),
                      method='POST',
                      headers=self.headers,
                      cookies=self.driver.get_cookies(),
                      meta={'start': 0, 'page': 0, 'my_cookie': self.driver.get_cookies()})

    def parse(self, response, **kwargs):
        json_data = json.loads(response.text)
        total_records = json_data.get('data', {}).get('results', {}).get('totalElements', 0)
        all_listing = json_data.get('data', {}).get('results', {}).get('content', {})
        for listing in all_listing:
            lot_num = listing.get('lotNumberStr', '')
            relative_url = listing.get('idu', '')
            absolute_url = f"https://www.copart.com/lot/{lot_num}/{relative_url}"
            product_name = listing.get('ld', {})
            fv = listing.get('fv', {})
            lot = listing.get('lotNumberStr', {})
            location = listing.get('yn', {})
            sale_timestamp = listing.get('ad', '')
            # adt = listing.get('odometerUOM','')
            # if adt == 'A':
            #     sale_time = 'Future'
            # else:
            try:
                sale_time = datetime.datetime.fromtimestamp(sale_timestamp / 1000).strftime('%m-%d-%Y')
            except:
                sale_time = 'Future'
            # if sale_time:
            yield {
                'Name': product_name,
                'Url': absolute_url,
                'FV': fv,
                'LOT': lot,
                'Location': location,
                'Sale Date':sale_time
            }
        if response.meta['start'] < total_records + 100:
            dynamic_payload = self.payload
            page = response.meta['page'] + 1
            start = response.meta['start'] + 100
            dynamic_payload['page'] = page
            dynamic_payload['start'] = start
            yield Request(url=self.url,
                          callback=self.parse,
                          body=json.dumps(dynamic_payload),
                          headers=self.headers,
                          method='POST',
                          cookies=response.meta['my_cookie'],
                          meta={'start': start, 'page': page, 'my_cookie': response.meta['my_cookie']})
