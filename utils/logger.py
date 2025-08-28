import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

class RailwayLogger:
    """Structured logger optimized for Railway deployment and Discord bot monitoring"""
    
    def __init__(self, name: str = "spice-tracker-bot"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Railway-friendly console handler
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        # Structured JSON formatter for Railway
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    def _format_log(self, level: str, message: str, **kwargs) -> str:
        """Format log message with structured data"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        return json.dumps(log_data, default=str)
    
    def info(self, message: str, **kwargs):
        """Log info level message"""
        formatted = self._format_log("INFO", message, **kwargs)
        self.logger.info(formatted)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message"""
        formatted = self._format_log("WARNING", message, **kwargs)
        self.logger.warning(formatted)
    
    def error(self, message: str, **kwargs):
        """Log error level message"""
        formatted = self._format_log("ERROR", message, **kwargs)
        self.logger.error(formatted)
    
    def debug(self, message: str, **kwargs):
        """Log debug level message"""
        formatted = self._format_log("DEBUG", message, **kwargs)
        self.logger.debug(formatted)
    
    def command_executed(self, command: str, user_id: str, username: str, 
                        guild_id: Optional[str] = None, guild_name: Optional[str] = None,
                        **kwargs):
        """Log Discord command execution"""
        self.info(
            f"Command executed: {command}",
            event_type="command_executed",
            command=command,
            user_id=user_id,
            username=username,
            guild_id=guild_id,
            guild_name=guild_name,
            **kwargs
        )
    
    def command_success(self, command: str, user_id: str, username: str, 
                       execution_time: float, **kwargs):
        """Log successful command execution"""
        self.info(
            f"Command completed successfully: {command}",
            event_type="command_success",
            command=command,
            user_id=user_id,
            username=username,
            execution_time=execution_time,
            **kwargs
        )
    
    def command_error(self, command: str, user_id: str, username: str, 
                     error: str, **kwargs):
        """Log command execution errors"""
        self.error(
            f"Command failed: {command}",
            event_type="command_error",
            command=command,
            user_id=user_id,
            username=username,
            error=error,
            **kwargs
        )
    
    def rate_limit_hit(self, command: str, user_id: str, username: str):
        """Log rate limit violations"""
        self.warning(
            f"Rate limit hit for command: {command}",
            event_type="rate_limit_hit",
            command=command,
            user_id=user_id,
            username=username
        )
    
    def permission_denied(self, command: str, user_id: str, username: str, 
                         required_permission: str):
        """Log permission denied events"""
        self.warning(
            f"Permission denied for command: {command}",
            event_type="permission_denied",
            command=command,
            user_id=user_id,
            username=username,
            required_permission=required_permission
        )
    
    def bot_event(self, event: str, **kwargs):
        """Log bot lifecycle events"""
        self.info(
            f"Bot event: {event}",
            event_type="bot_event",
            event=event,
            **kwargs
        )
    
    def database_operation(self, operation: str, table: str, success: bool, 
                          **kwargs):
        """Log database operations"""
        level = "INFO" if success else "ERROR"
        log_method = self.info if success else self.error
        
        log_method(
            f"Database operation: {operation} on {table}",
            event_type="database_operation",
            operation=operation,
            table=table,
            success=success,
            **kwargs
        )

# Global logger instance
logger = RailwayLogger()
