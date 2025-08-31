import time

class RateLimiter:
    """Simplified rate limiter for bot commands"""
    
    def __init__(self):
        # Command limits: (max_uses, time_window_seconds)
        self.limits = {
            'spicesolo': (10, 60),      # 10 uses per 60 seconds
            'myrefines': (5, 30),     # 5 uses per 30 seconds
            'leaderboard': (3, 60),   # 3 uses per 60 seconds
            'spicesplit': (2, 120),   # 2 uses per 2 minutes
            'help': (3, 60),          # 3 uses per 60 seconds
            'setrate': (1, 300),      # 1 use per 5 minutes
            'resetstats': (1, 600),   # 1 use per 10 minutes
        }
        self.usage = {}
    
    def check_rate_limit(self, user_id, command):
        """Check if user can use command based on rate limits"""
        max_uses, window = self.limits.get(command, (5, 60))  # Default: 5 uses per minute
        key = f"{user_id}:{command}"
        
        now = time.time()
        
        # Initialize or reset if window expired
        if key not in self.usage or now > self.usage[key]['reset_time']:
            self.usage[key] = {'count': 0, 'reset_time': now + window}
        
        # Check if limit exceeded
        if self.usage[key]['count'] >= max_uses:
            return False
        
        # Increment usage count
        self.usage[key]['count'] += 1
        return True
    
    def reset_user_rate_limit(self, user_id, command):
        """Reset rate limit for a specific user and command"""
        key = f"{user_id}:{command}"
        if key in self.usage:
            del self.usage[key]
    
    def get_remaining_uses(self, user_id, command):
        """Get remaining uses and reset time for a command"""
        key = f"{user_id}:{command}"
        if key not in self.usage:
            max_uses, _ = self.limits.get(command, (5, 60))
            return max_uses, None
        
        max_uses, _ = self.limits.get(command, (5, 60))
        remaining = max(0, max_uses - self.usage[key]['count'])
        reset_time = self.usage[key]['reset_time']
        
        return remaining, reset_time