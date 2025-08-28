const { SlashCommandBuilder } = require('discord.js');
const { getUser, getSetting } = require('../database');
const { checkRateLimit } = require('../utils/rateLimiter');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('myrefines')
        .setDescription('Show your total sand and melange statistics'),

    async execute(interaction) {
        // Check rate limit
        if (!checkRateLimit(interaction.user.id, 'myrefines')) {
            return interaction.reply({
                content: '⏰ Please wait before using this command again.',
                ephemeral: true
            });
        }

        const userId = interaction.user.id;
        const username = interaction.user.username;

        try {
            // Get user data
            const user = await getUser(userId);

            if (!user) {
                return interaction.reply({
                    embeds: [{
                        title: '📊 Your Refining Statistics',
                        description: '🏜️ You haven\'t deposited any sand yet! Use `/logsolo` to start tracking your deposits.',
                        color: 0x95A5A6,
                        footer: {
                            text: `Requested by ${username}`,
                            icon_url: interaction.user.displayAvatarURL()
                        },
                        timestamp: new Date().toISOString()
                    }],
                    ephemeral: true
                });
            }

            // Get conversion rate
            const sandPerMelange = parseInt(await getSetting('sand_per_melange')) || 50;

            // Calculate progress to next melange
            const remainingSand = user.total_sand % sandPerMelange;
            const sandNeededForNextMelange = sandPerMelange - remainingSand;
            const progressPercent = Math.floor((remainingSand / sandPerMelange) * 100);

            // Create progress bar
            const progressBarLength = 10;
            const filledBars = Math.floor((remainingSand / sandPerMelange) * progressBarLength);
            const emptyBars = progressBarLength - filledBars;
            const progressBar = '▓'.repeat(filledBars) + '░'.repeat(emptyBars);

            // Format last updated date
            const lastUpdated = new Date(user.last_updated).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            const responseMessage = {
                embeds: [{
                    title: '📊 Your Refining Statistics',
                    color: 0x3498DB,
                    thumbnail: {
                        url: interaction.user.displayAvatarURL()
                    },
                    fields: [
                        {
                            name: '🏜️ Sand Deposits',
                            value: `**Total Sand:** ${user.total_sand.toLocaleString()}`,
                            inline: true
                        },
                        {
                            name: '✨ Melange Refined',
                            value: `**Total Melange:** ${user.total_melange.toLocaleString()}`,
                            inline: true
                        },
                        {
                            name: '⚙️ Conversion Rate',
                            value: `${sandPerMelange} sand = 1 melange`,
                            inline: true
                        },
                        {
                            name: '🎯 Progress to Next Melange',
                            value: `${progressBar} ${progressPercent}%\n**Sand Needed:** ${sandNeededForNextMelange.toLocaleString()}`,
                            inline: false
                        },
                        {
                            name: '📅 Last Activity',
                            value: lastUpdated,
                            inline: false
                        }
                    ],
                    footer: {
                        text: `Spice Tracker • ${username}`,
                        icon_url: interaction.user.displayAvatarURL()
                    },
                    timestamp: new Date().toISOString()
                }]
            };

            await interaction.reply(responseMessage);

        } catch (error) {
            console.error('Error in myrefines command:', error);
            await interaction.reply({
                content: '❌ An error occurred while retrieving your statistics. Please try again later.',
                ephemeral: true
            });
        }
    }
};
