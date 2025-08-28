# 📊 Logging System for Railway

Your Spice Tracker Bot now includes comprehensive logging optimized for Railway deployment and Discord bot monitoring.

## 🚀 What Gets Logged

### Command Execution
- **Every slash command** executed by users
- **User details**: ID, username, guild info
- **Command parameters**: Amounts, limits, settings
- **Execution time**: Performance monitoring
- **Success/failure status**: Error tracking

### Bot Events
- **Bot startup/shutdown**: Lifecycle monitoring
- **Command syncing**: Slash command registration
- **Database operations**: Connection and query status
- **Health server**: Railway health check endpoint

### Security & Permissions
- **Rate limit violations**: Spam prevention monitoring
- **Permission denials**: Admin command access attempts
- **Invalid inputs**: User error tracking

## 📋 Log Format

All logs use a clean, Railway-friendly format that won't be misinterpreted:

```
2024-01-15 10:30:45 | INFO | [INFO] Command executed: logsolo | user=PlayerName | user_id=123456789 | guild=Dune Guild | amount=2,500
2024-01-15 10:30:46 | INFO | [INFO] Command completed: logsolo | user=PlayerName | user_id=123456789 | time=0.045s | total_sand=5,000 | new_melange=50
2024-01-15 10:30:47 | WARNING | [WARNING] Rate limit hit: logsolo | user=PlayerName | user_id=123456789
```

### Key Features
- **Clean formatting** - No JSON or special characters
- **Easy to read** - Pipe-separated fields
- **Railway compatible** - Won't trigger false error detection
- **Structured data** - Key=value pairs for easy parsing

## 🔍 Log Types

### Command Logs
- **Command execution** - When commands start
- **Command completion** - Successful command results
- **Command errors** - Failed commands with error details

### System Logs
- **Bot events** - Lifecycle and status changes
- **Database operations** - Success/failure of data operations
- **Rate limiting** - Spam prevention events
- **Permissions** - Access control failures

## 📊 Railway Monitoring

### View Logs
1. **Railway Dashboard** → Your Project → Deployments
2. **Click on deployment** → View logs
3. **Real-time logs** during bot operation

### Log Analysis
- **Command usage patterns**: Most popular commands
- **Performance metrics**: Execution times
- **Error tracking**: Failed commands and reasons
- **User activity**: Who's using the bot most

### Health Monitoring
- **Bot status**: Online/offline tracking
- **Database health**: Connection status
- **Command success rates**: Reliability metrics

## 🛠️ Customization

### Log Levels
The logger supports these levels:
- `INFO` - Normal operations (default)
- `WARNING` - Rate limits, permission issues
- `ERROR` - Command failures, system errors
- `DEBUG` - Detailed debugging info

### Adding Custom Logs
```python
from utils.logger import logger

# Log custom events
logger.info("Custom event", data="value", count=42)

# Log errors
logger.error("Something went wrong", error="details")
```

## 📈 Benefits

### For Developers
- **Debug issues** quickly with clean, readable logs
- **Monitor performance** with execution times
- **Track user behavior** and command usage
- **Identify problems** before they affect users

### For Users
- **Better bot reliability** through monitoring
- **Faster bug fixes** with detailed error logs
- **Performance optimization** based on usage data

### For Railway
- **Easy monitoring** with clean, structured logs
- **Health checks** for automatic restarts
- **Resource optimization** based on usage patterns
- **No false error detection** from log formatting

## 🔧 Troubleshooting

### If Logs Don't Appear
1. Check Railway deployment logs
2. Verify bot is running
3. Check environment variables
4. Restart the bot if needed

### Common Log Patterns
- **High error rates** → Check Discord permissions
- **Slow commands** → Database performance issues
- **Rate limit hits** → Spam prevention working
- **Permission denials** → Admin setup issues

### Railway Log Display
- **Clean format** - Logs appear as normal text, not errors
- **Easy filtering** - Use Railway's log search features
- **Performance tracking** - Monitor execution times
- **Error detection** - Only real errors are flagged

Your bot now provides comprehensive visibility with clean, Railway-friendly logs that won't be misinterpreted! 🎉
