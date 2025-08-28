const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { resetAllStats } = require('../database');
const { checkAdminPermission } = require('../utils/permissions');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('resetstats')
        .setDescription('Reset all user statistics (Admin only - USE WITH CAUTION)')
        .addBooleanOption(option =>
            option.setName('confirm')
                .setDescription('Confirm that you want to delete all user data')
                .setRequired(true)
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

        const confirmed = interaction.options.getBoolean('confirm');

        if (!confirmed) {
            return interaction.reply({
                embeds: [{
                    title: '⚠️ Reset Cancelled',
                    description: 'You must set the `confirm` parameter to `True` to proceed with the reset.',
                    color: 0xE74C3C,
                    fields: [
                        {
                            name: '🔄 How to Reset',
                            value: 'Use `/resetstats confirm:True` to confirm the reset.',
                            inline: false
                        }
                    ]
                }],
                ephemeral: true
            });
        }

        try {
            // Reset all user statistics
            const deletedRows = await resetAllStats();

            const responseMessage = {
                embeds: [{
                    title: '🔄 Statistics Reset Complete',
                    description: '⚠️ **All user statistics have been permanently deleted!**',
                    color: 0xE74C3C,
                    fields: [
                        {
                            name: '📊 Reset Summary',
                            value: `**Users Affected:** ${deletedRows}\n**Data Cleared:** All sand deposits and melange statistics`,
                            inline: false
                        },
                        {
                            name: '✅ What Remains',
                            value: 'Conversion rates and bot settings are preserved.',
                            inline: false
                        }
                    ],
                    footer: {
                        text: `Reset performed by ${interaction.user.username}`,
                        icon_url: interaction.user.displayAvatarURL()
                    },
                    timestamp: new Date().toISOString()
                }]
            };

            await interaction.reply(responseMessage);

            // Log the reset action
            console.log(`All user statistics reset by ${interaction.user.username} (${interaction.user.id}) - ${deletedRows} records deleted`);

        } catch (error) {
            console.error('Error in resetstats command:', error);
            await interaction.reply({
                content: '❌ An error occurred while resetting statistics. Please try again later.',
                ephemeral: true
            });
        }
    }
};
