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

All logs are structured in JSON format for easy parsing in Railway:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "message": "Command executed: logsolo",
  "event_type": "command_executed",
  "command": "logsolo",
  "user_id": "123456789",
  "username": "PlayerName",
  "guild_id": "987654321",
  "guild_name": "Dune Guild",
  "amount": 2500
}
```

## 🔍 Log Types

### Command Logs
- `command_executed` - Command started
- `command_success` - Command completed successfully
- `command_error` - Command failed with error details

### System Logs
- `bot_event` - Bot lifecycle events
- `database_operation` - Database operations
- `rate_limit_hit` - Rate limiting violations
- `permission_denied` - Access control failures

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
logger.info("Custom event", event_type="custom", data="value")

# Log errors
logger.error("Something went wrong", error="details")
```

## 📈 Benefits

### For Developers
- **Debug issues** quickly with detailed logs
- **Monitor performance** with execution times
- **Track user behavior** and command usage
- **Identify problems** before they affect users

### For Users
- **Better bot reliability** through monitoring
- **Faster bug fixes** with detailed error logs
- **Performance optimization** based on usage data

### For Railway
- **Easy monitoring** with structured logs
- **Health checks** for automatic restarts
- **Resource optimization** based on usage patterns

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

Your bot now provides comprehensive visibility into all operations, making it much easier to monitor, debug, and optimize! 🎉
