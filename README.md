# SOUL Bot

## Overview

**SOUL** is a powerful Discord bot tailored for Roblox community management. It streamlines tracking user activity, monitoring group memberships, and staying updated on item prices, all while delivering real-time notifications. Designed to enhance your Roblox-focused Discord server, SOUL is an indispensable tool for administrators and community managers.

## Key Features

- **User Activity Tracking**: Monitor Roblox users by their ID or username with slash commands.
- **Username Generator**: 
  - Check if a username is available and get suggestions if it's not (`/gen` with option 1).
  - Generate a 20-character random string and ensure it’s not already in use (`/gen` with option 2).
- **Status Notifications**: Get notified about user status changes, such as "Online," "In Game," or "Offline."
- **Item Tracking**: Track limited Roblox items per server and receive periodic price updates in a designated channel (`/trackitem`).
- **Item Details**: Fetch detailed information about limited Roblox items, including price history and creator details (`/item`).
- **Daily Reports**: Receive comprehensive daily summaries of group activities, including new members, shout updates, and item price changes.
- **Game Alerts**: Stay informed when tracked users join specific games.
- **Roblox Version Tracking**:
  - Use `/version` to display the current Roblox version.
  - Automatically detect Roblox updates and send notifications to the `updates` channel.
- **Group Monitoring**: Track group membership changes (joins and leaves) and shout updates in real time.
- **Group Details**: Fetch detailed information about Roblox groups, including owner details, member count, shout, and creation date (`/group`).
- **Error Logging**: Automatically logs errors to a file for easier debugging and maintenance.
- **Slash Command Support**: All commands are now implemented as slash commands for a more user-friendly experience.
- **Dynamic Setup**: Easily set up or remove the bot's categories and channels with `/setup` and `/unsetup`.
- **Changelog Updates**: Automatically fetch and share changelogs in a designated Discord channel when the bot starts or detects changes.

## How It Works

SOUL leverages Roblox's public APIs to gather user and group data. The bot performs periodic checks for updates and sends notifications to specified Discord channels. With dynamic user tracking and customizable settings, SOUL adapts seamlessly to your server's unique needs.

## Commands

Here’s a quick overview of SOUL’s core commands:

- `/track <user_id>`: Begin tracking a Roblox user by their ID or username.
- `/untrack <user_id>`: Stop tracking a Roblox user.
- `/subscribe <status>`: Subscribe to specific status updates (e.g., "Online," "In Game").
- `/gen`: Generate a username or random string:
  - Option 1: Check if a username is available and get suggestions if it's not.
  - Option 2: Generate a 20-character random string and ensure it’s not already in use.
- `/item <item_id>`: Fetch details about a Roblox limited item by its ID.
- `/trackitem <item_id>`: Track a Roblox limited item by its ID for price updates.
- `/whois <user_id or username>`: Fetch details about a Roblox user by their ID or username.
- `/whois_display <display_name>`: Fetch details about Roblox users by their display name.
- `/group <group_id>`: Fetch details about a Roblox group, including owner, members, shout, and creation date.
- `/version`: Display the current Roblox version.
- `/setup`: Set up the bot's categories and channels.
- `/unsetup`: Remove the bot's categories and channels.

Elevate your Roblox community management with SOUL Bot—your all-in-one solution for seamless tracking and notifications.
