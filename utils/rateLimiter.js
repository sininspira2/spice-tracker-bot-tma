// Simple in-memory rate limiter
// For production use, consider Redis or a database-backed solution

const rateLimits = new Map();

// Rate limit configurations (command: { maxUses, windowMs })
const RATE_LIMIT_CONFIG = {
    logsolo: { maxUses: 10, windowMs: 60000 }, // 10 uses per minute
    myrefines: { maxUses: 5, windowMs: 30000 }, // 5 uses per 30 seconds
    leaderboard: { maxUses: 3, windowMs: 60000 }, // 3 uses per minute
    setrate: { maxUses: 2, windowMs: 300000 }, // 2 uses per 5 minutes
    resetstats: { maxUses: 1, windowMs: 600000 } // 1 use per 10 minutes
};

/**
 * Check if a user is within rate limits for a command
 * @param {string} userId - The user ID to check
 * @param {string} command - The command being executed
 * @returns {boolean} - True if within rate limits, false if exceeded
 */
function checkRateLimit(userId, command) {
    const config = RATE_LIMIT_CONFIG[command];
    
    if (!config) {
        // No rate limit configured for this command
        return true;
    }

    const key = `${userId}:${command}`;
    const now = Date.now();
    
    // Get or create user's rate limit data
    if (!rateLimits.has(key)) {
        rateLimits.set(key, {
            count: 0,
            resetTime: now + config.windowMs
        });
    }

    const userLimit = rateLimits.get(key);

    // Check if the window has expired
    if (now >= userLimit.resetTime) {
        userLimit.count = 0;
        userLimit.resetTime = now + config.windowMs;
    }

    // Check if user has exceeded the limit
    if (userLimit.count >= config.maxUses) {
        return false;
    }

    // Increment the counter
    userLimit.count++;
    return true;
}

/**
 * Get remaining uses for a user and command
 * @param {string} userId - The user ID to check
 * @param {string} command - The command to check
 * @returns {object} - Object with remaining uses and reset time
 */
function getRemainingUses(userId, command) {
    const config = RATE_LIMIT_CONFIG[command];
    
    if (!config) {
        return { remaining: Infinity, resetTime: null };
    }

    const key = `${userId}:${command}`;
    const now = Date.now();
    
    if (!rateLimits.has(key)) {
        return { remaining: config.maxUses, resetTime: null };
    }

    const userLimit = rateLimits.get(key);

    // Check if the window has expired
    if (now >= userLimit.resetTime) {
        return { remaining: config.maxUses, resetTime: null };
    }

    return {
        remaining: Math.max(0, config.maxUses - userLimit.count),
        resetTime: userLimit.resetTime
    };
}

/**
 * Reset rate limits for a specific user and command
 * @param {string} userId - The user ID to reset
 * @param {string} command - The command to reset (optional, resets all if not provided)
 */
function resetUserRateLimit(userId, command = null) {
    if (command) {
        const key = `${userId}:${command}`;
        rateLimits.delete(key);
    } else {
        // Reset all commands for the user
        for (const key of rateLimits.keys()) {
            if (key.startsWith(`${userId}:`)) {
                rateLimits.delete(key);
            }
        }
    }
}

/**
 * Clear expired rate limit entries (cleanup function)
 */
function cleanupExpiredLimits() {
    const now = Date.now();
    
    for (const [key, limit] of rateLimits.entries()) {
        if (now >= limit.resetTime) {
            rateLimits.delete(key);
        }
    }
}

/**
 * Get rate limit configuration for a command
 * @param {string} command - The command to get config for
 * @returns {object|null} - Rate limit configuration or null if not found
 */
function getRateLimitConfig(command) {
    return RATE_LIMIT_CONFIG[command] || null;
}

// Clean up expired entries every 5 minutes
setInterval(cleanupExpiredLimits, 300000);

module.exports = {
    checkRateLimit,
    getRemainingUses,
    resetUserRateLimit,
    cleanupExpiredLimits,
    getRateLimitConfig
};
