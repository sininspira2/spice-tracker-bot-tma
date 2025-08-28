const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { setSetting, getSetting } = require('../database');
const { checkAdminPermission } = require('../utils/permissions');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('setrate')
        .setDescription('Set the sand to melange conversion rate (Admin only)')
        .addIntegerOption(option =>
            option.setName('sand_per_melange')
                .setDescription('Amount of sand required for 1 melange')
                .setRequired(true)
                .setMinValue(1)
                .setMaxValue(1000)
        )
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

    async execute(interaction) {
        // Check admin permissions
        if (!checkAdminPermission(interaction.member)) {
            return interaction.reply({
                content: '❌ You need Administrator permissions to use this command.',
                ephemeral: true
            });
        }

        const newRate = interaction.options.getInteger('sand_per_melange');

        try {
            // Get current rate for comparison
            const currentRate = parseInt(await getSetting('sand_per_melange')) || 50;

            // Update the conversion rate
            await setSetting('sand_per_melange', newRate.toString());

            const responseMessage = {
                embeds: [{
                    title: '⚙️ Conversion Rate Updated',
                    color: 0x27AE60,
                    fields: [
                        {
                            name: '📊 Rate Change',
                            value: `**Previous Rate:** ${currentRate} sand = 1 melange\n**New Rate:** ${newRate} sand = 1 melange`,
                            inline: false
                        },
                        {
                            name: '⚠️ Important Note',
                            value: 'This change affects future calculations only. Existing user stats remain unchanged.',
                            inline: false
                        }
                    ],
                    footer: {
                        text: `Changed by ${interaction.user.username}`,
                        icon_url: interaction.user.displayAvatarURL()
                    },
                    timestamp: new Date().toISOString()
                }]
            };

            await interaction.reply(responseMessage);

            // Log the change
            console.log(`Conversion rate changed from ${currentRate} to ${newRate} by ${interaction.user.username} (${interaction.user.id})`);

        } catch (error) {
            console.error('Error in setrate command:', error);
            await interaction.reply({
                content: '❌ An error occurred while updating the conversion rate. Please try again later.',
                ephemeral: true
            });
        }
    }
};
