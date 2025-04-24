import os
import asyncio
import discord
import requests
import logging
import json
import hashlib
import subprocess
from discord.ext import tasks, commands
from dotenv import load_dotenv
from discord import app_commands
from discord.ui import Button, View

logging.basicConfig(filename="bot_errors.log", level=logging.ERROR)

def log_error(e):
    logging.error(f"{e}")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_USER_IDS_FILE = "server_user_ids.json"

ROBLOX_COOKIES = [
    os.getenv("ROBLOX_COOKIE_1"),
    os.getenv("ROBLOX_COOKIE_2"),
    os.getenv("ROBLOX_COOKIE_3")
]

cookie_index = 0 

def get_next_cookie():
    global cookie_index
    cookie = ROBLOX_COOKIES[cookie_index]
    cookie_index = (cookie_index + 1) % len(ROBLOX_COOKIES) 
    return cookie

if not TOKEN:
    raise EnvironmentError("DISCORD_TOKEN is not set in the environment variables.")

def load_server_user_ids():
    try:
        with open(SERVER_USER_IDS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}  
    except Exception as e:
        log_error(e)
        print(f"Failed to load server user IDs: {e}")
        return {}

def save_server_user_ids():
    try:
        with open(SERVER_USER_IDS_FILE, 'w') as file:
            json.dump(server_user_ids, file, indent=4)
    except Exception as e:
        log_error(e)
        print(f"Failed to save server user IDs: {e}")

server_user_ids = load_server_user_ids()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

tree = bot.tree

data_cache = {}

GROUP_ID = 15574158
group_cache = {
    "members": set(),
    "last_shout": None
}

STATUS_MAP = {
    0: "Offline",
    1: "Online",
    2: "In Game",
    3: "In Studio"
}

LAST_CHANGELOG_FILE = "last_changelog.json"

def load_last_changelog():
    try:
        if os.path.exists(LAST_CHANGELOG_FILE):
            with open(LAST_CHANGELOG_FILE, "r") as file:
                return json.load(file)
        return {}
    except Exception as e:
        log_error(e)
        return {}

def save_last_changelog(version):
    try:
        with open(LAST_CHANGELOG_FILE, "w") as file:
            json.dump({"version": version}, file)
    except Exception as e:
        log_error(e)



def extract_latest_changelog(changelog_content: str) -> str:
    """
    Extracts the latest changelog entry from the changelog content.
    Assumes the changelog is formatted with headings (e.g., ## [Version]).
    """
    try:
        lines = changelog_content.splitlines()
        latest_entry = []
        in_latest_section = False

        for line in lines:
            if line.startswith("## "):  
                if in_latest_section:
                    break  
                in_latest_section = True
            if in_latest_section:
                latest_entry.append(line)

        return "\n".join(latest_entry).strip()
    except Exception as e:
        log_error(e)
        print("Failed to extract the latest changelog entry.")
        return "Failed to extract the latest changelog entry."

def get_roblox_presence(user_id: str) -> str:
    url = "https://presence.roblox.com/v1/presence/users"
    headers = {
        "Content-Type": "application/json",
        "Cookie": f".ROBLOSECURITY={get_next_cookie()}"
    }
    json_data = {"userIds": [int(user_id)]}

    try:
        response = requests.post(url, json=json_data, headers=headers)
        response.raise_for_status()
        data = response.json()
        user_data = data["userPresences"][0]
        status = STATUS_MAP.get(user_data["userPresenceType"], "Unknown")
        return status
    except Exception as e:
        log_error(e)
        print(f"Failed to get status for user {user_id}: {e}")
        return "Unknown"

def get_user_details(user_id: str):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        user_data = response.json()

        display_name = user_data.get("displayName", "No display name")
        username = user_data.get("name", "No username")
        description = user_data.get("description", "No description available.")
        is_banned = user_data.get("isBanned", False)

        return {
            "display_name": display_name,
            "username": username,
            "description": description,
            "is_banned": is_banned
        }

    except Exception as e:
        log_error(e)
        print(f"Failed to get user details for user {user_id}: {e}")
        return {
            "display_name": "No display name",
            "username": "No username",
            "description": "No description available.",
            "is_banned": False
        }

