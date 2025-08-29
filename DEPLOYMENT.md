# 🚀 Deployment Guide

This guide will walk you through deploying the Spice Tracker Bot to Fly.io with Supabase as the database.

## 📋 Prerequisites

- [GitHub account](https://github.com)
- [Discord Developer account](https://discord.com/developers)
- [Fly.io account](https://fly.io)
- [Supabase account](https://supabase.com)

## 🔧 Step 1: Discord Bot Setup

1. **Create Discord Application**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application" and give it a name
   - Go to "Bot" section and click "Add Bot"
   - Copy the bot token (you'll need this later)

2. **Configure Bot Permissions**:
   - In the Bot section, enable these permissions:
     - Send Messages
     - Use Slash Commands
     - Read Message History
   - Copy the Client ID (you'll need this later)

3. **Invite Bot to Server**:
   - Go to "OAuth2 > URL Generator"
   - Select scopes: `bot`, `applications.commands`
   - Select the permissions from step 2
   - Use the generated URL to invite the bot to your server

## 🗄️ Step 2: Supabase Database Setup

1. **Create Supabase Project**:
   - Go to [supabase.com](https://supabase.com) and sign up/login
   - Click "New Project"
   - Choose your organization
   - Enter project name: `spice-tracker-bot`
   - Enter database password (save this!)
   - Choose region closest to your users
   - Click "Create new project"

2. **Wait for Project Setup**:
   - This usually takes 2-3 minutes
   - You'll see "Project is ready" when complete

3. **Get Database Connection String**:
   - Go to Settings → Database
   - Copy the connection string from "Connection string" section
   - It looks like: `postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres`

4. **Run Database Migrations**:
   ```bash
   # Install Supabase CLI
   npm install -g supabase
   
   # Clone this repository
   git clone https://github.com/jaqknife777/spice-tracker-bot.git
   cd spice-tracker-bot
   
   # Link to your project (replace with your project ref)
   supabase link --project-ref [YOUR-PROJECT-REF]
   
   # Run migrations
   supabase db push
   ```

## 🚀 Step 3: Fly.io Setup

1. **Install Fly CLI**:
   ```bash
   # macOS/Linux
   curl -L https://fly.io/install.sh | sh
   
   # Windows (using PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login to Fly.io**:
   ```bash
   fly auth login
   ```

3. **Create Fly App**:
   ```bash
   fly apps create spice-tracker-bot
   ```

4. **Set Environment Variables**:
   ```bash
   # Set Discord bot token
   fly secrets set DISCORD_TOKEN="your_bot_token_here"
   
   # Set Discord client ID
   fly secrets set CLIENT_ID="your_client_id_here"
   
   # Set Supabase database URL
   fly secrets set DATABASE_URL="your_supabase_connection_string_here"
   
   # Optional: Set admin role IDs
   fly secrets set ADMIN_ROLE_IDS="123456789,987654321"
   
   # Optional: Set allowed role IDs
   fly secrets set ALLOWED_ROLE_IDS="111222333,444555666"
   ```

5. **Deploy the Bot**:
   ```bash
   fly deploy
   ```

## 🔄 Step 4: GitHub Actions Setup (Automatic Deployment)

1. **Fork this Repository**:
   - Go to [spice-tracker-bot](https://github.com/jaqknife777/spice-tracker-bot)
   - Click "Fork" to create your own copy

2. **Get Fly API Token**:
   - Go to [Fly.io Dashboard](https://fly.io/user/personal_access_tokens)
   - Click "New Token"
   - Give it a name like "GitHub Actions"
   - Copy the token

3. **Add GitHub Secret**:
   - Go to your forked repository
   - Go to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `FLY_API_TOKEN`
   - Value: Your Fly API token from step 2

4. **Update Fly App Name** (if different):
   - Edit `.github/workflows/ci.yml`
   - Change `flyctl deploy --remote-only` to `flyctl deploy --remote-only -a your-app-name`

5. **Push to Main**:
   - Make any change to your repository
   - Push to the main branch
   - GitHub Actions will automatically:
     - Run tests
     - Deploy to Fly.io (if tests pass)

## 🧪 Step 5: Testing Your Deployment

1. **Check Bot Status**:
   ```bash
   # Check Fly.io app status
   fly status -a spice-tracker-bot
   
   # Check logs
   fly logs -a spice-tracker-bot
   ```

2. **Test Bot Commands**:
   - Go to your Discord server
   - Try `/help` command
   - Test basic commands like `/spicesolo 100`

3. **Verify Database**:
   - Go to Supabase Dashboard → Table Editor
   - Check if tables were created
   - Verify data is being stored

## 🔧 Troubleshooting

### Bot Not Responding
- Check Fly.io logs: `fly logs -a spice-tracker-bot`
- Verify `DISCORD_TOKEN` is set correctly
- Ensure bot has proper permissions in Discord

### Database Connection Issues
- Verify `DATABASE_URL` format is correct
- Check Supabase project is active
- Ensure database password is correct

### Deployment Failures
- Check GitHub Actions logs
- Verify `FLY_API_TOKEN` is set correctly
- Ensure Fly.io app exists and is accessible

### Local Development
```bash
# Set environment variables
export DISCORD_TOKEN="your_bot_token"
export CLIENT_ID="your_client_id"
export DATABASE_URL="your_supabase_url"

# Run bot locally
python bot.py
```

## 📚 Additional Resources

- [Fly.io Documentation](https://fly.io/docs/)
- [Supabase Documentation](https://supabase.com/docs)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## 🆘 Need Help?

- Check the [GitHub Issues](https://github.com/jaqknife777/spice-tracker-bot/issues)
- Review [GitHub Actions logs](https://github.com/jaqknife777/spice-tracker-bot/actions)
- Check [Fly.io status page](https://status.fly.io/)

---

**Happy Deploying! 🚀**
