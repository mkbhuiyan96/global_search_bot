import asyncio
import aiosqlite
import os
import signal
import logging
import logging_utility
from typing import Literal #, Optional
import discord
from discord import app_commands
#from discord.ext import tasks, commands
import create_db
import access_db
import global_search
#import schedule_builder

logging_utility.setup_logger('discord_bot.log')


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self) 
        self.tracker = global_search.CourseTracker()
        self.MY_GUILD = discord.Object(id=os.environ.get('GUILD_ID'))
        self.course_number_range = app_commands.Range[int, 1000, 99999]
        self.available_terms = Literal['2023 Fall Term']

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        self.tree.copy_global_to(guild=self.MY_GUILD)
        await self.tree.sync(guild=self.MY_GUILD)


client = MyClient(intents=discord.Intents.all())


async def start_tracking(term):
    client.tracker.session = await client.tracker.create_session(term)
    while True:
        if not client.tracker.session_active:
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
            break
            
        params = [await client.tracker.encode_and_generate_params(class_number, year_term) for class_number, status, year_term in all_courses]
        try:
            async with aiosqlite.connect('classes.db') as conn:
                tasks = [client.tracker.sync_status_with_db(client.tracker.session, conn, param) for param in params]
                for completed_task in asyncio.as_completed(tasks):
                    result = await completed_task
                    if result:
                        class_name, class_id, status, changed = result
                        if changed:
                            await notify_users(class_name, class_id, status)
                        print(f'{class_name}-{class_id}: {status}')
                    else:
                        logging.error('Error: No results.')
                await asyncio.sleep(5)
        except Exception as e:
            logging.error(f'An error occurred: {e}\nTrying to recreate session in {client.tracker.wait_time} seconds.')
            client.tracker.session_active = False
            await client.tracker.session.aclose()
            client.tracker.session = await client.tracker.create_session()


@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user} (ID: {client.user.id})')
    async with aiosqlite.connect('classes.db') as conn:
        await create_db.initialize_tables(conn)
        await access_db.create_term_info(conn)
    await start_tracking('2023 Fall Term')


def signal_handler(signal, frame):
    print('Signal received, cleaning up...')
    if client.tracker.session:
        client.loop.create_task(client.tracker.session.aclose())
        print('Sent request to close session.')
    exit(0)


# Set the signal handler for SIGINT and SIGTERM
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def notify_users(class_name, course_number, status):
    try:
        async with aiosqlite.connect('classes.db') as conn:
            user_channel_tuples = await access_db.fetch_all_users_and_channels_for_course(conn, course_number)
            for user_id, channel_id in user_channel_tuples:
                user = client.get_user(int(user_id))
                channel = client.get_channel(int(channel_id))
                await channel.send(f'{user.mention}, {class_name}-{course_number} is now {status}!')
    except Exception as e:
        logging.error(f'An error occured: {e}')
        

# @client.tree.command()
# @app_commands.describe(action='The action to perform on Schedule Builder')
# async def perform_action(
#     interaction: discord.Interaction,
#     action: Literal['Add', 'Drop', 'Swap'],
#     prev: client.course_number_range,
#     new: client.course_number_range
# ):
#     """Add/Drop a course on Schedule Builder"""
#     await interaction.response.send_message(f'{action} {prev} {new}')


@client.tree.command()
@app_commands.describe(course_number='Course Number')
async def get_course_details(interaction: discord.Interaction, course_number: client.course_number_range):
    """Retreives saved course info from the database."""
    try:
        async with aiosqlite.connect('classes.db') as conn:
            course_row = await access_db.get_course_row(conn, str(course_number))
            course_details = await access_db.get_course_details(conn, str(course_number))
            if course_row and course_details:
                _, status, term = course_row
                class_id, class_name, times, professor = course_details
                await interaction.response.send_message(f'{class_name}-{class_id}: {status}\n{term}\nProfessor: {professor}\nTimes: {times}')
            else:
                await interaction.response.send_message('That course is not in the database.', ephemeral=True)
    except Exception as e:
        logging.error(f'An error occured: {e}')
        await interaction.response.send_message(f'Error occurred: {e}', ephemeral=True)        


@client.tree.command()
@app_commands.describe(course_number='Class Number from Global Search')
async def check_course_status(interaction: discord.Interaction, course_number: client.course_number_range, term: client.available_terms):
    """Checks CUNY Global Search for course status."""
    try:
        class_name, class_id, status = await client.tracker.scrape_webpage_status(
            client.tracker.session, params=await client.tracker.encode_and_generate_params(str(course_number), term)
        )
        if str(course_number) != class_id:
            raise ValueError('The course number did not match when checking the website.')
        await interaction.response.send_message(f'{class_name}-{class_id}: {status}')
    except Exception as e:
        logging.error(f'An error occured: {e}')
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
            logging.error(f'An error occured: {e}')
            await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)
            return
        
        if not database_value:        
            try:
                result = await client.tracker.add_new_course_to_db(client.tracker.session, conn, str(course_number), term)
                await access_db.add_user_interest(conn, (interaction.user.id, str(course_number), interaction.channel.id))
                class_name, status, _, _ = result
                await interaction.response.send_message(f'{class_name}-{course_number}: {status}')
            except Exception as e:
                logging.error(f'An error occured: {e}')
                await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)
                return
        else:
            try:
                await access_db.add_user_interest(conn, (interaction.user.id, str(course_number), interaction.channel.id))
                class_name, status = database_value
                await interaction.response.send_message(f'{class_name}-{course_number}: {status}')
            except Exception as e:
                logging.error(f'An error occured: {e}')
                await interaction.response.send_message(f'An error occurred: {e}', ephemeral=True)
                return


@client.tree.command()
@app_commands.describe(course_number='Course Number')
async def remove_course(interaction: discord.Interaction, course_number: client.course_number_range):
    """Removes a course from being tracked."""
    deleted_rows = 0
    class_name = None
    try:
        async with aiosqlite.connect('classes.db') as conn:
            class_name, _ = await access_db.get_course_name_and_status(conn, course_number)
            deleted_rows = await access_db.remove_user_interest(conn, interaction.user.id, str(course_number))
    except Exception as e:
        logging.error(f'An error occured: {e}')
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


client.run(os.environ.get('DISCORD_TOKEN'))