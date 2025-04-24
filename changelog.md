# Changelog

## [1.1.4] - 2025-04-24
### Added
- **Improved `!whois_display` Command**: The bot now properly handles valid and invalid display names. If a user does not exist, an embed is sent explaining the issue.
- **Invalid Input Feedback for `!track`**: When invalid inputs are provided to the `!track` command, the bot sends an embed explaining how to use the command correctly.

### Fixed
- **User Not Found in `!whois_display`**: Resolved an issue where valid users were incorrectly reported as non-existent.
- **Error Handling in `!track`**: Improved error handling for invalid usernames or IDs in the `!track` command.
