import time
import os
from dotenv import load_dotenv
import asyncio
import aiosqlite
import httpx
from bs4 import BeautifulSoup


async def get_term_info(term):
    conn = await aiosqlite.connect('classes.db')
    try:
        cur = await conn.cursor()
        await cur.execute('SELECT hidden_value, term_id FROM term_info WHERE year_term = ?', (term,))
        result = await cur.fetchone()
        if result is None:
            raise ValueError(f'No row found in term_info with year_term = "{term}"')
        return result
    finally:
        await conn.close()


async def send_request(client, choice, term, prev_class, new_class):
    hidden_value, school_term_ID = await get_term_info(term)    
    prev_class_string = f'QNS01--{hidden_value}_{prev_class}--'
    new_class_string = f'QNS01--{hidden_value}_{new_class}--'
    
    choice = choice.lower()
    if choice == 'drop':
        a = 'E'
        b = 'G'
    elif choice == 'swap':
        if prev_class == new_class:
            raise ValueError('You are trying to do a swap when the classes are the same!')
        a = b = 'E'
    elif choice == 'add':
        a = 'T'
        b = 'E'
    else:
        raise ValueError(f'Invalid choice parameter in prepare_action_params(). Expected "drop", "add", or "swap", but got {choice}.')
    
    params = {
        'statea': f'{a}',
        'keya': prev_class_string,
        'stateb': f'{b}',
        'keyb': new_class_string,
        '_': f'{int(time.time() * 1000)}'
    }
    await client.get(f'https://sb.cunyfirst.cuny.edu/api/enroll-options', params=params)

    params = {
        'conditionalAddDrop': '0', # What triggers this to be a value other than 0?
        'statea0': f'{a}',
        'keya0': prev_class_string,
        'vaa0': '99zz', # Eventually change this to get the proper validation keys.
        'vab0': '99zz', # Although it will still correctly perform the action.
        'stateb0': f'{b}',
        'keyb0': new_class_string,
        'schoolTermId': f'{school_term_ID}',
        '_': f'{int(time.time() * 1000)}'
    }
    response = await client.get(f'https://sb.cunyfirst.cuny.edu/api/perform-action', params=params)
    soup = BeautifulSoup(response.text, 'html.parser')
    message = soup.find('div', {'class': 'actionInfoMessage'}).text
    return message


async def main():
    load_dotenv()
    headers = {'User-Agent': 
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/114.0.0.0 Safari/537.36'
    }
    payload = {
        'usernameH': f'{os.getenv("USERNAMEH")}',
        'username': f'{os.getenv("USER")}',
        'password': f'{os.getenv("PASSWORD")}',
        'submit': ''
    }
    
    try:
        async with httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True) as client:
            await client.get('https://cssa.cunyfirst.cuny.edu/psc/cnycsprd/EMPLOYEE/SA/s/WEBLIB_VSB.TRANSFER_FUNCS.FieldFormula.IScript_RedirectVSBuilder?INSTITUTION=LAG01')
            await client.post('https://ssologin.cuny.edu/oam/server/auth_cred_submit', data=payload)
            
            response = await send_request(client, 'drop', '2023 Fall', '23427', '23427')
            print(response)
            response = await send_request(client, 'add', '2023 Fall', '23427', '23427')
            print(response)
    except Exception as e:
        print(f'An error occurred: {e}')


if __name__ == '__main__':
    asyncio.run(main())
