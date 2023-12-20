
from app.common.database.repositories import users
from app.common.constants.regexes import USERNAME
from discord.errors import Forbidden
from app.objects import Context

import asyncio
import hashlib
import discord
import config
import bcrypt
import app

@app.session.commands.register(['register'])
async def create_account(context: Context):
    """Create an account"""
    author = context.message.author

    if users.fetch_by_discord_id(author.id):
        await context.message.channel.send(
            'You already have an account linked to your discord profile.',
            reference=context.message,
            mention_author=True
        )
        return

    app.session.logger.info(f'[{author}] -> Starting registration process...')

    try:
        dm = await author.create_dm()
        await dm.send(
            'You are about to register an account on osuTitanic.\n'
            'Please enter a username!'
        )
    except Forbidden:
        await context.message.channel.send(
            'Failed to send a dm to your account. Please check your discord privacy settings!',
            reference=context.message,
            mention_author=True
        )
        return

    if type(context.message.channel) is not discord.DMChannel:
        await context.message.channel.send(
            content='Please check your dms!',
            reference=context.message,
            mention_author=True
        )

    def check(msg: discord.Message):
        return (
            msg.author.id == author.id and
            isinstance(msg.channel, discord.DMChannel)
        )

    try:
        while True:
            msg: discord.Message = await app.session.bot.wait_for(
                'message',
                check=check,
                timeout=60
            )

            username = msg.content.strip()
            safe_name = username.lower() \
                    .replace(' ', '_')

            if not USERNAME.match(username):
                await dm.send('Your username has invalid characters. Please try again!')
                continue

            if users.fetch_by_safe_name(safe_name):
                await dm.send('A user with that name already exists. Please try again!')
                continue

            break

        app.session.logger.info(
            f'[{author}] -> Selcted username "{username}"'
        )

        await dm.send(f'Your username will be "{username}".\n')
        await dm.send(
            'Please enter a password for you to log in!\n'
            '(Type "abort" to abort the registration)'
        )

        msg: discord.Message = await app.session.bot.wait_for(
            'message',
            check=check,
            timeout=60
        )

        password: str = msg.content

        if password.lower() == 'abort':
            app.session.logger.info(f'[{author}] -> Registration was cancelled')
            await dm.send('The registration was cancelled.')
            return

        async with dm.typing():
            hashed_password = bcrypt.hashpw(
                password=hashlib.md5(password.encode()) \
                                .hexdigest() \
                                .encode(),
                salt=bcrypt.gensalt()
            ).decode()

            app.session.logger.info(
                f'[{author}] -> Creating user...'
            )

            user = users.create(
                username=username,
                safe_name=safe_name,
                email='user@example.com', # TODO
                pw_bcrypt=hashed_password,
                country='XX',
                activated=True,
                discord_id=author.id,
                permissions=1 if not config.FREE_SUPPORTER else 5
            )

            if not user:
                app.session.logger.warning(f'[{author}] -> Failed to register user.')
                await dm.send(
                    'Something went wrong during the registration. Please contact a developer!'
                )
                return

            app.session.logger.info(
                f'[{author}] -> Trying to get profile picture from discord...'
            )

            try:
                # Add "Member" role
                if type(context.message.channel) is discord.DMChannel:
                    guild = app.session.bot.guilds[0]
                    member = guild.get_member(context.message.author.id)

                    await member.add_roles(
                        discord.utils.get(guild.roles, name='Member')
                    )

                else:
                    await context.message.author.add_roles(
                        discord.utils.get(author.guild.roles, name='Member')
                    )
            except Exception as e:
                app.session.logger.warning(
                    f'[{author}] -> Failed to assign role: {e}',
                    exc_info=e
                )

        app.session.logger.info(f'[{author}] -> Registration finished!')

        await dm.send(
            "Thank you! You can now try to log in.\n"
            "If something doesn't work, feel free to ping a developer or admin.\n"
            "Have fun playing on this server!"
        )

    except asyncio.TimeoutError:
        app.session.logger.warning(
            'Registration was cancelled due to timeout.'
        )
        await dm.send(
            content='The registration was cancelled due to inactivity.\n'
                    'Please try again!'
        )


