const { Client, GatewayIntentBits, Collection } = require('discord.js');
const { REST } = require('@discordjs/rest');
const { Routes } = require('discord-api-types/v9');
const fs = require('fs');
require('dotenv').config();

// Import database functions
const { initializeDatabase } = require('./database');

// Create a new client instance
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages
    ]
});

// Create a collection for commands
client.commands = new Collection();

// Load command files
const commandFiles = fs.readdirSync('./commands').filter(file => file.endsWith('.js'));
const commands = [];

for (const file of commandFiles) {
    const command = require(`./commands/${file}`);
    client.commands.set(command.data.name, command);
    commands.push(command.data.toJSON());
}

// Register slash commands
const rest = new REST({ version: '9' }).setToken(process.env.DISCORD_TOKEN || 'your_bot_token_here');

async function registerCommands() {
    try {
        console.log('Started refreshing application (/) commands.');

        await rest.put(
            Routes.applicationCommands(process.env.CLIENT_ID || 'your_client_id_here'),
            { body: commands },
        );

        console.log('Successfully reloaded application (/) commands.');
    } catch (error) {
        console.error('Error registering commands:', error);
    }
}

// Bot ready event
client.once('ready', async () => {
    console.log(`${client.user.tag} is online!`);
    
    // Initialize database
    try {
        await initializeDatabase();
        console.log('Database initialized successfully.');
    } catch (error) {
        console.error('Failed to initialize database:', error);
        process.exit(1);
    }

    // Register commands
    await registerCommands();
});

// Handle slash command interactions
client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;

    const command = client.commands.get(interaction.commandName);

    if (!command) {
        console.error(`No command matching ${interaction.commandName} was found.`);
        return;
    }

    try {
        await command.execute(interaction);
    } catch (error) {
        console.error('Error executing command:', error);
        
        const errorMessage = {
            content: '❌ There was an error while executing this command!',
            ephemeral: true
        };

        if (interaction.replied || interaction.deferred) {
            await interaction.followUp(errorMessage);
        } else {
            await interaction.reply(errorMessage);
        }
    }
});

// Error handling
client.on('error', error => {
    console.error('Discord client error:', error);
});

process.on('unhandledRejection', error => {
    console.error('Unhandled promise rejection:', error);
});

// Login to Discord
client.login(process.env.DISCORD_TOKEN || 'your_bot_token_here');
