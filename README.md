# 🏜️ Spice Tracker Bot

A Discord bot for **Dune: Awakening** that helps guilds track spice sand collection, convert to melange, and manage team spice splits for operations.

## ✨ Features

- **Spice Sand Tracking** - Log individual spice deposits with automatic melange conversion
- **Team Spice Splits** - Calculate fair distribution among team members with customizable harvester cuts
- **Leaderboards** - Track top spice collectors in your guild
- **User Statistics** - View personal refining stats and totals
- **Admin Controls** - Configurable conversion rates and data management
- **Rate Limiting** - Prevents spam and abuse

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Discord Bot Token
- Discord Application Client ID

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/jaqknife777/spice-tracker-bot.git
   cd spice-tracker-bot
   ```

2. **Install dependencies**
   ```bash
   pip install discord.py python-dotenv aiosqlite
   ```

3. **Set up environment variables**
   Create a `.env` file:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   CLIENT_ID=your_client_id_here
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

## 🌐 Replit Deployment

### One-Click Deploy
[![Run on Replit](https://replit.com/badge/github/jaqknife777/spice-tracker-bot)](https://replit.com/github/jaqknife777/spice-tracker-bot)

### Manual Replit Setup

1. **Create a new Repl**
   - Go to [replit.com](https://replit.com) and sign in
   - Click "Create Repl"
   - Choose "Import from GitHub"
   - Enter: `jaqknife777/spice-tracker-bot`

2. **Configure Environment Variables**
   - In your Repl, go to "Tools" → "Secrets"
   - Add these secrets:
     - `DISCORD_TOKEN` = Your Discord bot token
     - `CLIENT_ID` = Your Discord application client ID

3. **Run the Bot**
   - Click the "Run" button
   - The bot will start and connect to Discord
   - Check the console for connection status

### Replit-Specific Features
- **Automatic Restart**: Bot restarts automatically if it crashes
- **24/7 Uptime**: Replit keeps your bot running continuously
- **Free Tier**: Includes 500 hours/month of runtime
- **Database Persistence**: SQLite database persists between restarts

### Troubleshooting Replit
- **Bot Offline**: Check the console for error messages
- **Commands Not Working**: Ensure slash commands are registered (check console logs)
- **Database Issues**: The bot creates the database automatically on first run
- **Rate Limiting**: Replit may have additional rate limits on free tier

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token for your `.env` file
5. Go to "OAuth2 > URL Generator"
6. Select scopes: `bot`, `applications.commands`
7. Select permissions: `Send Messages`, `Use Slash Commands`, `Read Message History`
8. Use the generated URL to invite the bot to your server

## 🤖 Commands

### User Commands
- `/logsolo <amount>` - Log spice sand you've collected
- `/spicesplit <sand> <participants> [harvester%]` - Calculate spice splits for team operations
- `/myrefines` - View your personal spice statistics
- `/leaderboard` - See top spice collectors in the server
- `/help` - Display all available commands

### Admin Commands
- `/setrate <rate>` - Change sand-to-melange conversion rate (default: 50 sand = 1 melange)
- `/resetstats` - Reset all user statistics (requires confirmation)

## 📊 Example Usage

### Individual Spice Logging
```
/logsolo 2500
```
*Logs 2,500 spice sand (converts to 50 melange at default rate)*

### Team Spice Split
```
/spicesplit 50000 5 25
```
*Splits 50,000 sand among 5 participants with 25% harvester cut*

**Result:**
- **Harvester gets:** 12,500 sand (250 melange)
- **Each team member gets:** 7,500 sand (150 melange)

## 🏗️ System Architecture

### Bot Framework
- **Discord.py** with slash command support
- **Single File Architecture** - All commands integrated in main bot file for simplicity
- **Async/await** - Non-blocking operations for better performance

### Data Storage
- **SQLite3** with aiosqlite for persistent data storage
- **Two-table Schema**: 
  - `users` table: Tracks user IDs, usernames, sand/melange totals, and timestamps
  - `settings` table: Stores configurable bot settings like conversion rates
- **No external database server required** - Self-contained storage solution

### Command Structure
- **Slash Commands** - Modern Discord interaction pattern
- **Permission-based Access** - Admin-only commands for configuration and data management
- **Rate Limiting** - In-memory rate limiter to prevent spam and abuse
- **Input Validation** - Min/max value constraints on user inputs

## 🔧 Configuration

### Conversion Rate
Default: 50 sand = 1 melange (changeable with `/setrate`)

### Rate Limiting
- Commands are rate-limited per user to prevent spam
- Configurable cooldowns for different command types

## 🛡️ Security & Permissions

- **Discord Permissions Integration** - Uses Discord's built-in permission system
- **Admin Verification** - Commands like `/setrate` and `/resetstats` require Administrator permissions
- **Rate Limiting** - Per-user, per-command cooldowns stored in memory
- **Input Sanitization** - Validates user inputs for type and range
- **Environment Variables** - Sensitive data stored in `.env` file

## 🗃️ Database Schema

The bot uses SQLite for data persistence with two main tables:
- **users** - Tracks individual spice collection and refining stats
- **settings** - Stores configurable bot settings like conversion rates

## 🎮 Game Mechanics

- **Progressive Conversion** - Sand accumulates and converts to melange at configurable thresholds
- **Persistent Progress** - User statistics persist between bot restarts
- **Leaderboard System** - Encourages competition through ranking display
- **Administrative Controls** - Admins can modify conversion rates and reset all data

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## 🎮 About Dune: Awakening

This bot is designed for the Dune: Awakening MMO game to help guilds manage spice operations, track resource collection, and fairly distribute rewards among team members.

---

**Bot Status:** Active and maintained  
**Game:** Dune: Awakening  
**Version:** 1.0.0