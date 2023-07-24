import asyncio
import aiosqlite
import os
from dotenv import load_dotenv
import signal
import logger_utility
from typing import Literal
import discord
from discord import app_commands
import access_db
import global_search

load_dotenv()
logger = logger_utility.setup_logger(__name__, 'discord_bot.log')


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self) 
        self.tracker = global_search.CourseTracker()
        self.course_number_range = app_commands.Range[int, 1000, 99999]
        self.available_terms = Literal['2023 Fall Term']
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        await start_tracking('2023 Fall Term')

    # async def setup_hook(self):
    #     """This copies the global commands over to each guild.
    #     Although if you never call .sync() with empty parameters, it's a good way to test your commands
    #     without having to actually be rate limited for the global command sync."""
    #     async for guild in self.fetch_guilds():
    #         self.tree.copy_global_to(guild=guild)
    #         await self.tree.sync(guild=guild)
    #     await self.tree.sync()
    
    def signal_handler(self, signal, frame):
        print('Signal received, cleaning up...')
        if self.tracker.session:
            self.loop.create_task(self.tracker.session.aclose())
            print('Sent request to close session.')
        exit(0)


client = MyClient(intents=discord.Intents.all())


async def start_tracking(term):
    await client.tracker.initialize_db()
    client.tracker.session = await client.tracker.create_session(term)
    
    while True:
        if not client.tracker.session_active:
            logger.info('Session is not active. Sleeping for 10 seconds.')
            await asyncio.sleep(10)
            continue
        try:
            async with aiosqlite.connect('classes.db') as conn:
                all_courses = await access_db.fetch_all_courses(conn)
                if not all_courses:
                    logger.info('No courses are in the database. Sleeping for 10 seconds.')
                    await asyncio.sleep(10)
                    continue
        except Exception as e:
            logger.error(f'Error occured while trying to fetch all courses from the db: {e}')
            break
            
        params = [await client.tracker.encode_and_generate_params(class_number, year_term) for class_number, _, year_term in all_courses]
        try:
            async with aiosqlite.connect('classes.db') as conn:
                tasks = [client.tracker.sync_status_with_db(client.tracker.session, conn, param) for param in params]
                for task in asyncio.as_completed(tasks):
                    completed_task = await task
                    if completed_task:
                        class_name, class_id, class_status, status_changed = completed_task
                        if status_changed:
                            await notify_users(class_name, class_id, class_status)
                        print(f'{class_name}-{class_id}: {class_status}')
                    else:
                        logger.error('An error occured when trying to sync webpage status with db: No results.')
                await asyncio.sleep(5)
        except Exception as e:
            logger.error(f'An error occurred: {e}\nTrying to recreate session in {client.tracker.wait_time} seconds.')
            client.tracker.session_active = False
            await client.tracker.session.aclose()
            client.tracker.session = await client.tracker.create_session()
    await client.tracker.session.aclose()

async def notify_users(class_name, course_number, status):
    try:
        async with aiosqlite.connect('classes.db') as conn:
            user_channel_tuples = await access_db.fetch_all_users_and_channels_for_course(conn, course_number)
            for user_id, channel_id in user_channel_tuples:
                user = client.get_user(int(user_id))
                channel = client.get_channel(int(channel_id))
                if user and channel:
                    await channel.send(f'{user.mention}, {class_name}-{course_number} is now {status}!')
    except Exception as e:
        logger.error(f'An error occured when trying to notify users about a status change: {e}')


@client.tree.command()
@app_commands.describe(course_number='Course Number')
async def get_course_info(interaction: discord.Interaction, course_number: client.course_number_range):
    """Retreives basic information about a course saved on the database."""
    try:
        async with aiosqlite.connect('classes.db') as conn:
            course_row = await access_db.get_course_row(conn, str(course_number))
            course_details = await access_db.get_course_details(conn, str(course_number))
            if course_row and course_details: # Refactor in access_db to use a union
                _, status, term = course_row
                class_id, class_name, times, professor = course_details
                await interaction.response.send_message(f'{class_name}-{class_id}: {status}\n{term}\nProfessor: {professor}\nTimes: {times}')
            else:
                await interaction.response.send_message('That course is not in the database.', ephemeral=True)
    except Exception as e:
        logger.error(f'An error occured when trying to get course information on {course_number}: {e}')
        await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)        


