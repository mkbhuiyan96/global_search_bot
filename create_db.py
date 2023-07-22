import aiosqlite
import asyncio
import logger_utility

logger = logger_utility.setup_logger(__name__, 'create_db.log')

async def initialize_tables(conn):
    try:
        async with conn.cursor() as cursor:    
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS term_info (
                    year_term TEXT PRIMARY KEY,
                    hidden_value TEXT,
                    term_id TEXT
                )
            """)
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    class_id TEXT PRIMARY KEY,
                    status TEXT,
                    year_term TEXT REFERENCES term_info(year_term)
                )
            """)
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS course_details (
                    class_id TEXT PRIMARY KEY REFERENCES courses(class_id) ON DELETE CASCADE,
                    class_name TEXT,
                    times TEXT,
                    professor TEXT
                )
            """)
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interests (
                    user_id TEXT,
                    class_id TEXT REFERENCES courses(class_id) ON DELETE CASCADE,
                    channel_id TEXT,
                    PRIMARY KEY (user_id, class_id)
                )
            """)
            await conn.commit()
            logger.info("Tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error occurred while initializing tables: {e}")

async def main():
    try:
        async with aiosqlite.connect('classes.db') as conn:
            await initialize_tables(conn)
    except Exception as e:
        logger.error(f"Error occurred while connecting to the database: {e}")

if __name__ == "__main__":
    asyncio.run(main())
