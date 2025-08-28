# Overview

This is a Discord bot called "Spice Tracker" that gamifies resource collection in a Dune-themed setting. Users can deposit "sand" and convert it to "melange" at configurable conversion rates. The bot tracks user statistics and provides leaderboards to encourage engagement through a progression system.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Discord.py**: Python Discord bot library with slash command support
- **Python 3.11**: Python runtime environment
- **Single File Architecture**: All commands integrated in main bot file for simplicity

## Data Storage
- **SQLite3 with aiosqlite**: Async local file-based database for persistent data storage
- **Two-table Schema**: 
  - `users` table: Tracks user IDs, usernames, sand/melange totals, and timestamps
  - `settings` table: Stores configurable bot settings like conversion rates
- **Direct SQL with async/await**: Async SQL queries for performance

## Command Structure
- **Slash Commands**: Modern Discord interaction pattern
- **Permission-based Access**: Admin-only commands for configuration and data management
- **Rate Limiting**: In-memory rate limiter to prevent spam and abuse
- **Input Validation**: Min/max value constraints on user inputs

## Security & Permissions
- **Discord Permissions Integration**: Uses Discord's built-in permission system
- **Admin Verification**: Commands like `/setrate` and `/resetstats` require Administrator permissions
- **Rate Limiting**: Per-user, per-command cooldowns stored in memory
- **Input Sanitization**: Validates user inputs for type and range

## Game Mechanics
- **Progressive Conversion**: Sand accumulates and converts to melange at configurable thresholds
- **Persistent Progress**: User statistics persist between bot restarts
- **Leaderboard System**: Encourages competition through ranking display
- **Administrative Controls**: Admins can modify conversion rates and reset all data

# External Dependencies

## Discord Integration
- **Discord.js**: Official Discord API wrapper for bot functionality
- **Discord REST API**: For command registration and interaction handling
- **Discord API Types**: TypeScript definitions for API structures

## Database
- **SQLite3**: Embedded database engine for local data persistence
- **No external database server required**: Self-contained storage solution

## Environment Management
- **dotenv**: Manages sensitive configuration like bot tokens
- **Environment Variables**: 
  - `DISCORD_TOKEN`: Bot authentication token
  - `CLIENT_ID`: Discord application client ID

## Development Tools
- **Node.js Package Manager**: npm for dependency management
- **File System Operations**: Built-in fs module for command file discovery