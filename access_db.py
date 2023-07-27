import logger_utility

logger = logger_utility.setup_logger(__name__, 'access_db.log')


async def add_term_info(conn, term_tuple):
    try:
        async with conn.cursor() as cur:
            await cur.execute('INSERT OR IGNORE INTO term_info VALUES (?, ?, ?)', term_tuple)
            await conn.commit()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to add term info {term_tuple}: {e}')


async def remove_term_info(conn, year_term):
    try:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM term_info WHERE year_term = ?', (year_term,))
            await conn.commit()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to remove year_term {year_term}: {e}')


async def update_hidden_value_for_term(conn, year_term, hidden_value):
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                UPDATE term_info
                SET hidden_value = ?
                WHERE year_term = ?
            """, (hidden_value, year_term))
            await conn.commit()
    except Exception as e:
        logger.error(f'DB error occurred while updating term info: {e}')


async def get_term_info(conn, year_term):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM term_info WHERE year_term = ?', (year_term,))
            return await cur.fetchone()
    except Exception as e:
        logger.error(f'DB error occurred while trying to get term info for {year_term}: {e}')
        return None


async def fetch_all_terms(conn):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM term_info')
            return await cur.fetchall()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to fetch all terms: {e}')
        return []


async def add_course(conn, course_tuple):
    try:
        async with conn.cursor() as cur:
            await cur.execute('INSERT OR IGNORE INTO courses VALUES (?, ?, ?)', course_tuple)
            await conn.commit()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to add course {course_tuple}: {e}')


async def remove_course(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('PRAGMA foreign_keys=ON')
            await cur.execute('DELETE FROM courses WHERE class_id = ?', (class_id,))
            await conn.commit()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to remove class_id {class_id}: {e}')


async def get_course_row(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM courses WHERE class_id = ?', (class_id,))
            return await cur.fetchone()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to get the course row for {class_id}: {e}')
        return None


async def update_course_status(conn, class_id, status):
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                UPDATE courses
                SET status = ?
                WHERE class_id = ?
            """, (status, class_id))
            await conn.commit()
    except Exception as e:
        logger.error(f'DB error occurred while trying to update course status for {class_id} to {status}: {e}')


async def fetch_all_courses(conn):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM courses')
            return await cur.fetchall()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to fetch all courses: {e}')
        return []


async def get_course_name_and_status(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT course_details.class_name, courses.status
                FROM course_details
                JOIN courses ON course_details.class_id = courses.class_id
                WHERE course_details.class_id = ?
            """, (class_id,))
            return await cur.fetchone()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to get course name and status for {class_id}: {e}')
        return None


async def get_course_with_term_info_row(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('''
                SELECT courses.*, term_info.hidden_value, term_info.term_id
                FROM courses
                INNER JOIN term_info ON courses.year_term = term_info.year_term
                WHERE courses.class_id = ?
            ''', (class_id,))
            return await cur.fetchone()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to get course with term values for {class_id}: {e}')
        return None
    
    
async def get_course_with_details_row(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT courses.*, course_details.class_name, course_details.times, course_details.professor
                FROM courses
                JOIN course_details ON courses.class_id = course_details.class_id
                WHERE courses.class_id = ?
            """, (class_id,))
            return await cur.fetchone()
    except Exception as e:
        logger.error(f'Error occurred while trying to get course and details for {class_id}: {e}')
        return None
    

async def add_course_details(conn, course_details_tuple):
    try:
        async with conn.cursor() as cur:
            await cur.execute('INSERT OR IGNORE INTO course_details VALUES (?, ?, ?, ?)', course_details_tuple)
            await conn.commit()
    except Exception as e:
        logger.error(f'DB error occurred while trying to add course details {course_details_tuple}: {e}')


async def get_course_details(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM course_details WHERE class_id = ?', (class_id,))
            return await cur.fetchone()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to get course details for {class_id}: {e}')
        return None


async def add_user_interest(conn, user_interests_tuple):
    try:
        async with conn.cursor() as cur:
            await cur.execute('INSERT OR IGNORE INTO user_interests VALUES (?, ?, ?)', user_interests_tuple)
            await conn.commit()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to add user interest {user_interests_tuple}: {e}')


async def remove_user_interest(conn, user_id, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM user_interests WHERE user_id = ? AND class_id = ?', (user_id, class_id))
            num_deleted_user_interests = cur.rowcount
            
            await cur.execute('SELECT COUNT(*) FROM user_interests WHERE class_id = ?', (class_id,))
            remaining_users_interested = await cur.fetchone()
            if remaining_users_interested[0] == 0:
                await cur.execute('PRAGMA foreign_keys=ON')
                await cur.execute('DELETE FROM courses WHERE class_id = ?', (class_id,))
                num_deleted_user_interests *= -1 # A way to indicate that the whole course was deleted from DB.
            
            await conn.commit()
            return num_deleted_user_interests
    except Exception as e:
        logger.error(f'DB error occurred while attempting to remove a user interest for {class_id}: {e}')
        return None


async def fetch_all_users_and_channels_for_course(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT user_id, channel_id FROM user_interests WHERE class_id = ?', (class_id,))
            return await cur.fetchall()
    except Exception as e:
        logger.error(f'DB error occurred while attempting to fetch all users interested in {class_id}: {e}')
        return []    


async def fetch_user_interests(conn, user_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT class_id FROM user_interests WHERE user_id = ?', (user_id,))
            classes = await cur.fetchall()
            return [class_[0] for class_ in classes]
    except Exception as e:
        logger.error(f'DB error occurred while attempting to fetch all user interests: {e}')
        return []