@client.tree.command()
@app_commands.describe(course_number='Class Number from Global Search')
async def check_course_status(interaction: discord.Interaction, course_number: client.course_number_range, term: client.available_terms):
    """Checks CUNY Global Search website for course status."""
    try:
        response = await client.tracker.scrape_webpage_status(
            client.tracker.session, params=await client.tracker.encode_and_generate_params(str(course_number), term)
        )
        if response:
            class_name, class_id, status = response
        else:
            logger.warning(f'Response was empty when trying to check course status.')
            await interaction.response.send_message(f"Got back nothing when trying to get that course's status.", ephemeral=True)
            return
        if str(course_number) != class_id:
            raise ValueError('Course number did not match when checking the website.')
        await interaction.response.send_message(f'{class_name}-{class_id}: {status}')
    except Exception as e:
        logger.error(f"An error occured when attempting to check on that course's status: {e}")
        await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)


@client.tree.command()
@app_commands.describe(course_number='Course Number')
async def add_course(interaction: discord.Interaction, course_number: client.course_number_range, term: client.available_terms):
    """Adds a course to be tracked by the bot."""
    database_value = None
    async with aiosqlite.connect('classes.db') as conn:    
        try:
            database_value = await access_db.get_course_name_and_status(conn, str(course_number))
        except Exception as e:
            logger.error(f'An error occured when trying acess the db to add a new course: {e}')
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)
            return

        if not database_value: # This means we have to create a new database entry.        
            try:
                response = await client.tracker.add_new_course_to_db(client.tracker.session, conn, str(course_number), term)
                await access_db.add_user_interest(conn, (interaction.user.id, str(course_number), interaction.channel.id))
                class_name, status, _, _ = response
                await interaction.response.send_message(f'{class_name}-{course_number}: {status}')
            except Exception as e:
                logger.error(f'An error occured when trying to add a new entry to the db: {e}')
                await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)
                return
        else:
            try:
                await access_db.add_user_interest(conn, (interaction.user.id, str(course_number), interaction.channel.id))
                class_name, status = database_value
                await interaction.response.send_message(f'{class_name}-{course_number}: {status}')
            except Exception as e:
                logger.error(f'An error occured: {e}')
                await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)
                return


@client.tree.command()
@app_commands.describe(course_number='Course Number')
async def remove_course(interaction: discord.Interaction, course_number: client.course_number_range):
    """Removes a course from being tracked by you."""
    deleted_rows = 0
    class_name = None
    try:
        async with aiosqlite.connect('classes.db') as conn:
            class_name, _ = await access_db.get_course_name_and_status(conn, course_number)
            deleted_rows = await access_db.remove_user_interest(conn, interaction.user.id, str(course_number))
    except Exception as e:
        logger.error(f'An error occured when accessing the db to remove a course: {e}')
        await interaction.response.send_message(f'An error occured: {e}', ephemeral=True)
        return
    if deleted_rows < 0:
        await interaction.response.send_message(f'Removed {class_name}-{course_number} from your tracked courses.\n'
            'No one else was tracking this course, so the course was removed from the database.'
        )
    elif deleted_rows > 0:
        await interaction.response.send_message(f'Removed {class_name}-{course_number} from your tracked courses.')
    else:
        await interaction.response.send_message('Did not find that course to remove from your tracked courses.', ephemeral=True)


@client.tree.command()
async def fetch_all_tracked_courses(interaction: discord.Interaction):
    """Returns a list of ALL courses currently being tracked by the bot."""
    try:
        async with aiosqlite.connect('classes.db') as conn:
            courses = await access_db.fetch_all_courses(conn)
            if courses:
                message = ''
                for class_id, _, _ in courses:
                    class_name, status = await access_db.get_course_name_and_status(conn, class_id)
                    message += f'{class_name}-{class_id}: {status}\n'
                await interaction.response.send_message(message)
            else:
                await interaction.response.send_message('No courses are currently being tracked.', ephemeral=True)
    except Exception as e:
        logger.error(f'An error occured when trying to retrieve all courses in the db: {e}')
        await interaction.response.send_message(f'An error occured: {e}', ephemeral=True)     


@client.tree.command()
async def get_my_tracked_courses(interaction: discord.Interaction):
    """Returns a list of courses YOU have requested to be notified about."""
    try:
        async with aiosqlite.connect('classes.db') as conn:
            class_ids = await access_db.fetch_user_interests(conn, interaction.user.id)
            if class_ids:
                message = ''
                for class_id in class_ids:
                    class_name, status = await access_db.get_course_name_and_status(conn, class_id)
                    message += f'{class_name}-{class_id}: {status}\n'
                await interaction.response.send_message(message)
            else:
                await interaction.response.send_message('No courses are currently being tracked.', ephemeral=True)
    except Exception as e:
        logger.error(f"An error occured when trying to access {interaction.user.name}'s tracke courses: {e}")
        await interaction.response.send_message(f'An error occured: {e}', ephemeral=True) 
    

client.run(os.getenv('DISCORD_TOKEN'))
