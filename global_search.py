import re
import httpx
import asyncio
import aiosqlite
from bs4 import BeautifulSoup


class CourseTracker:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)
        self.client_lock = asyncio.Lock()
        self.client = None

    async def get_urls_from_db(self):
        conn = await aiosqlite.connect('classes.db')
        cur = await conn.cursor()
        await cur.execute('SELECT url FROM classes')
        rows = await cur.fetchall()
        
        urls = []
        for row in rows:
            urls.append(row[0])
        await conn.close()
        return urls

    async def create_client(self):
        async with self.client_lock:
            headers = {'User-Agent': 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/114.0.0.0 Safari/537.36'
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

    async def track_course(self, url):
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

    async def start_tracking(self):
        self.client = await self.create_client()
        
        while True:
            tasks = []
            urls = await self.get_urls_from_db()
            for url in urls:
                await asyncio.sleep(0.1)
                tasks.append(asyncio.ensure_future(self.track_course(url)))
            await asyncio.gather(*tasks)


def main():
    tracker = CourseTracker()
    asyncio.run(tracker.start_tracking())

if __name__ == "__main__":
    main()