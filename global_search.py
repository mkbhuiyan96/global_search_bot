import re
import httpx
import asyncio
import sqlite3
from bs4 import BeautifulSoup


class CourseTracker:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)
        self.client_lock = asyncio.Lock()
        self.client = None

    async def create_client(self):
        async with self.client_lock:
            headers = {'User-Agent': 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
            }
            payload = {
                'selectedInstName': 'Queens College | ',
                'inst_selection': 'QNS01',
                'selectedTermName': 'Fall 2023',
                'term_value': '1239',
                'next_btn': 'Next'
            }
            self.client = httpx.AsyncClient(headers=headers)
            
            while True:
                try:
                    response = await self.client.post('https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController', data=payload)
                    response.raise_for_status()
                    return self.client
                except Exception as e:
                    print(f'Error occurred while starting a session: {e}\nTrying again in 10 minutes.')
                    await asyncio.sleep(600)

    async def track_courses(self, url):
        async with self.semaphore:
            try:
                response = await self.client.get(url)
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
                print(f'An error occured: {e}\nWhile trying to get information about\n{url}\nTrying again in 10 minutes.')
                await asyncio.sleep(600)
                async with self.client_lock:
                    self.client = await self.create_client()

    async def main(self):
        self.client = await self.create_client()
        urls = ['https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController?class_number_searched=MjQyMDQ=&session_searched=MQ==&term_searched=MTIzOQ==&inst_searched=UXVlZW5zIENvbGxlZ2U=',
               'https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController?class_number_searched=MjU1MzI=&session_searched=MQ==&term_searched=MTIzOQ==&inst_searched=UXVlZW5zIENvbGxlZ2U=',
               'https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController?class_number_searched=MjM3MDQ=&session_searched=MQ==&term_searched=MTIzOQ==&inst_searched=UXVlZW5zIENvbGxlZ2U=']
        
        while True:
            tasks = []
            for url in urls:
                await asyncio.sleep(0.1)
                tasks.append(asyncio.ensure_future(self.track_courses(url)))
            await asyncio.gather(*tasks)


if __name__ == "__main__":
    tracker = CourseTracker()
    asyncio.run(tracker.main())