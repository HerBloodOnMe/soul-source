import os
import asyncio
import discord
import requests
import logging
import json
import hashlib
import subprocess
import random
import string
from discord.ext import tasks, commands
from dotenv import load_dotenv
from discord import app_commands
from discord.ui import Button, View

logging.basicConfig(filename="bot_errors.log", level=logging.ERROR)

def log_error(e):
    logging.error(f"{e}")

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_USER_IDS_FILE = "server_user_ids.json"  # File to store server-specific user IDs

ROBLOX_COOKIES = [
    os.getenv("ROBLOX_COOKIE_1"),
    os.getenv("ROBLOX_COOKIE_2"),
    os.getenv("ROBLOX_COOKIE_3")
]

cookie_index = 0  # Global index to track the current cookie

def get_next_cookie():
    global cookie_index
    cookie = ROBLOX_COOKIES[cookie_index]
    cookie_index = (cookie_index + 1) % len(ROBLOX_COOKIES)  # Move to the next cookie
    return cookie

if not TOKEN:
    raise EnvironmentError("DISCORD_TOKEN is not set in the environment variables.")

# Load server-specific user IDs from file
def load_server_user_ids():
    try:
        with open(SERVER_USER_IDS_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}  # Return an empty dictionary if the file doesn't exist
    except Exception as e:
        log_error(e)
        print(f"Failed to load server user IDs: {e}")
        return {}

# Save server-specific user IDs to file
def save_server_user_ids():
    try:
        with open(SERVER_USER_IDS_FILE, 'w') as file:
            json.dump(server_user_ids, file, indent=4)
    except Exception as e:
        log_error(e)
        print(f"Failed to save server user IDs: {e}")

# Dictionary to store user IDs for each server
server_user_ids = load_server_user_ids()

# Dictionary to store tracked items per server
server_item_ids = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Use the existing bot.tree instead of creating a new CommandTree
tree = bot.tree

# Tracks previous statuses per server
data_cache = {}

GROUP_ID = # add a group ID
group_cache = {
    "members": set(),
    "last_shout": None
}

