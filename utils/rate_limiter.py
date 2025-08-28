import time
from typing import Dict, Tuple

class RateLimiter:
    def __init__(self):
        # Store rate limit data: {user_id: {command: (count, reset_time)}}
        self.rate_limits: Dict[str, Dict[str, Tuple[int, float]]] = {}
        
        # Rate limit configurations (command: (max_uses, window_seconds))
        self.rate_limit_config = {
            'logsolo': (10, 60),      # 10 uses per minute
            'myrefines': (5, 30),     # 5 uses per 30 seconds
            'leaderboard': (3, 60),   # 3 uses per minute
            'spicesplit': (3, 300),   # 3 uses per 5 minutes
            'help': (5, 60),          # 5 uses per minute
            'setrate': (2, 300),      # 2 uses per 5 minutes
            'resetstats': (1, 600)    # 1 use per 10 minutes
        }

    def check_rate_limit(self, user_id: str, command: str) -> bool:
        """Check if a user is within rate limits for a command"""
        config = self.rate_limit_config.get(command)
        if not config:
            # No rate limit configured for this command
            return True

        max_uses, window_seconds = config
        now = time.time()
        
        # Initialize user data if not exists
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {}
        
        if command not in self.rate_limits[user_id]:
            self.rate_limits[user_id][command] = (0, now + window_seconds)

        count, reset_time = self.rate_limits[user_id][command]

        # Check if the window has expired
        if now >= reset_time:
            count = 0
            reset_time = now + window_seconds

        # Check if user has exceeded the limit
        if count >= max_uses:
            return False

        # Increment the counter
        count += 1
        self.rate_limits[user_id][command] = (count, reset_time)
        return True

    def get_remaining_uses(self, user_id: str, command: str) -> Tuple[int, float | None]:
        """Get remaining uses for a user and command"""
        config = self.rate_limit_config.get(command)
        if not config:
            return 999999, None

        max_uses, window_seconds = config
        now = time.time()
        
        if (user_id not in self.rate_limits or 
            command not in self.rate_limits[user_id]):
            return max_uses, None

        count, reset_time = self.rate_limits[user_id][command]

        # Check if the window has expired
        if now >= reset_time:
            return max_uses, None

        return max(0, max_uses - count), reset_time

    def reset_user_rate_limit(self, user_id: str, command: str | None = None):
        """Reset rate limits for a specific user and command"""
        if user_id in self.rate_limits:
            if command:
                self.rate_limits[user_id].pop(command, None)
            else:
                # Reset all commands for the user
                self.rate_limits[user_id] = {}

    def cleanup_expired_limits(self):
        """Clean up expired rate limit entries"""
        now = time.time()
        users_to_remove = []
        
        for user_id, user_limits in self.rate_limits.items():
            commands_to_remove = []
            
            for command, (count, reset_time) in user_limits.items():
                if now >= reset_time:
                    commands_to_remove.append(command)
            
            for command in commands_to_remove:
                del user_limits[command]
            
            if not user_limits:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.rate_limits[user_id]