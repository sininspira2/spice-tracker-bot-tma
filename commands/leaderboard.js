const { SlashCommandBuilder } = require('discord.js');
const { getLeaderboard, getSetting } = require('../database');
const { checkRateLimit } = require('../utils/rateLimiter');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('leaderboard')
        .setDescription('Display top refiners by melange earned')
        .addIntegerOption(option =>
            option.setName('limit')
                .setDescription('Number of top users to display (default: 10)')
                .setMinValue(5)
                .setMaxValue(25)
                .setRequired(false)
        ),

    async execute(interaction) {
        // Check rate limit
        if (!checkRateLimit(interaction.user.id, 'leaderboard')) {
            return interaction.reply({
                content: '⏰ Please wait before using this command again.',
                ephemeral: true
            });
        }

        const limit = interaction.options.getInteger('limit') || 10;

        try {
            // Get leaderboard data
            const leaderboard = await getLeaderboard(limit);

            if (!leaderboard || leaderboard.length === 0) {
                return interaction.reply({
                    embeds: [{
                        title: '🏆 Melange Refining Leaderboard',
                        description: '🏜️ No refiners found yet! Be the first to start depositing sand with `/logsolo`.',
                        color: 0x95A5A6,
                        timestamp: new Date().toISOString()
                    }]
                });
            }

            // Get conversion rate for display
            const sandPerMelange = parseInt(await getSetting('sand_per_melange')) || 50;

            // Create leaderboard entries
            let leaderboardText = '';
            const medals = ['🥇', '🥈', '🥉'];

            leaderboard.forEach((user, index) => {
                const position = index + 1;
                const medal = index < 3 ? medals[index] : `**${position}.**`;
                
                leaderboardText += `${medal} **${user.username}**\n`;
                leaderboardText += `├ Melange: ${user.total_melange.toLocaleString()}\n`;
                leaderboardText += `└ Sand: ${user.total_sand.toLocaleString()}\n\n`;
            });

            // Calculate total stats
            const totalMelange = leaderboard.reduce((sum, user) => sum + user.total_melange, 0);
            const totalSand = leaderboard.reduce((sum, user) => sum + user.total_sand, 0);

            const responseMessage = {
                embeds: [{
                    title: '🏆 Melange Refining Leaderboard',
                    description: leaderboardText,
                    color: 0xF39C12,
                    fields: [
                        {
                            name: '📊 Community Stats',
                            value: `**Total Refiners:** ${leaderboard.length}\n**Total Melange:** ${totalMelange.toLocaleString()}\n**Total Sand:** ${totalSand.toLocaleString()}`,
                            inline: true
                        },
                        {
                            name: '⚙️ Current Rate',
                            value: `${sandPerMelange} sand = 1 melange`,
                            inline: true
                        }
                    ],
                    footer: {
                        text: `Showing top ${leaderboard.length} refiners • Updated`,
                        icon_url: interaction.client.user.displayAvatarURL()
                    },
                    timestamp: new Date().toISOString()
                }]
            };

            await interaction.reply(responseMessage);

        } catch (error) {
            console.error('Error in leaderboard command:', error);
            await interaction.reply({
                content: '❌ An error occurred while retrieving the leaderboard. Please try again later.',
                ephemeral: true
            });
        }
    }
};