def get_file_hash(file_path):
    """
    Calculate the hash of a file to detect changes.
    """
    try:
        with open(file_path, "rb") as file:
            return hashlib.md5(file.read()).hexdigest()
    except FileNotFoundError:
        return None

async def check_and_send_changelog():
    """
    Check if the changelog.md file has changed and send the latest changelog if it has.
    """
    changelog_file = "changelog.md"
    last_changelog_file = "last_changelog.json"

    current_hash = get_file_hash(changelog_file)

    try:
        with open(last_changelog_file, "r") as file:
            last_data = json.load(file)
            last_hash = last_data.get("hash")
    except FileNotFoundError:
        last_hash = None

    if current_hash != last_hash:
        print("Changelog has changed. Sending updates...")

        with open(changelog_file, "r") as file:
            changelog_content = file.read()
        latest_changelog = extract_latest_changelog(changelog_content)

        if latest_changelog and not latest_changelog.startswith("Failed"):
            version = latest_changelog.splitlines()[0].strip("## ").strip()
            await send_changelog_to_all_guilds(latest_changelog, version)

        with open(last_changelog_file, "w") as file:
            json.dump({"hash": current_hash}, file)
    else:
        print("No changes detected in changelog.md.")

async def pull_and_check_changelog():
    """
    Perform a git pull and check for changes in the changelog.md file.
    """
    try:
        result = subprocess.run(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
        print(result.stderr)

        await check_and_send_changelog()
    except Exception as e:
        log_error(e)
        print("Failed to pull changes or check the changelog.")

@tasks.loop(minutes=10)  
async def update_changelog_task():
    await pull_and_check_changelog()

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")

    update_changelog_task.start()

    if check_status.is_running():
        check_status.cancel()
    check_status.start()

    try:
        synced = await tree.sync()  
        print(f"Slash commands re-synced successfully: {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print("Starting tasks...")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="Invalid Command",
            description="The command you entered does not exist. Here are the available commands:",
            color=discord.Color.red()
        )
        embed.add_field(name="!track", value="Track a user by their Roblox ID or username.\nUsage: `!track <user_id>` or `!track <username>`", inline=False)
        embed.add_field(name="!untrack", value="Untrack a user by their Roblox ID.\nUsage: `!untrack <user_id>`", inline=False)
        embed.add_field(name="!whois", value="Get details about a Roblox user.\nUsage: `!whois <user_id>` or `!whois <username>`", inline=False)
        embed.add_field(name="!tracking", value="List all currently tracked users.\nUsage: `!tracking`", inline=False)
        embed.add_field(name="!setup", value="Set up the bot's categories and channels.\nUsage: `!setup`", inline=False)
        embed.add_field(name="!unsetup", value="Remove the bot's categories and channels.\nUsage: `!unsetup`", inline=False)
        embed.add_field(name="!h", value="Show this help message.\nUsage: `!h`", inline=False)

        await ctx.send(embed=embed, delete_after=30)

@tasks.loop(seconds=30)
async def check_status():
    print(f"Checking status for servers: {server_user_ids.keys()}")  
    for guild_id, user_ids in server_user_ids.items():
        guild = bot.get_guild(int(guild_id))
        if not guild:
            print(f"Guild with ID {guild_id} not found.")  
            continue

        if guild_id not in data_cache:
            data_cache[guild_id] = {}

        soul_category = discord.utils.get(guild.categories, name="Soul")
        if not soul_category:
            print(f"⚠️ Soul category not found in guild {guild.name}. Skipping...")
            continue

        status_channel = discord.utils.get(soul_category.channels, name="status-updates")
        if not status_channel:
            print(f"⚠️ Status Updates channel not found in guild {guild.name}. Skipping...")
            continue

        print(f"Processing guild: {guild.name}, channel: {status_channel.name}")  

        for user_id in user_ids:
            if user_id not in data_cache[guild_id]:
                data_cache[guild_id][user_id] = {"last_status": None}

            current_status = get_roblox_presence(user_id)
            previous_status = data_cache[guild_id][user_id]["last_status"]

            if current_status == previous_status:
                continue

            data_cache[guild_id][user_id]["last_status"] = current_status

            user_details = get_user_details(user_id)

            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
            try:
                response = requests.get(avatar_url)
                response.raise_for_status()
                avatar_data = response.json()
                avatar_url = avatar_data["data"][0]["imageUrl"]
            except Exception as e:
                log_error(e)
                avatar_url = None

            embed_color = discord.Color.blue() 
            if current_status == "In Game":
                embed_color = discord.Color.green()  
            elif current_status == "Offline":
                embed_color = discord.Color.red() 

            embed = discord.Embed(
                title=f"{user_details['username']}",
                color=embed_color
            )
            embed.add_field(name="Status", value=current_status, inline=False)
            embed.add_field(name="Last Online", value="Recently" if current_status != "Offline" else "Unknown", inline=False)
            embed.add_field(name="Description", value=user_details["description"], inline=False)
            embed.add_field(name="Is Banned", value="Yes" if user_details["is_banned"] else "No", inline=False)
            embed.add_field(name="USER ID", value=user_id, inline=False)
            embed.add_field(name="DISPLAY NAME", value=user_details["display_name"], inline=False)
            embed.add_field(name="USERNAME", value=user_details["username"], inline=False)

            if avatar_url:
                embed.set_thumbnail(url=avatar_url)

            await status_channel.send(embed=embed)

@bot.event
async def on_guild_join(guild):
    """
    Sends a welcome message with the bot's README content when added to a new server.
    """
    default_channel = next((channel for channel in guild.text_channels if channel.permissions_for(guild.me).send_messages), None)
    if default_channel:
        await default_channel.send("This is a fallback message!")

    if not default_channel:
        print(f"⚠️ No suitable channel found in guild {guild.name} to send the welcome message.")
        return

    try:
        with open("README.md", "r") as readme_file:
            readme_content = readme_file.read()
    except Exception as e:
        log_error(e)
        print("⚠️ Failed to read the README.md file.")
        return

    about_section = []
    commands_section = []
    in_about = False
    in_commands = False

    for line in readme_content.splitlines():
        if line.startswith("## About"):
            in_about = True
            in_commands = False
        elif line.startswith("### Commands"):
            in_about = False
            in_commands = True
        elif line.startswith("## "): 
            in_about = False
            in_commands = False

        if in_about:
            about_section.append(line)
        elif in_commands:
            commands_section.append(line)

    about_text = "\n".join(about_section).strip()
    commands_text = "\n".join(commands_section).strip()

    commands_chunks = [commands_text[i:i + 1024] for i in range(0, len(commands_text), 1024)]

    welcome_embed = discord.Embed(
        title="Welcome to SOUL Bot!",
        description="Thank you for adding SOUL Bot to your server! Here's how to get started:",
        color=discord.Color.blue()
    )
    welcome_embed.add_field(name="About", value=about_text[:1024], inline=False)
    welcome_embed.set_footer(text="SOULBOT MADE BY GRAVE @ soullessgraves.us")

    commands_embeds = []
    for i, chunk in enumerate(commands_chunks):
        commands_embed = discord.Embed(
            title=f"Commands (Page {i + 1}/{len(commands_chunks)})",
            description=chunk,
            color=discord.Color.blue()
        )
        commands_embed.set_footer(text="SOULBOT MADE BY GRAVE @ soullessgraves.us")
        commands_embeds.append(commands_embed)

    setup_embed = discord.Embed(
        title="Setup Instructions",
        description="Run the `!setup` command to create the necessary categories and channels for the bot to function properly.",
        color=discord.Color.blue()
    )
    setup_embed.set_footer(text="SOULBOT MADE BY GRAVE @ soullessgraves.us")

    await default_channel.send(embed=welcome_embed)
    for embed in commands_embeds:
        await default_channel.send(embed=embed)
    await default_channel.send(embed=setup_embed)

@bot.command(name="track")
async def track_command(ctx, *inputs: str):
    guild_id = str(ctx.guild.id)  
    if guild_id not in server_user_ids:
        server_user_ids[guild_id] = []  

    guild = ctx.guild
    soul_category = discord.utils.get(guild.categories, name="Soul")
    logs_channel = discord.utils.get(soul_category.channels, name="addedremoved-users-logs") if soul_category else None

    for input_value in inputs:
        if input_value.isdigit():
            user_id = input_value
        else:
            url = f"https://users.roblox.com/v1/usernames/users"
            try:
                response = requests.post(url, json={"usernames": [input_value]})
                response.raise_for_status()
                data = response.json()
                if not data["data"]:
                    error_embed = discord.Embed(
                        title="Invalid Input",
                        description=f"No user found with the username '{input_value}'.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=error_embed, delete_after=30)
                    continue
                user_id = str(data["data"][0]["id"])
            except Exception as e:
                log_error(e)
                error_embed = discord.Embed(
                    title="Error",
                    description=f"Failed to resolve username '{input_value}' to a user ID.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed, delete_after=30)
                continue

        if user_id in server_user_ids[guild_id]:
            user_details = get_user_details(user_id)

            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
            try:
                response = requests.get(avatar_url)
                response.raise_for_status()
                avatar_data = response.json()
                avatar_url = avatar_data["data"][0]["imageUrl"]
            except Exception as e:
                log_error(e)
                avatar_url = None

            already_tracked_embed = discord.Embed(
                title="User Already Tracked",
                description=f"**Username:** {user_details['username']}\n**User ID:** {user_id}",
                color=discord.Color.orange()
            )
            already_tracked_embed.add_field(name="Display Name", value=user_details["display_name"], inline=False)
            if avatar_url:
                already_tracked_embed.set_thumbnail(url=avatar_url)
            await ctx.send(embed=already_tracked_embed)
        else:
            server_user_ids[guild_id].append(user_id)

            user_details = get_user_details(user_id)

            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
            try:
                response = requests.get(avatar_url)
                response.raise_for_status()
                avatar_data = response.json()
                avatar_url = avatar_data["data"][0]["imageUrl"]
            except Exception as e:
                log_error(e)
                avatar_url = None

            if logs_channel:
                log_embed = discord.Embed(
                    title="User Added to Tracking",
                    description=f"**Username:** {user_details['username']}\n**User ID:** {user_id}",
                    color=discord.Color.green()
                )
                log_embed.add_field(name="Display Name", value=user_details["display_name"], inline=False)
                if avatar_url:
                    log_embed.set_thumbnail(url=avatar_url)
                await logs_channel.send(embed=log_embed)

    save_server_user_ids()

@bot.command(name="untrack")
async def untrack_command(ctx, user_input: str):
    guild_id = str(ctx.guild.id) 
    if guild_id not in server_user_ids:
        server_user_ids[guild_id] = []  

    if user_input.isdigit():
        user_id = user_input
    else:
        url = f"https://users.roblox.com/v1/usernames/users"
        try:
            response = requests.post(url, json={"usernames": [user_input]})
            response.raise_for_status()
            data = response.json()
            if not data["data"]:
                error_embed = discord.Embed(
                    title="User Not Found",
                    description=f"No user found with the username '{user_input}'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed, delete_after=30)
                return
            user_id = str(data["data"][0]["id"])
        except Exception as e:
            log_error(e)
            error_embed = discord.Embed(
                title="Error",
                description=f"Failed to resolve username '{user_input}' to a user ID.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed, delete_after=30)
            return

    guild = ctx.guild
    soul_category = discord.utils.get(guild.categories, name="Soul")
    logs_channel = discord.utils.get(soul_category.channels, name="addedremoved-users-logs") if soul_category else None

    if user_id in server_user_ids[guild_id]:
        server_user_ids[guild_id].remove(user_id)
        save_server_user_ids()

        user_details = get_user_details(user_id)

        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
        try:
            response = requests.get(avatar_url)
            response.raise_for_status()
            avatar_data = response.json()
            avatar_url = avatar_data["data"][0]["imageUrl"]
        except Exception as e:
            log_error(e)
            avatar_url = None

        if logs_channel:
            log_embed = discord.Embed(
                title="User Removed from Tracking",
                description=f"**Username:** {user_details['username']}\n**User ID:** {user_id}",
                color=discord.Color.red()
            )
            log_embed.add_field(name="Display Name", value=user_details["display_name"], inline=False)
            if avatar_url:
                log_embed.set_thumbnail(url=avatar_url)
            await logs_channel.send(embed=log_embed)
    else:
        error_embed = discord.Embed(
            title="User Not Tracked",
            description=f"User ID {user_id} is not being tracked.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=30)

@bot.command(name="setup")
async def setup_command(ctx):
    guild = ctx.guild

    soul_category = discord.utils.get(guild.categories, name="Soul")
    if soul_category:
        error_embed = discord.Embed(
            title="Setup Error",
            description="The **Soul** category already exists.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=30)
        return

    embed = discord.Embed(
        title="Setup Permission",
        description="I can create the following category and channels:\n\n"
                    "**Soul**:\n"
                    "- **Added/Removed Users Logs**: Logs added and removed users.\n"
                    "- **Status Updates**: Posts status updates for tracked users.\n"
                    "- **Changelogs**: Posts bot changelogs.\n\n"
                    "Do you want me to create these? (yes/no)",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)
        if msg.content.lower() == "no":
            await ctx.send("Setup canceled.", delete_after=30)
            return
    except asyncio.TimeoutError:
        await ctx.send("Setup timed out. Please run the command again.", delete_after=30)
        return

    soul_category = await guild.create_category("Soul")
    await guild.create_text_channel("Added/Removed Users Logs", category=soul_category)
    await guild.create_text_channel("Status Updates", category=soul_category)
    await guild.create_text_channel("Changelogs", category=soul_category)

    await ctx.send("Setup complete!", delete_after=30)


@bot.command(name="unsetup")
async def unsetup_command(ctx):
    guild = ctx.guild

    category = discord.utils.get(guild.categories, name="Soul")
    if not category:
        error_embed = discord.Embed(
            title="Unsetup Error",
            description="The **Soul** category does not exist.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=30)
        return

    for channel in category.channels:
        await channel.delete()
    await category.delete()

    await ctx.send("Unsetup complete! The **Soul** category and its channels have been deleted.", delete_after=30)


@bot.command(name="tracking")
async def tracking_command(ctx):
    guild_id = str(ctx.guild.id)  
    if guild_id not in server_user_ids or not server_user_ids[guild_id]:
        await ctx.send("⚠️ No users are currently being tracked in this server.")
        return

    embed = discord.Embed(title="Tracking List", description="Currently tracked users", color=discord.Color.blue())

    for user_id in server_user_ids[guild_id]:
        user_details = get_user_details(user_id)
        embed.add_field(
            name=f"{user_details['username']} (ID: {user_id})",
            value=f"**Display Name:** {user_details['display_name']}\n**Description:** {user_details['description']}",
            inline=False
        )

    await ctx.send(embed=embed)


@bot.command(name="whois")
async def whois_command(ctx, user_input: str):
    """
    Fetch and display details about a Roblox user by user ID or username.
    """
    if user_input.isdigit():
        user_id = user_input
    else:
        url = f"https://users.roblox.com/v1/usernames/users"
        try:
            response = requests.post(url, json={"usernames": [user_input]})
            response.raise_for_status()
            data = response.json()
            if not data["data"]:
                error_embed = discord.Embed(
                    title="User Not Found",
                    description=f"No user found with the username '{user_input}'.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed, delete_after=30)
                return
            user_id = str(data["data"][0]["id"])
        except Exception as e:
            log_error(e)
            error_embed = discord.Embed(
                title="Error",
                description=f"Failed to resolve username '{user_input}' to a user ID.",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed, delete_after=30)
            return

    user_details = get_user_details(user_id)
    if user_details["username"] == "No username":
        error_embed = discord.Embed(
            title="User Not Found",
            description=f"No user found with the ID '{user_id}'.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=30)
        return

    avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
    try:
        response = requests.get(avatar_url)
        response.raise_for_status()
        avatar_data = response.json()
        avatar_url = avatar_data["data"][0]["imageUrl"]
    except Exception as e:
        log_error(e)
        avatar_url = None

    embed = discord.Embed(
        title=f"Whois for {user_details['username']}",
        description=f"**Display Name:** {user_details['display_name']}\n**Description:** {user_details['description']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="User ID", value=user_id, inline=False)
    embed.add_field(name="Is Banned", value="Yes" if user_details["is_banned"] else "No", inline=False)
    embed.set_thumbnail(url=avatar_url)

    await ctx.send(embed=embed)


@bot.command(name="whois_display")
async def whois_display_command(ctx, *, display_name: str):
    """
    Fetch and display details about Roblox users by display name.
    """
    url = "https://users.roblox.com/v1/users/search"
    try:
        response = requests.get(url, params={"keyword": display_name, "limit": 10})  
        response.raise_for_status()
        data = response.json()
        users = data.get("data", [])
    except Exception as e:
        log_error(e)
        error_embed = discord.Embed(
            title="Error",
            description=f"⚠️ Failed to search for users with the display name '{display_name}'.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=30)
        return

    if not users:
        error_embed = discord.Embed(
            title="No Users Found",
            description=f"No users found with the display name '{display_name}'.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed, delete_after=30)
        return

    pages = []
    for user in users:
        user_id = user.get("id", "Unknown")
        username = user.get("name", "Unknown")
        display_name = user.get("displayName", "Unknown")

        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
        try:
            response = requests.get(avatar_url)
            response.raise_for_status()
            avatar_data = response.json()
            avatar_url = avatar_data["data"][0]["imageUrl"]
        except Exception as e:
            log_error(e)
            avatar_url = None

        embed = discord.Embed(
            title=f"Whois for Display Name: {display_name}",
            description=f"**Username:** {username}\n**User ID:** {user_id}",
            color=discord.Color.blue()
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        pages.append(embed)

    current_page = 0

    async def send_page(page_index):
        return await ctx.send(embed=pages[page_index], view=view)

    async def previous_callback(interaction):
        nonlocal current_page
        if current_page > 0:
            current_page -= 1
            await interaction.response.edit_message(embed=pages[current_page], view=view)

    async def next_callback(interaction):
        nonlocal current_page
        if current_page < len(pages) - 1:
            current_page += 1
            await interaction.response.edit_message(embed=pages[current_page], view=view)

    async def finish_callback(interaction):
        await interaction.message.delete()
        await ctx.message.delete()

    previous_button = Button(label="⬅️ Previous", style=discord.ButtonStyle.primary)
    next_button = Button(label="➡️ Next", style=discord.ButtonStyle.primary)
    finish_button = Button(label="Finished", style=discord.ButtonStyle.danger)

    previous_button.callback = previous_callback
    next_button.callback = next_callback
    finish_button.callback = finish_callback

    view = View(timeout=30) 
    if len(pages) > 1:
        view.add_item(previous_button)
        view.add_item(next_button)
    view.add_item(finish_button)

    message = await send_page(current_page)

    async def on_timeout():
        await message.delete()
        await ctx.message.delete()

    view.on_timeout = on_timeout


@bot.command(name="h")
async def help_command(ctx):
    embed = discord.Embed(
        title="Help - Available Commands",
        description="Here are the available commands and how to use them:",
        color=discord.Color.blue()
    )
    embed.add_field(name="!track", value="Track a user by their Roblox ID or username.\nUsage: `!track <user_id>` or `!track <username>`", inline=False)
    embed.add_field(name="!untrack", value="Untrack a user by their Roblox ID.\nUsage: `!untrack <user_id>`", inline=False)
    embed.add_field(name="!whois", value="Get details about a Roblox user.\nUsage: `!whois <user_id>` or `!whois <username>`", inline=False)
    embed.add_field(name="!whois_display", value="Get details about Roblox users by display name.\nUsage: `!whois_display <display_name>`", inline=False)
    embed.add_field(name="!tracking", value="List all currently tracked users.\nUsage: `!tracking`", inline=False)
    embed.add_field(name="!setup", value="Set up the bot's categories and channels.\nUsage: `!setup`", inline=False)
    embed.add_field(name="!unsetup", value="Remove the bot's categories and channels.\nUsage: `!unsetup`", inline=False)
    embed.add_field(name="!h", value="Show this help message.\nUsage: `!h`", inline=False)

    await ctx.send(embed=embed)


@bot.command(name="changelog")
@commands.has_permissions(administrator=True)  
async def changelog_command(ctx, *, message: str):
    """
    Sends a changelog update to the Changelogs channel.
    """
    guild = ctx.guild

    await send_changelog_update(guild, message)

    confirmation_embed = discord.Embed(
        title="Changelog Sent",
        description="Your changelog update has been sent to the **Changelogs** channel.",
        color=discord.Color.green()
    )
    await ctx.send(embed=confirmation_embed, delete_after=10)

@bot.command(name="push_changelog_all")
@commands.has_permissions(administrator=True)
async def push_changelog_all_command(ctx, *, message: str):
    """
    Pushes a changelog message to the Changelogs channel in all servers.
    """
    for guild in bot.guilds:
        await send_changelog_update(guild, message)

    confirmation_embed = discord.Embed(
        title="Changelog Sent to All Servers",
        description="Your changelog update has been sent to the **Changelogs** channel in all servers.",
        color=discord.Color.green()
    )
    await ctx.send(embed=confirmation_embed, delete_after=10)


async def send_changelog_update(guild, message: str):
    """
    Sends a changelog update to the Changelogs channel in the specified guild.
    """
    soul_category = discord.utils.get(guild.categories, name="Soul")
    changelogs_channel = discord.utils.get(soul_category.channels, name="changelogs") if soul_category else None

    if not changelogs_channel:
        print(f"⚠️ Changelogs channel not found in guild {guild.name}.")
        return

    embed = discord.Embed(
        title="Changelog Update",
        description=message,
        color=discord.Color.gold()
    )
    await changelogs_channel.send(embed=embed)


async def send_changelog_to_all_guilds(changelog_message: str, version: str):
    """
    Sends the latest changelog to the Changelogs channel in all guilds if it hasn't been sent already.
    """
    last_changelog = load_last_changelog()
    if last_changelog.get("version") == version:
        print("Changelog has already been sent. Skipping...")
        return

    for guild in bot.guilds:
        soul_category = discord.utils.get(guild.categories, name="Soul")
        changelogs_channel = discord.utils.get(soul_category.channels, name="changelogs") if soul_category else None

        if not changelogs_channel:
            print(f"⚠️ Changelogs channel not found in guild {guild.name}.")
            continue

        embed = discord.Embed(
            title="Changelog Update",
            description=changelog_message,
            color=discord.Color.gold()
        )
        await changelogs_channel.send(embed=embed)

    save_last_changelog(version)


if __name__ == "__main__":
    bot.run(TOKEN)
