const { PermissionFlagsBits } = require('discord.js');

/**
 * Check if a member has administrator permissions
 * @param {GuildMember} member - The guild member to check
 * @returns {boolean} - True if member has admin permissions
 */
function checkAdminPermission(member) {
    if (!member) {
        return false;
    }

    // Check if member has administrator permission
    return member.permissions.has(PermissionFlagsBits.Administrator);
}

/**
 * Check if a member has specific permissions
 * @param {GuildMember} member - The guild member to check
 * @param {bigint|bigint[]} permissions - Permission(s) to check
 * @returns {boolean} - True if member has the required permissions
 */
function checkPermissions(member, permissions) {
    if (!member) {
        return false;
    }

    if (Array.isArray(permissions)) {
        return member.permissions.has(permissions);
    }

    return member.permissions.has(permissions);
}

/**
 * Check if a member is a server owner
 * @param {GuildMember} member - The guild member to check
 * @returns {boolean} - True if member is the server owner
 */
function checkOwnerPermission(member) {
    if (!member || !member.guild) {
        return false;
    }

    return member.guild.ownerId === member.id;
}

/**
 * Check if a member has manage server permissions
 * @param {GuildMember} member - The guild member to check
 * @returns {boolean} - True if member can manage server
 */
function checkManageServerPermission(member) {
    if (!member) {
        return false;
    }

    return member.permissions.has(PermissionFlagsBits.ManageGuild);
}

/**
 * Get permission level description for a member
 * @param {GuildMember} member - The guild member to check
 * @returns {string} - Description of permission level
 */
function getPermissionLevel(member) {
    if (!member) {
        return 'Unknown';
    }

    if (checkOwnerPermission(member)) {
        return 'Server Owner';
    }

    if (checkAdminPermission(member)) {
        return 'Administrator';
    }

    if (checkManageServerPermission(member)) {
        return 'Server Manager';
    }

    return 'Regular User';
}

module.exports = {
    checkAdminPermission,
    checkPermissions,
    checkOwnerPermission,
    checkManageServerPermission,
    getPermissionLevel
};
