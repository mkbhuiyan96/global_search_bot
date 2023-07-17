import re
import httpx
import asyncio
import aiosqlite
from bs4 import BeautifulSoup


class CourseTracker:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)
        self.wait_time = 15

    async def get_urls_from_db(self):
        conn = await aiosqlite.connect('classes.db')
        try:
            cur = await conn.cursor()
            await cur.execute('SELECT url FROM courses')
            rows = await cur.fetchall()
            return [row[0] for row in rows]
        finally:
            await conn.close()

    async def track_course(self, client, url):
        async with self.semaphore:
            try:
                response = await client.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                full_class_name = soup.find('span', {'id': 'DERIVED_CLSRCH_DESCR200'}).text.strip()
                class_number = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DATE_LONG'}).text
                status = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DESCRSHORT'}).text
                if not full_class_name or not class_number or not status:
                    raise ValueError('An error occurred: failed to find the specified span in the HTML.')
                
                class_name = re.search(r'([A-Z]+\s\d+)', full_class_name).group(1)
                print(f'{class_name}-{class_number}: {status}')
                self.wait_time = 15
            except ValueError as e:
                print(e)
                exit(1)
            except Exception as e:
                print(f'An error occured: {e}\nWhile trying to get information about\n{url}\nTrying again in {self.wait_time} seconds.')
                await asyncio.sleep(self.wait_time)
                self.wait_time = min(self.wait_time * 2, 300)

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
                
                urls = await self.get_urls_from_db()
                tasks = [self.track_course(client, url) for url in urls]
                await asyncio.gather(*tasks)
                self.wait_time = 15
            except Exception as e:
                print(f'An error occurred: {e}\nWhile trying to create the client. Trying again in {self.wait_time} seconds.')
                await asyncio.sleep(self.wait_time)
                self.wait_time = min(self.wait_time * 2, 300)
            finally:
                await client.aclose()
                await asyncio.sleep(2)


async def main():
    tracker = CourseTracker()
    await tracker.start_tracking()

if __name__ == "__main__":
    asyncio.run(main())