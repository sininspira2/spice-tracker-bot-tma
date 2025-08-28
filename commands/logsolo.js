const { SlashCommandBuilder } = require('discord.js');
const { getUser, upsertUser, updateUserMelange, getSetting } = require('../database');
const { checkRateLimit } = require('../utils/rateLimiter');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('logsolo')
        .setDescription('Log sand deposits and calculate melange conversion')
        .addIntegerOption(option =>
            option.setName('amount')
                .setDescription('Amount of sand to deposit')
                .setRequired(true)
                .setMinValue(1)
                .setMaxValue(10000)
        ),

    async execute(interaction) {
        // Check rate limit
        if (!checkRateLimit(interaction.user.id, 'logsolo')) {
            return interaction.reply({
                content: '⏰ Please wait before using this command again.',
                ephemeral: true
            });
        }

        const sandAmount = interaction.options.getInteger('amount');
        const userId = interaction.user.id;
        const username = interaction.user.username;

        try {
            // Get current conversion rate
            const sandPerMelange = parseInt(await getSetting('sand_per_melange')) || 50;

            // Update user sand
            await upsertUser(userId, username, sandAmount);

            // Get updated user data
            const user = await getUser(userId);
            
            // Calculate melange conversion
            const totalMelangeEarned = Math.floor(user.total_sand / sandPerMelange);
            const currentMelange = user.total_melange || 0;
            const newMelange = totalMelangeEarned - currentMelange;

            // Update melange if new melange earned
            if (newMelange > 0) {
                await updateUserMelange(userId, newMelange);
            }

            // Calculate remaining sand after conversion
            const remainingSand = user.total_sand % sandPerMelange;
            const sandNeededForNextMelange = sandPerMelange - remainingSand;

            // Create response embed
            const responseMessage = {
                embeds: [{
                    title: '🏜️ Sand Deposit Logged',
                    color: 0xE67E22,
                    fields: [
                        {
                            name: '📊 Deposit Summary',
                            value: `**Sand Deposited:** ${sandAmount.toLocaleString()}\n**Total Sand:** ${user.total_sand.toLocaleString()}`,
                            inline: true
                        },
                        {
                            name: '✨ Melange Status',
                            value: `**Total Melange:** ${(currentMelange + newMelange).toLocaleString()}\n**Conversion Rate:** ${sandPerMelange} sand = 1 melange`,
                            inline: true
                        },
                        {
                            name: '🎯 Next Conversion',
                            value: `**Sand Until Next Melange:** ${sandNeededForNextMelange.toLocaleString()}`,
                            inline: false
                        }
                    ],
                    footer: {
                        text: `Requested by ${username}`,
                        icon_url: interaction.user.displayAvatarURL()
                    },
                    timestamp: new Date().toISOString()
                }]
            };

            // Add melange earned notification if applicable
            if (newMelange > 0) {
                responseMessage.embeds[0].description = `🎉 **You earned ${newMelange.toLocaleString()} melange from this deposit!**`;
            }

            await interaction.reply(responseMessage);

        } catch (error) {
            console.error('Error in logsolo command:', error);
            await interaction.reply({
                content: '❌ An error occurred while processing your sand deposit. Please try again later.',
                ephemeral: true
            });
        }
    }
};
