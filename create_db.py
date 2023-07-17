import aiosqlite
import asyncio


async def create_tables(conn):
    cursor = await conn.cursor()
    
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
            year_term TEXT,
            url TEXT,
            FOREIGN KEY(year_term) REFERENCES term_info(year_term)
        )
    """)
    await cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_details (
            class_id TEXT,
            class_name TEXT,
            times TEXT,
            professor TEXT,
            FOREIGN KEY(class_id) REFERENCES courses(class_id)
        )
    """)
    await cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_interests (
            user_id TEXT,
            class_id TEXT,
            FOREIGN KEY(class_id) REFERENCES courses(class_id)
        )
    """)
    
    await conn.commit()


async def main():
    conn = await aiosqlite.connect('classes.db')
    await create_tables(conn)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())