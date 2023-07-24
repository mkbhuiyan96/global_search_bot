# CUNYFirst Auto Enroller
This is some code to try and attempt to enroll in a class automatically using Python and the HTTPX library. I then realized that I would have to store student's credentials to be able to automatically enroll them via the discord bot, so instead I have provided the file "schedule_builder.py" which will allow a user to Add/Drop a course by simply giving the course number.

## CUNY Global Search Web Scraper
Since I did not feel comfortable with storing user's credentials, I fell back to the original plan of just scraping CUNY Global Search and constantly checking the course status. This code is used by a Discord bot that will allow them to use slash commands to add a course to be tracked, notifying them when the status of the course changes.

## Instructions
1) Create a Discord bot if you haven't already done so, over at https://discord.com/developers/applications
2) From the bot section, you'll need to get the token. This is basically the login information for the bot, so do not share this with anyone, because they will be able to do anything with your bot if so.
3) From OAUTH2 and then the URL Generator, I usually check off 'bot' and then the relevant permissions. I usually enable 'Read Messages/View Channels', 'Send Messages' and 'Use slash commands'. I'm kind of shaky on if I need all 3 of them honestly, but whatever.
4) You will then have a URL that will you can use to invite your bot from your browser. You'll have to log into Discord, and you'll also need a server where you are admin.
5) You'll need to get the GUILD_ID for your server, which you can get by enabling Developer mode on Discord. You'll then be able to right click a server and Copy Server ID.
6) You should be able to then run the Python file "discord_bot.py" once you set up these variables properly.

### Side Note
I have included an SSL certificate because the client for Schedule Builder will not work without it. If you don't trust it, you can download it yourself from https://www.digicert.com/kb/digicert-root-certificates.htm. The certificate is DigiCert TLS RSA SHA256 2020 CA1.
