# CUNYFirst Auto Enroller
I originally intended to create this to try and attempt to enroll in a class automatically using HTTP requests. I then realized that I would have to store student's credentials to be able to automatically enroll them via the Discord bot, so instead I have provided the file "schedule_builder.py" which will allow a user to Add/Drop a course by simply giving the course number.

## CUNY Global Search Web Scraper
Since I did not feel comfortable with storing user's credentials, I decided to just scrape CUNY Global Search and constantly check the course status. This code is used by a Discord bot which will allow one to use slash commands to add a course to be tracked, notifying them when the status of the course changes.

## Instructions
1) Create a Discord bot at the [Discord Developer Portal](https://discord.com/developers/applications), if you haven't already done so.
2) From the bot section, copy the bot's token. This token is effectively the bot's password — do not share it with anyone unless you want them to be able to do anything with your bot!
3) You need to set this token as an environmental variable. You can make a .env file, or if you know how to make environmental variables for your OS, do that. You must then update the code in "discord_bot.py" to use this variable.
4) Under the OAUTH2 section, use the URL Generator to get an invitation link for your bot. Select 'bot' and the necessary permissions ('Read Messages/View Channels', 'Send Messages', and 'Use slash commands').
5) Use the generated URL to invite your bot to a Discord server where you have admin rights.
6) You can install the dependencies by running "pip install -r requirements.txt" on your console in the directory for this project.
7) I have the setup hook that registers the slash commands commented out because there is a rate limit. You will need to uncomment this the first time you run it to register the commands.
8) You should be able to then run the Python file "discord_bot.py" once you set up these variables properly.

### Side Note
I have included an SSL certificate because the client for Schedule Builder will not work without it. If you don't trust it, you can [download it yourself](https://www.digicert.com/kb/digicert-root-certificates.htm). The certificate is DigiCert TLS RSA SHA256 2020 CA1.
