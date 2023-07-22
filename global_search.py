import re
import base64
import logging
import logging_utility
import asyncio
import aiosqlite
import httpx
from bs4 import BeautifulSoup
import access_db

logging_utility.setup_logger('global_search.log')


class CourseTracker:
    def __init__(self):
        self.all_terms = None
        self.wait_time = 15
        
        self.semaphore = asyncio.Semaphore(5)
        self.session = None
        self.session_lock = asyncio.Lock()
        self.session_active = False
        
        self.payload = None
        self.headers = {'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }

    async def create_payload(self, term):
        try:
            async with aiosqlite.connect('classes.db') as conn:
                self.all_terms = {year_term: hidden_value for year_term, hidden_value, _ in await access_db.fetch_all_terms(conn)}
                if term in self.all_terms:
                    return {
                        'selectedInstName': 'Queens College | ',
                        'inst_selection': 'QNS01',
                        'selectedTermName': term,
                        'term_value': self.all_terms[term],
                        'next_btn': 'Next'
                    }
                raise ValueError(f'No row found in term_info for term {term}')
        except Exception as e:
            logging.error(f"Database access error: {e}")
            exit(1)
    
    async def create_session(self, term):
        async with self.session_lock:
            if not self.payload:
                self.payload = await self.create_payload(term)
            
            while True:
                try:
                    session = httpx.AsyncClient(headers=self.headers)
                    response = await session.post('https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController', data=self.payload)
                    response.raise_for_status()
                    self.session_active = True
                    self.wait_time = 15
                    return session
                except Exception as e:
                    self.session_active = False
                    logging.error(f'An error occured: {e}\nTrying again in {self.wait_time} seconds.')
                    await asyncio.sleep(self.wait_time)
                    self.wait_time = min(self.wait_time * 2, 300)
    
    async def encode_and_generate_params(self, class_id, term):
        encoded_class_number = base64.b64encode(class_id.encode()).decode()
        encoded_term = base64.b64encode(self.all_terms[term].encode()).decode()
        return {
            'class_number_searched': encoded_class_number,
            'session_searched': 'MQ==', # Hard coded '1'
            'term_searched': encoded_term,
            'inst_searched': 'UXVlZW5zIENvbGxlZ2U=' # Hard coded 'Queens College'
        }

    async def scrape_for_new_entry(self, session, class_id, term):
        async with self.semaphore:
            params = await self.encode_and_generate_params(class_id, term)
            try:
                response = await session.get('https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController', params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                error_message = soup.find('h1')
                if error_message and 'Ooops' in error_message.text:
                    raise ValueError('An error occured: the class does not exist.')
                
                webpage_class_id = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DATE_LONG'}).text
                if class_id != webpage_class_id:
                    raise ValueError('An error occured: the webpage class number does not match the request.')
                
                
                full_class_name = soup.find('span', {'id': 'DERIVED_CLSRCH_DESCR200'}).text
                status = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DESCRSHORT'}).text
                time = soup.find('span', {'id': 'MTG_SCHED$0'}).text
                professor = soup.find('span', {'id': 'MTG_INSTR$0'}).text
                if not full_class_name or not status or not time or not professor:
                    raise ValueError('Failed to find the specified span in the HTML.')
                class_name = re.search(r'([A-Z]+\s\d+)', full_class_name).group(1)
                self.wait_time = 15
                return (class_name, status, time, professor)
            except Exception as e:
                logging.error(f'An error occured: {e}')
                return None
    
    async def add_new_course_to_db(self, session, conn, class_id, term):
        result = await self.scrape_for_new_entry(session, class_id, term)
        if not result:
            logging.error('Something happened when scraping the webpage. Cannot add course.')
            return None
        class_name, status, time, professor = result
        try:
            await access_db.add_course(conn, (class_id, status, term))
            await access_db.add_course_details(conn, (class_id, class_name, time, professor))
            logging.info(f'Succesfully added {class_id}. These were the details scraped:')
            logging.info(f'{class_name}: {status}. Professor: {professor}. Time: {time}.')
            return result
        except Exception as e:
            logging.error(f'Database access error: {e}')
            return None
    
    async def scrape_webpage_status(self, session, params):
        async with self.semaphore:
            try:
                response = await session.get('https://globalsearch.cuny.edu/CFGlobalSearchTool/CFSearchToolController', params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                full_class_name = soup.find('span', {'id': 'DERIVED_CLSRCH_DESCR200'}).text
                class_id = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DATE_LONG'}).text
                status = soup.find('span', {'id': 'SSR_CLS_DTL_WRK_SSR_DESCRSHORT'}).text
                if not full_class_name or not class_id or not status:
                    raise ValueError('Failed to find the specified span in the HTML.')
                class_name = re.search(r'([A-Z]+\s\d+)', full_class_name).group(1)
                self.wait_time = 15
                return (class_name, class_id, status)
            except Exception as e:
                logging.error(f'An error occurred: {e}')
                return None
            
    async def sync_status_with_db(self, session, conn, params):
        result = await self.scrape_webpage_status(session, params)
        if not result:
            logging.error('Something happened when scraping the webpage. Cannot update status.')
            return None
        class_name, class_id, status = result
        try:
            _, stored_status = await access_db.get_course_name_and_status(conn, class_id)
            if status != stored_status:
                await access_db.update_course_status(conn, class_id, status)
                return (class_name, class_id, status, True)
            return (class_name, class_id, status, False)
        except Exception as e:
            logging.error(f'An error occurred: {e}')
            return None
    
    async def start_tracking(self, term):
        self.session = await self.create_session(term)
        while True:
            if not self.session_active:
                logging.info('Session is not active. Sleeping for 10 seconds.')
                await asyncio.sleep(10)
                continue
            try:
                async with aiosqlite.connect('classes.db') as conn:
                    all_courses = await access_db.fetch_all_courses(conn)
                    if not all_courses:
                        logging.info('No courses are in the database. Sleeping for 30 seconds.')
                        await asyncio.sleep(30)
                        continue
            except Exception as e:
                logging.error(f'Database access error: {e}')
                exit(1)
                
            params = [await self.encode_and_generate_params(class_number, year_term) for class_number, status, year_term in all_courses]
            try:
                async with aiosqlite.connect('classes.db') as conn:
                    tasks = [self.sync_status_with_db(self.session, conn, param) for param in params]
                    for completed_task in asyncio.as_completed(tasks):
                        result = await completed_task
                        if result:
                            class_name, class_id, status, changed = result
                            if changed:
                                logging.info(f'Course Status Changed: {class_name}-{class_id}: {status}')
                            print(f'{class_name}-{class_id}: {status}')
                        else:
                            print('Error: No results.')
                    await asyncio.sleep(5)
            except Exception as e:
                logging.error(f'An error occurred: {e}\nTrying to recreate session in {self.wait_time} seconds.')
                self.session_active = False
                await self.session.aclose()
                self.session = await self.create_session()


async def main():
    tracker = CourseTracker()
    await tracker.start_tracking('2023 Fall Term')


if __name__ == '__main__':
    asyncio.run(main())
