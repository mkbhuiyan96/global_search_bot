import aiosqlite
import asyncio
import logging
import logging_utility

logging_utility.setup_logger('access_db.log')


async def create_term_info(conn):
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT OR IGNORE INTO term_info VALUES
                    ('2024 Spring Term', '????', '3202420'),
                    ('2023 Fall Term', '1239', '3202330'),
                    ('2023 Summer Term', '1236', '3202320'),
                    ('2023 Spring Term', '1232', '3202310')
            """)
        await conn.commit()
    except Exception as e:
        logging.error(f"Error occurred: {e}")


async def update_term_info(conn, term_id, hidden_value):
    try:
        async with conn.cursor() as cur:
            await cur.execute("""
                UPDATE term_info
                SET hidden_value = ?
                WHERE term_id = ?
            """, (hidden_value, term_id))
            await conn.commit()
    except Exception as e:
        logging.error(f"Error occurred: {e}")


async def get_term_info(conn, year_term):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM term_info WHERE year_term = ?', (year_term,))
            term_info = await cur.fetchone()
            return term_info
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return None


async def fetch_all_terms(conn):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM term_info')
            return await cur.fetchall()
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return []


async def add_course(conn, course_tuple):
    try:
        async with conn.cursor() as cur:
            await cur.execute('INSERT OR IGNORE INTO courses VALUES (?, ?, ?)', course_tuple)
            await conn.commit()
    except Exception as e:
        logging.error(f"Error occurred: {e}")


async def remove_course(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('PRAGMA foreign_keys=ON;')
            await cur.execute('DELETE FROM courses WHERE class_id = ?', (class_id,))
            await conn.commit()
    except Exception as e:
        logging.error(f"Error occurred: {e}")


async def get_course_row(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM courses WHERE class_id = ?', (class_id,))
            term_info = await cur.fetchone()
            return term_info
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return None


async def fetch_all_courses(conn):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM courses')
            return await cur.fetchall()
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return []


async def get_course_with_term_values(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('''
                SELECT courses.*, term_info.hidden_value, term_info.term_id
                FROM courses
                INNER JOIN term_info ON courses.year_term = term_info.year_term
                WHERE courses.class_id = ?
            ''', (class_id,))
            row = await cur.fetchone()
            return row
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return None


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
        logging.error(f"Error occurred: {e}")
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
        logging.error(f"Error occurred: {e}")


async def add_course_details(conn, course_details_tuple):
    try:
        async with conn.cursor() as cur:
            await cur.execute('INSERT OR IGNORE INTO course_details VALUES (?, ?, ?, ?)', course_details_tuple)
            await conn.commit()
    except Exception as e:
        logging.error(f"Error occurred: {e}")


async def get_course_details(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT * FROM course_details WHERE class_id = ?', (class_id,))
            details = await cur.fetchone()
            return details
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return None


async def add_user_interest(conn, user_interests_tuple):
    try:
        async with conn.cursor() as cur:
            await cur.execute('INSERT OR IGNORE INTO user_interests VALUES (?, ?, ?)', user_interests_tuple)
            await conn.commit()
    except Exception as e:
        logging.error(f"Error occurred: {e}")


async def remove_user_interest(conn, user_id, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM user_interests WHERE user_id = ? AND class_id = ?', (user_id, class_id))
            num_deleted_rows = cur.rowcount
            await cur.execute('SELECT COUNT(*) FROM user_interests WHERE class_id = ?', (class_id,))
            remaining = await cur.fetchone()
            if remaining[0] == 0:
                await cur.execute('PRAGMA foreign_keys=ON;')
                await cur.execute('DELETE FROM courses WHERE class_id = ?', (class_id,))
                num_deleted_rows = cur.rowcount
                if num_deleted_rows > 0:
                    print(f"Successfully deleted {num_deleted_rows} rows from courses.")
                else:
                    print("No rows were deleted from courses.")
                await conn.commit()
                return -1 * num_deleted_rows
            else:
                await conn.commit()
                return num_deleted_rows
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return None


async def fetch_all_users_and_channels_for_course(conn, class_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT user_id, channel_id FROM user_interests WHERE class_id = ?', (class_id,))
            return await cur.fetchall()
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return []    


async def fetch_user_interests(conn, user_id):
    try:
        async with conn.cursor() as cur:
            await cur.execute('SELECT class_id FROM user_interests WHERE user_id = ?', (user_id,))
            classes = await cur.fetchall()
            return [class_[0] for class_ in classes]
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return []
