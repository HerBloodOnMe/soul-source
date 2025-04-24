# Changelog

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
