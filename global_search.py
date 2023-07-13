import re
import httpx
import asyncio
import sqlite3
from bs4 import BeautifulSoup

sem = asyncio.Semaphore(5)


async def create_client():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
    payload = {
        'selectedInstName': 'Queens College | ',
        'inst_selection': 'QNS01',
        'selectedTermName': 'Fall 2023',
        'term_value': '1239',
        'next_btn': 'Next'
    }
    client = httpx.AsyncClient(headers=headers)
    while True:
        try: 
            response = await client.post('https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController', data=payload)
            response.raise_for_status()
            return client
        except Exception as e:
            print(f'Error occurred while starting a session: {e}\nTrying again in 5 minutes.')
            await asyncio.sleep(300)


async def track_courses(client, url):
    async with sem:
        try:
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            full_class_name = soup.find('span', {'id': 'DERIVED_CLSRCH_DESCR200'}).text.strip()
            
            match = re.search(r'([A-Z]+\s\d+)', full_class_name)
            if match:
                class_name = match.group(1)
            else:
                class_name = full_class_name
            status = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DESCRSHORT'}).text
            print(f'{class_name}: {status}')
        except Exception as e:
            print(f'An error occured: {e}\nWhile trying to get information about\n{url}\n')


async def main():
    client = await create_client()
    urls = ['https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController?class_number_searched=MjQyMDQ=&session_searched=MQ==&term_searched=MTIzOQ==&inst_searched=UXVlZW5zIENvbGxlZ2U=',
           'https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController?class_number_searched=MjU1MzI=&session_searched=MQ==&term_searched=MTIzOQ==&inst_searched=UXVlZW5zIENvbGxlZ2U=',
           'https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController?class_number_searched=MjM3MDQ=&session_searched=MQ==&term_searched=MTIzOQ==&inst_searched=UXVlZW5zIENvbGxlZ2U=']
    
    while True:
        tasks = []
        for url in urls:
            tasks.append(asyncio.ensure_future(track_courses(client, url)))
        await asyncio.gather(*tasks)

asyncio.run(main())