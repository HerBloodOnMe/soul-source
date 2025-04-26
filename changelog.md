# Changelog

## [1.1.10] - 2025-05-06
### Added
- **New Website Integration**:
  - Updated all embeds to include a clickable link to the new website: [https://www.soullessgraves.us/#].
  - Improved visibility and accessibility of the website link in all bot messages.
- **Clickable Links in Embeds**:
  - Replaced footer text links with clickable links in the embed descriptions for better user experience.

### Changed
- **Welcome Message**:
  - Updated the welcome message to include a clickable link to the website in the description.
- **Support Embed**:
  - Enhanced the `/support` command to include a clickable link to the website for more information.
- **Changelog Embed**:
  - Updated the changelog embed to include a clickable link to the website in the description.

### Fixed
- **Footer Link Issue**:
  - Resolved an issue where links in the footer were not clickable by moving them to the embed description.
- **Consistency Across Embeds**:
  - Ensured all embeds across the bot now have a consistent clickable link to the website.

## [1.1.9] - 2025-04-24
### Added
- **Slash Command Migration**:
  - Replaced `!h` with `/support` for a more user-friendly help menu.
  - Added `/setup` and `/unsetup` commands for dynamic category and channel management.
  - Added `/gen` command to generate usernames or random strings.
  - Added `/item` and `/trackitem` commands for fetching and tracking Roblox limited items.
  - Added `/whois` and `/whois_display` commands for fetching Roblox user details by ID, username, or display name.
  - Added `/tracking` command to list all currently tracked users in a server.
- **Bot Status Update**:
  - The bot's status is now set to "Watching /users".
- **Footer Update**:
  - All embeds now include a footer with the website link: `https://www.soullessgraves`.

### Changed
- **Help Menu**:
  - Updated the help menu to reflect the new slash commands.
  - `/support` now provides a detailed list of commands and their usage.
- **Changelog Notifications**:
  - Improved changelog detection and ensured updates are sent to the `changelogs` channel in each server.

### Fixed
- **Changelog Delivery**:
  - Resolved an issue where changelog updates were detected but not sent to the `changelogs` channel.
- **Error Handling**:
  - Improved error handling for API requests in `/gen`, `/item`, `/trackitem`, and `/whois` commands.
  - Resolved an issue where invalid inputs in `/gen` caused crashes.
- **Duplicate Tracking**:
  - Fixed a bug where duplicate items or users could be added to tracking lists.
- **Dynamic Welcome Message**:
  - Fixed the "About Me" embeds to dynamically pull content from the `README.md` file.
- **Invalid Command Handling**:
  - Added an error embed for invalid slash commands, listing all available commands. The embed auto-deletes after 30 seconds.

### Coming Soon
- **Verification System**: A command to verify users by linking their Discord account to their Roblox account.
- **Basic Moderation Tools**: Commands for managing your server, such as `/ban`, `/kick`, and `/mute`.
- **Game Searching**: A command to search for Roblox games by name or ID and fetch details about them.
- **Group Searching**: A command to search for Roblox groups by name or ID and fetch details about them.
- **Clothing Template Command**: A command to fetch Roblox clothing templates for shirts, pants, and t-shirts.
- **Group Leaderboard**: A new `/leaderboard` command to display the most active group members based on their activity (e.g., online status or shout contributions).

---

## [1.1.7] - 2025-04-25
### Added
- **Username Generator Commands**:
  - `!user`: Check if a username is available and suggest alternatives if it's not. Includes a 20-character limit check.
  - `!string`: Generate a 20-character random string and ensure it’s not already in use as a username.
- **Help Menu Update**: Added descriptions for the new `!user` and `!string` commands in the `!h` help menu.
- **Item Tracking Enhancements**:
  - Improved the `!track_item` command to handle multiple items per server.
  - Added periodic price updates for tracked items in the `status-updates` channel.

### Changed
- **Random String Length**: Updated the `!string` command to generate 20-character strings instead of 32-character strings.
- **Username Suggestions**: Improved the `!user` command to suggest usernames that adhere to the 20-character limit.
- **Item Validation**: Enhanced validation for limited items in the `!track_item` command to ensure only valid items are tracked.

### Fixed
- **Username Validation**: Resolved an issue where generated usernames were not checked for availability before being suggested.
- **Error Handling**: Improved error handling for API requests in the `!user`, `!string`, and `!track_item` commands to ensure proper feedback is provided when an error occurs.
- **Multiple Item Tracking**: Fixed a bug where tracking multiple items caused errors in the `!track_item` command and price update task.

## [1.1.4] - 2025-04-24
### Added
- **Improved `!whois_display` Command**: The bot now properly handles valid and invalid display names. If a user does not exist, an embed is sent explaining the issue.
- **Invalid Input Feedback for `!track`**: When invalid inputs are provided to the `!track` command, the bot sends an embed explaining how to use the command correctly.

### Fixed
- **User Not Found in `!whois_display`**: Resolved an issue where valid users were incorrectly reported as non-existent.
- **Error Handling in `!track`**: Improved error handling for invalid usernames or IDs in the `!track` command.
