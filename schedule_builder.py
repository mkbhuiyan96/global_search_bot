import time
import os
import ssl
import aiosqlite
import httpx
from bs4 import BeautifulSoup
import access_db
import logger_utility

logger = logger_utility.setup_logger(__name__, 'schedule_builder.log')
context = ssl.create_default_context()
context.load_verify_locations(cafile='DigiCertTLSRSASHA2562020CA1-1.crt.pem')

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

async def send_request(action, term, prev_class_id, new_class_id):
    try:
        async with httpx.AsyncClient(headers=headers, verify=context, follow_redirects=True) as client:
            await client.get('https://cssa.cunyfirst.cuny.edu/psc/cnycsprd/EMPLOYEE/SA/s/WEBLIB_VSB.TRANSFER_FUNCS.FieldFormula.IScript_RedirectVSBuilder?INSTITUTION=LAG01')
            await client.post('https://ssologin.cuny.edu/oam/server/auth_cred_submit', data=payload)
            return await perform_action(client, action, term, prev_class_id, new_class_id)
    except Exception as e:
        logger.error(f'An error occurred while trying to send a request to Schedule Builder: {e}')
        return None


async def perform_action(client, action, term, prev_class_id, new_class_id):
    action = action.lower()
    if action == 'drop':
        a = 'E'
        b = 'G'
    elif action == 'swap':
        if prev_class_id == new_class_id:
            raise ValueError('You are trying to do a swap when the classes are the same!')
        a = b = 'E'
    elif action == 'add':
        a = 'T'
        b = 'E'
    else:
        raise ValueError(f'Invalid action parameter in prepare_action_params(). Expected "drop", "add", or "swap", but got {action}.')
    
    try:
        async with aiosqlite.connect('classes.db') as conn:
            term_info = await access_db.get_term_info(conn, term)
            if not term_info:
                raise ValueError(f'No row found in term_info for term: {term}')
    except Exception as e:
        logger.error(f'An error occured when trying to access the DB: {e}')
        return None
    
    _, hidden_value, term_ID = term_info
    prev_class_string = f'QNS01--{hidden_value}_{prev_class_id}--'
    new_class_string = f'QNS01--{hidden_value}_{new_class_id}--'
    params = {
        'statea': a,
        'keya': prev_class_string,
        'stateb': b,
        'keyb': new_class_string,
        '_': f'{int(time.time() * 1000)}'
    }
    await client.get(f'https://sb.cunyfirst.cuny.edu/api/enroll-options', params=params)

    params = {
        'conditionalAddDrop': '0', # What triggers this to be a value other than 0?
        'statea0': a,
        'keya0': prev_class_string,
        'vaa0': '99zz', # Eventually change this to get the proper validation keys.
        'vab0': '99zz', # Although it will still correctly perform the action.
        'stateb0': b,
        'keyb0': new_class_string,
        'schoolTermId': term_ID,
        '_': f'{int(time.time() * 1000)}'
    }
    response = await client.get(f'https://sb.cunyfirst.cuny.edu/api/perform-action', params=params)
    soup = BeautifulSoup(response.text, 'html.parser')
    message = soup.find('div', {'class': 'actionInfoMessage'}).text
    return message