# Mapping ROBLOX status codes
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


        # Decode the content from Base64

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
            if line.startswith("## "):  # Start of a new version section
                if in_latest_section:
                    break  # Stop when the next section starts
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

    # Get the current hash of the changelog file
    current_hash = get_file_hash(changelog_file)

    # Load the last saved hash
    try:
        with open(last_changelog_file, "r") as file:
            last_data = json.load(file)
            last_hash = last_data.get("hash")
    except FileNotFoundError:
        last_hash = None

    # If the hash has changed, send the changelog
    if current_hash != last_hash:
        print("Changelog has changed. Sending updates...")

        # Extract the latest changelog entry
        with open(changelog_file, "r") as file:
            changelog_content = file.read()
        latest_changelog = extract_latest_changelog(changelog_content)

        if latest_changelog and not latest_changelog.startswith("Failed"):
            version = latest_changelog.splitlines()[0].strip("## ").strip()

            # Send the changelog to the `changelogs` channel in each server
            for guild in bot.guilds:
                soul_category = discord.utils.get(guild.categories, name="Soul")
                if not soul_category:
                    print(f"⚠️ Soul category not found in guild {guild.name}. Skipping...")
                    continue

                changelog_channel = discord.utils.get(soul_category.channels, name="changelogs")
                if not changelog_channel:
                    print(f"⚠️ Changelogs channel not found in guild {guild.name}. Skipping...")
                    continue

                # Create an embed for the changelog
                embed = discord.Embed(
                    title=f"Changelog Update - {version}",
                    description=latest_changelog,
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Visit https://www.soullessgraves for more information.")

                # Send the embed
                try:
                    await changelog_channel.send(embed=embed)
                    print(f"✅ Changelog sent to {guild.name} in {changelog_channel.name}.")
                except Exception as e:
                    log_error(e)
                    print(f"⚠️ Failed to send changelog to {guild.name}: {e}")

        # Save the new hash
        with open(last_changelog_file, "w") as file:
            json.dump({"hash": current_hash}, file)
    else:
        print("No changes detected in changelog.md.")

async def pull_and_check_changelog():
    """
    Perform a git pull and check for changes in the changelog.md file.
    """
    try:
        # Perform a git pull
        result = subprocess.run(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
        print(result.stderr)

        # Check and send the changelog if it has changed
        await check_and_send_changelog()
    except Exception as e:
        log_error(e)
        print("Failed to pull changes or check the changelog.")

@tasks.loop(minutes=10)  # Adjust the interval as needed
async def update_changelog_task():
    await pull_and_check_changelog()

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")

    # Set the bot's status to "Watching /users"
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/users"))

    # Start the changelog update task
    update_changelog_task.start()

    # Restart the check_status task
    if check_status.is_running():
        check_status.cancel()
    check_status.start()

    # Start the price checking task
    @tasks.loop(minutes=10)  # Adjust the interval as needed
    async def check_item_prices():
        # Add your logic for checking item prices here
        print("Checking item prices...")
    
        # Example logic: Iterate through tracked items and fetch their prices
        for guild_id, items in server_item_ids.items():
            for item_id, item_data in items.items():
                resale_url = f"https://economy.roblox.com/v1/assets/{item_id}/resale-data"
                try:
                    response = requests.get(resale_url)
                    response.raise_for_status()
                    resale_data = response.json()
    
                    # Get the current price
                    current_price = resale_data.get("recentAveragePrice", None)
                    last_price = item_data.get("last_price", None)
    
                    # If the price has changed, update and notify
                    if current_price != last_price:
                        item_data["last_price"] = current_price
                        print(f"Price for item {item_id} updated: {last_price} -> {current_price}")
                except Exception as e:
                    log_error(e)
                    print(f"Failed to fetch price for item {item_id}: {e}")
    
    check_item_prices.start()

    try:
        synced = await tree.sync()  # Sync slash commands with Discord
        print(f"Slash commands re-synced successfully: {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print("Starting tasks...")

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error):
    """
    Handle errors for invalid slash commands and provide a list of available commands.
    """
    if isinstance(error, app_commands.CommandNotFound):
        # Create an embed for invalid commands
        embed = discord.Embed(
            title="Invalid Command",
            description="The command you entered does not exist. Here are the available commands:",
            color=discord.Color.red()
        )
        embed.add_field(name="/track", value="Track a user by their Roblox ID or username.\nUsage: `/track <user_id>` or `/track <username>`", inline=False)
        embed.add_field(name="/untrack", value="Untrack a user by their Roblox ID.\nUsage: `/untrack <user_id>`", inline=False)
        embed.add_field(name="/whois", value="Get details about a Roblox user.\nUsage: `/whois <user_id>` or `/whois <username>`", inline=False)
        embed.add_field(name="/whois_display", value="Get details about Roblox users by display name.\nUsage: `/whois_display <display_name>`", inline=False)
        embed.add_field(name="/gen", value="Generate a username or random string.\nUsage: `/gen` with options 1 or 2.", inline=False)
        embed.add_field(name="/item", value="Fetch details about a Roblox limited item by its ID.\nUsage: `/item <item_id>`", inline=False)
        embed.add_field(name="/trackitem", value="Track a Roblox limited item by its ID.\nUsage: `/trackitem <item_id>`", inline=False)
        embed.add_field(name="/setup", value="Set up the bot's categories and channels.\nUsage: `/setup`", inline=False)
        embed.add_field(name="/unsetup", value="Remove the bot's categories and channels.\nUsage: `/unsetup`", inline=False)
        embed.add_field(name="/support", value="Show this help message.\nUsage: `/support`", inline=False)
        embed.add_field(name="/tracking", value="List all currently tracked users in this server.\nUsage: `/tracking`", inline=False)
        embed.set_footer(text="Visit https://www.soullessgraves for more information and support.")

        # Send the embed as an ephemeral message
        await interaction.response.send_message(embed=embed, ephemeral=False, delete_after=30)
    else:
        # Log other errors
        log_error(error)
        await interaction.response.send_message(
            "An unexpected error occurred. Please try again later.",
            ephemeral=True
        )

@tasks.loop(seconds=30)
async def check_status():
    print(f"Checking status for servers: {server_user_ids.keys()}")  # Debug log
    guild_ids_to_remove = []  # Track guilds to remove from active checks

    for guild_id, user_ids in server_user_ids.items():
        guild = bot.get_guild(int(guild_id))
        if not guild:
            print(f"⚠️ Guild with ID {guild_id} not found. Skipping...")
            guild_ids_to_remove.append(guild_id)  # Mark for removal
            continue

        # Initialize data_cache for the guild if it doesn't exist
        if guild_id not in data_cache:
            data_cache[guild_id] = {}

        # Get the Soul category and Status Updates channel
        soul_category = discord.utils.get(guild.categories, name="Soul")
        if not soul_category:
            print(f"⚠️ Soul category not found in guild {guild.name}. Skipping...")
            continue

        status_channel = discord.utils.get(soul_category.channels, name="status-updates")
        if not status_channel:
            print(f"⚠️ Status Updates channel not found in guild {guild.name}. Skipping...")
            continue

        print(f"Processing guild: {guild.name}, channel: {status_channel.name}")  # Debug log

        for user_id in user_ids:
            # Ensure the user ID exists in the data_cache for this guild
            if user_id not in data_cache[guild_id]:
                data_cache[guild_id][user_id] = {"last_status": None}

            current_status = get_roblox_presence(user_id)
            previous_status = data_cache[guild_id][user_id]["last_status"]

            # Avoid sending duplicate status updates
            if current_status == previous_status:
                continue

            data_cache[guild_id][user_id]["last_status"] = current_status

            # Fetch user details
            user_details = get_user_details(user_id)

            # Fetch the user's headshot URL
            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
            try:
                response = requests.get(avatar_url)
                response.raise_for_status()
                avatar_data = response.json()
                avatar_url = avatar_data["data"][0]["imageUrl"]
            except Exception as e:
                log_error(e)
                avatar_url = None

            # Create an embed for the status update
            embed_color = discord.Color.blue()  # Default color for "Online"
            if current_status == "In Game":
                embed_color = discord.Color.green()  # Green for "In Game"
            elif current_status == "Offline":
                embed_color = discord.Color.red()  # Red for "Offline"

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

            # Add the user's headshot as the thumbnail
            if avatar_url:
                embed.set_thumbnail(url=avatar_url)

            # Send the embed to the Status Updates channel
            await status_channel.send(embed=embed)

    # Remove guilds that are no longer present
    for guild_id in guild_ids_to_remove:
        print(f"⚠️ Removing guild ID {guild_id} from active checks.")
        server_user_ids.pop(guild_id, None)  # Remove from server_user_ids
        data_cache.pop(guild_id, None)  # Remove from data_cache
        save_server_user_ids()  # Save updated user IDs to file

@bot.event
async def on_guild_join(guild):
    """
    Sends a welcome message with the bot's README content when added to a new server.
    """
    # Find a general or default text channel to send the message
    default_channel = next((channel for channel in guild.text_channels if channel.permissions_for(guild.me).send_messages), None)
    if not default_channel:
        print(f"⚠️ No suitable channel found in guild {guild.name} to send the welcome message.")
        return

    # Read the README.md file
    try:
        with open("README.md", "r") as readme_file:
            readme_content = readme_file.read()
    except Exception as e:
        log_error(e)
        print("⚠️ Failed to read the README.md file.")
        return

    # Extract the "Overview" and "Commands" sections from the README
    overview_section = []
    commands_section = []
    in_overview = False
    in_commands = False

    for line in readme_content.splitlines():
        if line.startswith("## Overview"):
            in_overview = True
            in_commands = False
        elif line.startswith("## Commands"):
            in_overview = False
            in_commands = True
        elif line.startswith("## "):  # End of a section
            in_overview = False
            in_commands = False

        if in_overview:
            overview_section.append(line)
        elif in_commands:
            commands_section.append(line)

    overview_text = "\n".join(overview_section).strip()
    commands_text = "\n".join(commands_section).strip()

    # Split the commands into chunks of 1024 characters or fewer
    commands_chunks = [commands_text[i:i + 1024] for i in range(0, len(commands_text), 1024)]

    # Create the Welcome Page embed
    welcome_embed = discord.Embed(
        title="Welcome to SOUL Bot!",
        description="Thank you for adding SOUL Bot to your server! Here's how to get started:",
        color=discord.Color.blue()
    )
    welcome_embed.add_field(name="Overview", value=overview_text[:1024], inline=False)
    welcome_embed.set_footer(text="Visit https://www.soullessgraves for more information and support.")

    # Create the Commands Page embeds
    commands_embeds = []
    for i, chunk in enumerate(commands_chunks):
        commands_embed = discord.Embed(
            title=f"Commands (Page {i + 1}/{len(commands_chunks)})",
            description=chunk,
            color=discord.Color.blue()
        )
        commands_embed.set_footer(text="Visit https://www.soullessgraves for more information and support.")
        commands_embeds.append(commands_embed)

    # Send the embeds sequentially
    await default_channel.send(embed=welcome_embed)
    for embed in commands_embeds:
        await default_channel.send(embed=embed)

    """
    Automatically assign the bot an admin-like role when it joins a server.
    """
    # Check if the bot already has an admin-like role
    bot_member = guild.me  # The bot's member object
    if bot_member.guild_permissions.administrator:
        print(f"Bot already has admin permissions in {guild.name}.")
        return

    # Check if an "Admin" role exists
    admin_role = discord.utils.get(guild.roles, name="Admin")
    if not admin_role:
        # Create the "Admin" role if it doesn't exist
        try:
            admin_role = await guild.create_role(
                name="Admin",
                permissions=discord.Permissions(administrator=True),
                reason="Automatically created Admin role for the bot."
            )
            print(f"Created 'Admin' role in {guild.name}.")
        except discord.Forbidden:
            print(f"⚠️ Bot lacks permissions to create roles in {guild.name}.")
            return
        except Exception as e:
            print(f"⚠️ Failed to create 'Admin' role in {guild.name}: {e}")
            return

    # Assign the "Admin" role to the bot
    try:
        await bot_member.add_roles(admin_role, reason="Assigning Admin role to the bot.")
        print(f"Assigned 'Admin' role to the bot in {guild.name}.")
    except discord.Forbidden:
        print(f"⚠️ Bot lacks permissions to assign roles in {guild.name}.")
    except Exception as e:
        print(f"⚠️ Failed to assign 'Admin' role to the bot in {guild.name}: {e}")

@tree.command(name="track", description="Track a Roblox user by their ID or username.")
@app_commands.describe(user_input="The Roblox user ID or username to track.")
async def track_command(interaction: discord.Interaction, user_input: str):
    """
    Track a Roblox user by their ID or username.
    """
    guild_id = str(interaction.guild_id)  # Get the server (guild) ID as a string
    if guild_id not in server_user_ids:
        server_user_ids[guild_id] = []  # Initialize the list for this server

    # Validate the input
    if not user_input.isdigit():
        # Resolve username to user ID
        url = f"https://users.roblox.com/v1/usernames/users"
        try:
            response = requests.post(url, json={"usernames": [user_input]})
            response.raise_for_status()
            data = response.json()
            if not data["data"]:
                error_embed = discord.Embed(
                    title="Invalid Input",
                    description=f"No user found with the username '{user_input}'.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
            user_id = str(data["data"][0]["id"])
        except Exception as e:
            log_error(e)
            error_embed = discord.Embed(
                title="Error",
                description=f"Failed to resolve username '{user_input}' to a user ID.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
    else:
        user_id = user_input

    # Check if the user ID is already being tracked
    if user_id in server_user_ids[guild_id]:
        already_tracked_embed = discord.Embed(
            title="User Already Tracked",
            description=f"User ID `{user_id}` is already being tracked.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=already_tracked_embed, ephemeral=True)
        return

    # Add the user to the tracker
    server_user_ids[guild_id].append(user_id)
    save_server_user_ids()

    success_embed = discord.Embed(
        title="User Tracked",
        description=f"User ID `{user_id}` has been added to the tracking list.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=success_embed, ephemeral=True)


@tree.command(name="untrack", description="Stop tracking a Roblox user by their ID or username.")
@app_commands.describe(user_input="The Roblox user ID or username to untrack.")
async def untrack_command(interaction: discord.Interaction, user_input: str):
    """
    Stop tracking a Roblox user by their ID or username.
    """
    guild_id = str(interaction.guild_id)  # Get the server (guild) ID
    if guild_id not in server_user_ids:
        server_user_ids[guild_id] = []  # Initialize the list for this server

    # Validate the input
    if not user_input.isdigit():
        # Resolve username to user ID
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
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
            user_id = str(data["data"][0]["id"])
        except Exception as e:
            log_error(e)
            error_embed = discord.Embed(
                title="Error",
                description=f"Failed to resolve username '{user_input}' to a user ID.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
    else:
        user_id = user_input

    # Check if the user ID is being tracked
    if user_id not in server_user_ids[guild_id]:
        error_embed = discord.Embed(
            title="User Not Tracked",
            description=f"User ID `{user_id}` is not being tracked.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Remove the user from the tracker
    server_user_ids[guild_id].remove(user_id)
    save_server_user_ids()

    success_embed = discord.Embed(
        title="User Untracked",
        description=f"User ID `{user_id}` has been removed from the tracking list.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=success_embed, ephemeral=True)

@tree.command(name="setup", description="Set up the bot's categories and channels.")
async def setup_command(interaction: discord.Interaction):
    """
    Set up the bot's categories and channels.
    """
    guild = interaction.guild

    # Check if the Soul category already exists
    soul_category = discord.utils.get(guild.categories, name="Soul")
    if soul_category:
        error_embed = discord.Embed(
            title="Setup Error",
            description="The **Soul** category already exists.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Ask for permission to create the categories and channels
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
    await interaction.response.send_message(embed=embed, ephemeral=True)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.content.lower() in ["yes", "no"]

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)
        if msg.content.lower() == "no":
            await interaction.followup.send("Setup canceled.", ephemeral=True)
            return
    except asyncio.TimeoutError:
        await interaction.followup.send("Setup timed out. Please run the command again.", ephemeral=True)
        return

    # Create the Soul category and channels
    soul_category = await guild.create_category("Soul")
    await guild.create_text_channel("Added/Removed Users Logs", category=soul_category)
    await guild.create_text_channel("Status Updates", category=soul_category)
    await guild.create_text_channel("Changelogs", category=soul_category)

    success_embed = discord.Embed(
        title="Setup Complete",
        description="The **Soul** category and its channels have been created successfully.",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=success_embed, ephemeral=True)


@tree.command(name="unsetup", description="Remove the bot's categories and channels.")
async def unsetup_command(interaction: discord.Interaction):
    """
    Remove the bot's categories and channels.
    """
    guild = interaction.guild

    # Check if the Soul category exists
    category = discord.utils.get(guild.categories, name="Soul")
    if not category:
        error_embed = discord.Embed(
            title="Unsetup Error",
            description="The **Soul** category does not exist.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Delete the category and its channels
    for channel in category.channels:
        await channel.delete()
    await category.delete()

    success_embed = discord.Embed(
        title="Unsetup Complete",
        description="The **Soul** category and its channels have been deleted successfully.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=success_embed, ephemeral=True)


@tree.command(name="whois", description="Fetch details about a Roblox user by ID or username.")
@app_commands.describe(user_input="The Roblox user ID or username.")
async def whois_command(interaction: discord.Interaction, user_input: str):
    """
    Fetch and display details about a Roblox user by user ID or username.
    """
    # Resolve username to user ID if input is not numeric
    if user_input.isdigit():
        user_id = user_input
    else:
        url = "https://users.roblox.com/v1/usernames/users"
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
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                return
            user_id = str(data["data"][0]["id"])
        except Exception as e:
            log_error(e)
            error_embed = discord.Embed(
                title="Error",
                description=f"Failed to resolve username '{user_input}' to a user ID.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

    # Fetch user details
    user_details = get_user_details(user_id)
    if user_details["username"] == "No username":
        error_embed = discord.Embed(
            title="User Not Found",
            description=f"No user found with the ID '{user_id}'.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Fetch the user's headshot URL
    avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
    try:
        response = requests.get(avatar_url)
        response.raise_for_status()
        avatar_data = response.json()
        avatar_url = avatar_data["data"][0]["imageUrl"]
    except Exception as e:
        log_error(e)
        avatar_url = None

    # Create an embed for the user details
    embed = discord.Embed(
        title=f"Whois for {user_details['username']}",
        description=f"**Display Name:** {user_details['display_name']}\n**Description:** {user_details['description']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="User ID", value=user_id, inline=False)
    embed.add_field(name="Is Banned", value="Yes" if user_details["is_banned"] else "No", inline=False)
    embed.set_thumbnail(url=avatar_url)

    # Send the embed
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="whois_display", description="Fetch details about Roblox users by display name.")
@app_commands.describe(display_name="The display name to search for.")
async def whois_display_command(interaction: discord.Interaction, display_name: str):
    """
    Fetch and display details about Roblox users by display name.
    """
    # Search for users by display name
    url = "https://users.roblox.com/v1/users/search"
    try:
        response = requests.get(url, params={"keyword": display_name, "limit": 10})  # Limit results to 10
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
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Check if no users were found
    if not users:
        error_embed = discord.Embed(
            title="No Users Found",
            description=f"No users found with the display name '{display_name}'.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Create embeds for each user
    embeds = []
    for user in users:
        user_id = user.get("id", "Unknown")
        username = user.get("name", "Unknown")
        display_name = user.get("displayName", "Unknown")

        # Fetch the user's headshot URL
        avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=352x352&format=Png&isCircular=false"
        try:
            response = requests.get(avatar_url)
            response.raise_for_status()
            avatar_data = response.json()
            avatar_url = avatar_data["data"][0]["imageUrl"]
        except Exception as e:
            log_error(e)
            avatar_url = None

        # Create an embed for the user
        embed = discord.Embed(
            title=f"Whois for Display Name: {display_name}",
            description=f"**Username:** {username}\n**User ID:** {user_id}",
            color=discord.Color.blue()
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embeds.append(embed)

    # Send the embeds
    for embed in embeds:
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="item", description="Fetch details about a Roblox limited item by its ID.")
@app_commands.describe(item_id="The ID of the Roblox limited item.")
async def item_command(interaction: discord.Interaction, item_id: int):
    """
    Fetch and display details about a Roblox limited item by its ID.
    """
    resale_url = f"https://economy.roblox.com/v1/assets/{item_id}/resale-data"
    catalog_url = f"https://catalog.roblox.com/v1/catalog/items/details"
    thumbnail_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={item_id}&size=420x420&format=Png&isCircular=false"

    headers = {
        "Content-Type": "application/json",
        "Cookie": f".ROBLOSECURITY={get_next_cookie()}"
    }

    try:
        # Fetch resale data
        resale_response = requests.get(resale_url, headers=headers)
        resale_response.raise_for_status()
        resale_data = resale_response.json()

        # Check if the item is limited by verifying resale-related fields
        if "recentAveragePrice" not in resale_data or "priceDataPoints" not in resale_data:
            error_embed = discord.Embed(
                title="Invalid Item",
                description=f"Item ID `{item_id}` is not a limited item and cannot be tracked.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Fetch catalog data for item details
        catalog_payload = {"items": [{"itemType": "Asset", "id": item_id}]}
        catalog_response = requests.post(catalog_url, json=catalog_payload, headers=headers)
        catalog_response.raise_for_status()
        catalog_data = catalog_response.json()

        # Extract item details from catalog data
        if not catalog_data.get("data"):
            raise ValueError("Invalid item ID or item not found in the catalog.")
        catalog_item = catalog_data["data"][0]
        item_name = catalog_item.get("name", "Unknown Item")
        creator_name = catalog_item.get("creator", {}).get("name", "Unknown Creator")

        # Fetch item thumbnail
        thumbnail_response = requests.get(thumbnail_url)
        thumbnail_response.raise_for_status()
        thumbnail_data = thumbnail_response.json()
        thumbnail_image_url = thumbnail_data["data"][0].get("imageUrl", None)

        # Extract item details from resale data
        current_price = resale_data.get("recentAveragePrice", "N/A")
        previous_price = resale_data.get("originalPrice", "N/A")

        # Create an embed for the item details
        embed = discord.Embed(
            title=f"Item Details: {item_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Limited", value="Yes", inline=False)
        embed.add_field(name="Current Price", value=f"{current_price} Robux" if current_price != "N/A" else "N/A", inline=False)
        embed.add_field(name="Previous Price", value=f"{previous_price} Robux" if previous_price != "N/A" else "N/A", inline=False)
        embed.add_field(name="Creator", value=creator_name, inline=False)
        embed.add_field(name="Item ID", value=item_id, inline=False)

        # Add the item's image as the embed thumbnail
        if thumbnail_image_url:
            embed.set_thumbnail(url=thumbnail_image_url)

        # Send the embed
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except ValueError as e:
        error_embed = discord.Embed(
            title="Invalid Item",
            description=str(e),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

    except requests.exceptions.RequestException as e:
        log_error(e)
        error_embed = discord.Embed(
            title="Error",
            description=f"Failed to fetch details for item ID `{item_id}`. Please try again later.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)


@tree.command(name="trackitem", description="Track a Roblox limited item by its ID.")
@app_commands.describe(item_id="The ID of the Roblox limited item to track.")
async def track_item_command(interaction: discord.Interaction, item_id: int):
    """
    Track a Roblox limited item by its ID for price updates.
    """
    guild_id = str(interaction.guild_id)
    if guild_id not in server_item_ids:
        server_item_ids[guild_id] = {}

    # Check if the item is already being tracked
    if item_id in server_item_ids[guild_id]:
        error_embed = discord.Embed(
            title="Item Already Tracked",
            description=f"Item ID `{item_id}` is already being tracked.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    # Fetch resale data to check if the item is limited
    resale_url = f"https://economy.roblox.com/v1/assets/{item_id}/resale-data"
    try:
        resale_response = requests.get(resale_url)
        resale_response.raise_for_status()
        resale_data = resale_response.json()

        # Check if the item is limited by verifying resale-related fields
        if "recentAveragePrice" not in resale_data or "priceDataPoints" not in resale_data:
            error_embed = discord.Embed(
                title="Invalid Item",
                description=f"Item ID `{item_id}` is not a limited item and cannot be tracked.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Add the item to the tracking list
        server_item_ids[guild_id][item_id] = {"last_price": resale_data.get("recentAveragePrice", None)}
        success_embed = discord.Embed(
            title="Item Tracked",
            description=f"Item ID `{item_id}` has been added to the tracking list.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=success_embed, ephemeral=True)

    except requests.exceptions.RequestException as e:
        log_error(e)
        error_embed = discord.Embed(
            title="Error",
            description=f"Failed to fetch details for item ID `{item_id}`. Please try again later.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@tree.command(name="string", description="Generate a 20-character random string and check if it's available.")
async def string_command(interaction: discord.Interaction):
    """
    Generate a 20-character random string and check if it's available as a username.
    """
    url = "https://users.roblox.com/v1/usernames/users"
    while True:
        random_string = ''.join(random.choices(string.ascii_letters, k=20))
        try:
            response = requests.post(url, json={"usernames": [random_string]})
            response.raise_for_status()
            data = response.json()

            if not data["data"]:  # If the string is not in use
                break
        except requests.exceptions.RequestException as e:
            log_error(e)
            error_embed = discord.Embed(
                title="Error",
                description="Failed to check username availability. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

    embed = discord.Embed(
        title="Generated String",
        description=f"Your randomly generated username is: `{random_string}`",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="user", description="Check if a username is available and get suggestions if it's not.")
@app_commands.describe(word="The username to check.")
async def user_command(interaction: discord.Interaction, word: str):
    """
    Check if a username is available and suggest alternatives if it's not.
    """
    if len(word) > 20:
        error_embed = discord.Embed(
            title="Invalid Username",
            description="The username exceeds the 20-character limit. Please provide a shorter username.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return

    url = "https://users.roblox.com/v1/usernames/users"
    try:
        response = requests.post(url, json={"usernames": [word]})
        response.raise_for_status()
        data = response.json()

        if data["data"]:  # If the word is found in the results
            suggestions = [f"{word[:15]}{random.randint(1, 9999)}" for _ in range(3)]
            embed = discord.Embed(
                title="Username Unavailable",
                description=f"The username `{word}` is already in use.\n\n**Suggestions:**\n" +
                            "\n".join([f"`{suggestion}`" for suggestion in suggestions]),
                color=discord.Color.red()
            )
        else:  # If the word is not found
            embed = discord.Embed(
                title="Username Available",
                description=f"The username `{word}` is available!",
                color=discord.Color.green()
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except requests.exceptions.RequestException as e:
        log_error(e)
        error_embed = discord.Embed(
            title="Error",
            description="Failed to check username availability. Please try again later.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)


@tree.command(name="gen", description="Generate a username or random string.")
@app_commands.describe(option="Choose 1 for word-based username or 2 for random string.", word="The word to check for availability (if option is 1).")
async def gen_command(interaction: discord.Interaction, option: int, word: str = None):
    """
    Generate a username based on the selected option:
    1. Word: Check if the word is already in use as a username.
    2. Random String: Generate a 20-character random string.
    """
    if option == 1:  # Word-based username
        if not word:
            error_embed = discord.Embed(
                title="Missing Word",
                description="⚠️ Please provide a word to check for availability.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Check if the word is already in use as a username
        url = "https://users.roblox.com/v1/usernames/users"
        try:
            response = requests.post(url, json={"usernames": [word]})
            response.raise_for_status()
            data = response.json()

            if data["data"]:  # If the word is found in the results
                # Suggest adding numbers to the username
                suggestions = [f"{word[:15]}{random.randint(1, 9999)}" for _ in range(3)]
                embed = discord.Embed(
                    title="Username Unavailable",
                    description=f"The username `{word}` is already in use.\n\n**Suggestions:**\n" +
                                "\n".join([f"`{suggestion}`" for suggestion in suggestions]),
                    color=discord.Color.red()
                )
            else:  # If the word is not found
                embed = discord.Embed(
                    title="Username Available",
                    description=f"The username `{word}` is available!",
                    color=discord.Color.green()
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except requests.exceptions.RequestException as e:
            log_error(e)
            error_embed = discord.Embed(
                title="Error",
                description="⚠️ Failed to check username availability. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    elif option == 2:  # Random string-based username
        random_string = ''.join(random.choices(string.ascii_letters, k=20))  # Generate a 20-character random string
        embed = discord.Embed(
            title="Generated Username",
            description=f"Your randomly generated username is: `{random_string}`",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    else:
        error_embed = discord.Embed(
            title="Invalid Option",
            description="⚠️ Invalid option. Please select `1` for Word or `2` for Random String.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)


# Create a test slash command
@tree.command(name="hi", description="Sends a hello")
async def test_command(interaction: discord.Interaction):
    """
    A simple test slash command.
    """
    await interaction.response.send_message("Hello!", ephemeral=True)


@tree.command(name="support", description="Get help and support for using the bot.")
async def support_command(interaction: discord.Interaction):
    """
    Provide help and support information for the bot.
    """
    embed = discord.Embed(
        title="Support - Available Commands",
        description="Here are the available commands and how to use them:",
        color=discord.Color.blue()
    )
    embed.add_field(name="/track", value="Track a user by their Roblox ID or username.\nUsage: `/track <user_id>` or `/track <username>`", inline=False)
    embed.add_field(name="/untrack", value="Untrack a user by their Roblox ID.\nUsage: `/untrack <user_id>`", inline=False)
    embed.add_field(name="/whois", value="Get details about a Roblox user.\nUsage: `/whois <user_id>` or `/whois <username>`", inline=False)
    embed.add_field(name="/whois_display", value="Get details about Roblox users by display name.\nUsage: `/whois_display <display_name>`", inline=False)
    embed.add_field(name="/gen", value="Generate a username or random string.\nUsage: `/gen` with options 1 or 2.", inline=False)
    embed.add_field(name="/item", value="Fetch details about a Roblox limited item by its ID.\nUsage: `/item <item_id>`", inline=False)
    embed.add_field(name="/trackitem", value="Track a Roblox limited item by its ID.\nUsage: `/trackitem <item_id>`", inline=False)
    embed.add_field(name="/setup", value="Set up the bot's categories and channels.\nUsage: `/setup`", inline=False)
    embed.add_field(name="/unsetup", value="Remove the bot's categories and channels.\nUsage: `/unsetup`", inline=False)
    embed.add_field(name="/support", value="Show this help message.\nUsage: `/support`", inline=False)
    embed.set_footer(text="Visit https://www.soullessgraves for more information and support.")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="tracking", description="List all currently tracked users in this server.")
async def tracking_command(interaction: discord.Interaction):
    """
    Display all users currently being tracked in the server.
    """
    guild_id = str(interaction.guild_id)  # Get the server (guild) ID as a string

    # Check if there are any tracked users for this server
    if guild_id not in server_user_ids or not server_user_ids[guild_id]:
        embed = discord.Embed(
            title="No Tracked Users",
            description="There are currently no users being tracked in this server.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Create an embed to display the tracked users
    tracked_users = server_user_ids[guild_id]
    embed = discord.Embed(
        title="Tracked Users",
        description="Here is the list of users currently being tracked in this server:",
        color=discord.Color.blue()
    )

    # Add the tracked users to the embed
    for user_id in tracked_users:
        embed.add_field(name="User ID", value=user_id, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN)
