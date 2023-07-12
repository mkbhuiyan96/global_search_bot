import time
import re
from bs4 import BeautifulSoup
import requests
from requests.exceptions import RequestException

def main():
    class_url = input('Enter the URL of the class page from CUNY Global Search: ')
    payload = {
        'selectedInstName': 'Queens College | ',
        'inst_selection': 'QNS01',
        'selectedTermName': 'Fall 2023',
        'term_value': '1239',
        'next_btn': 'Next'
    }
    
    while True:
        try:
            with requests.session() as session:
                session.post('https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController', data=payload)
                response = session.get(class_url)
                soup = BeautifulSoup(response.content, 'html.parser')
                
            full_class_name = soup.find('span', {'id': 'DERIVED_CLSRCH_DESCR200'}).text.strip()
            match = re.search(r'([A-Z]+\s\d+)', full_class_name)
            if match:
                class_name = match.group(1)
            else:
                class_name = full_class_name  # If the regex doesn't match, use the full name
            status = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DESCRSHORT'}).text
            print(f'{class_name}: {status}')
        except RequestException:
            print("Error occured, trying again...")
        time.sleep(3)
    
if __name__ == '__main__':
    main()