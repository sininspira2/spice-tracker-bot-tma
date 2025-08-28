# 🏜️ Spice Tracker Bot

A Discord bot for **Dune: Awakening** that helps guilds track spice sand collection, convert to melange, and manage team spice splits for operations.

## ✨ Features

- **Spice Sand Tracking** - Log individual spice deposits with automatic melange conversion
- **Team Spice Splits** - Calculate fair distribution among team members with customizable harvester cuts
- **Leaderboards** - Track top spice collectors in your guild
- **User Statistics** - View personal refining stats and totals
- **Admin Controls** - Configurable conversion rates and data management
- **Rate Limiting** - Prevents spam and abuse

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

## 🚀 Setup

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

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token for your `.env` file
5. Go to "OAuth2 > URL Generator"
6. Select scopes: `bot`, `applications.commands`
7. Select permissions: `Send Messages`, `Use Slash Commands`, `Read Message History`
8. Use the generated URL to invite the bot to your server

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

## 🗃️ Database

The bot uses SQLite for data persistence with two main tables:
- **users** - Tracks individual spice collection and refining stats
- **settings** - Stores configurable bot settings like conversion rates

## 🔧 Configuration

### Conversion Rate
Default: 50 sand = 1 melange (changeable with `/setrate`)

### Rate Limiting
- Commands are rate-limited per user to prevent spam
- Configurable cooldowns for different command types

## 🛡️ Permissions

- **User Commands** - Available to all server members
- **Admin Commands** - Require Discord Administrator permission
- **Bot Permissions** - Needs Send Messages, Use Slash Commands, Read Message History

## 🔒 Security

- Discord token and sensitive data stored in environment variables
- Input validation on all user commands
- Rate limiting prevents abuse
- Admin-only access to destructive operations

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