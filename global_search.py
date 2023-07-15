import re
import httpx
import asyncio
import aiosqlite
from bs4 import BeautifulSoup


class CourseTracker:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)

    async def get_urls_from_db(self):
        conn = await aiosqlite.connect('classes.db')
        try:
            cur = await conn.cursor()
            await cur.execute('SELECT url FROM classes')
            rows = await cur.fetchall()

            urls = []
            for row in rows:
                urls.append(row[0])
            return urls
        finally:
            await conn.close()

    async def track_course(self, client, url):
        async with self.semaphore:
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
                print(f'An error occured: {e}\nWhile trying to get information about\n{url}\nTrying again in 1 minute.')
                await asyncio.sleep(60)

    async def start_tracking(self):
        payload = {
            'selectedInstName': 'Queens College | ',
            'inst_selection': 'QNS01',
            'selectedTermName': 'Fall 2023',
            'term_value': '1239',
            'next_btn': 'Next'
        }
        while True:
            try:
                client = httpx.AsyncClient(
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
                )
                response = await client.post('https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController', data=payload)
                response.raise_for_status()
                tasks = []
                urls = await self.get_urls_from_db()
                for url in urls:
                    tasks.append(self.track_course(client, url))
                await asyncio.gather(*tasks)
            except Exception as e:
                print(f'An error occurred: {e}\nWhile trying to create the client. Trying again in 1 minute.')
                await asyncio.sleep(60)
            finally:
                await client.aclose()
                await asyncio.sleep(2)


async def main():
    tracker = CourseTracker()
    await tracker.start_tracking()

if __name__ == "__main__":
    asyncio.run(main())