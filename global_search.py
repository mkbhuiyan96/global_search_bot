import time
import re
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup

def create_session():
    payload = {
        'selectedInstName': 'Queens College | ',
        'inst_selection': 'QNS01',
        'selectedTermName': 'Fall 2023',
        'term_value': '1239',
        'next_btn': 'Next'
    }
    while True:
        try:
            session = requests.session()
            session.post('https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController', data=payload, timeout=10)
            return session
        except (RequestException, requests.Timeout):
            print("Error occurred while starting a session, trying again in 5 minutes.")
            time.sleep(300)

def main():
    class_url = input('Enter the URL of the class page from CUNY Global Search: ')
    session = create_session()

    while True:
        try:
            response = session.get(class_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            full_class_name = soup.find('span', {'id': 'DERIVED_CLSRCH_DESCR200'}).text.strip()
            
            match = re.search(r'([A-Z]+\s\d+)', full_class_name)
            if match:
                class_name = match.group(1)
            else:
                class_name = full_class_name
            status = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DESCRSHORT'}).text
            print(f'{class_name}: {status}')
            time.sleep(3)
        except (RequestException, requests.Timeout):
            session = create_session()
    
if __name__ == '__main__':
    main()