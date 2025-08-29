# 🗄️ Supabase Setup Guide

This directory contains everything you need to set up your Supabase database for the Spice Tracker Bot.

## 📁 Files Overview

- **`config.toml`** - Local Supabase development configuration
- **`migrations/20240101000000_initial_schema.sql`** - Database schema migration
- **`seed.sql`** - Sample data for development and testing
- **`setup.sh`** - Automated setup script (Linux/macOS)
- **`setup.ps1`** - Automated setup script (Windows PowerShell)
- **`README.md`** - This file

## 🚀 Quick Setup

### Prerequisites

1. **Supabase Account**: [Sign up at supabase.com](https://supabase.com)
2. **Node.js**: For Supabase CLI installation
3. **Git**: For version control

### Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click "New Project"
3. Choose your organization
4. Enter project name: `spice-tracker-bot`
5. Enter a strong database password (save this!)
6. Choose a region closest to your users
7. Click "Create new project"
8. Wait for project setup (2-3 minutes)

### Step 2: Get Project Reference

1. In your Supabase dashboard, note the project reference from the URL:
   ```
   https://supabase.com/dashboard/project/[YOUR-PROJECT-REF]
   ```
2. Save this reference - you'll need it for the setup

### Step 3: Install Supabase CLI

```bash
# Install globally
npm install -g supabase

# Verify installation
supabase --version
```

### Step 4: Run Setup Script

#### Option A: Automated Setup (Recommended)

**Linux/macOS:**
```bash
# Make script executable
chmod +x supabase/setup.sh

# Run setup
./supabase/setup.sh
```

**Windows PowerShell:**
```powershell
# Run setup script
.\supabase\setup.ps1

# Or with project reference
.\supabase\setup.ps1 -ProjectRef "your-project-ref"
```

#### Option B: Manual Setup

```bash
# Navigate to project root
cd spice-tracker-bot

# Initialize Supabase
supabase init

# Link to your project
supabase link --project-ref [YOUR-PROJECT-REF]

# Run migrations
supabase db push

# Optional: Seed with sample data
supabase db reset --linked
```

## 🗄️ Database Schema

### Tables Created

1. **`users`** - Player information and melange totals
2. **`deposits`** - Individual spice sand harvests
3. **`settings`** - Bot configuration options
4. **`audit_log`** - Change tracking and history

### Views Created

1. **`user_stats`** - Comprehensive user statistics
2. **`leaderboard`** - User rankings by melange production

### Features

- **UUID Primary Keys** for better scalability
- **Automatic Timestamps** for all records
- **Foreign Key Constraints** for data integrity
- **Check Constraints** for data validation
- **Optimized Indexes** for performance
- **Row Level Security** for data protection
- **Audit Logging** for change tracking
- **Triggers** for automatic updates

## 🔧 Configuration

### Default Settings

The migration creates these default settings:

- **`sand_per_melange`**: 50 (sand required for 1 melange)
- **`default_harvester_percentage`**: 25.0% (primary harvester cut)
- **`max_sand_per_harvest`**: 10,000 (maximum per harvest)
- **`min_sand_per_harvest`**: 1 (minimum per harvest)

### Customizing Settings

You can modify these values after setup:

```sql
-- Update conversion rate
UPDATE settings SET value = '75' WHERE key = 'sand_per_melange';

-- Update harvester percentage
UPDATE settings SET value = '30.0' WHERE key = 'default_harvester_percentage';
```

## 🌱 Sample Data

The seed file includes:

- **5 sample users** with different melange totals
- **15 sample deposits** with various amounts and dates
- **Realistic data** for testing bot functionality

## 🔍 Database Operations

### Viewing Data

```sql
-- Check all users
SELECT * FROM user_stats;

-- View leaderboard
SELECT * FROM leaderboard LIMIT 10;

-- Check settings
SELECT * FROM settings;

-- View recent deposits
SELECT * FROM deposits ORDER BY created_at DESC LIMIT 20;
```

### Monitoring Changes

```sql
-- View audit log
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 50;

-- Check specific user changes
SELECT * FROM audit_log WHERE user_id = '123456789012345678';
```

## 🚨 Troubleshooting

### Common Issues

1. **"Project not found"**
   - Verify your project reference is correct
   - Ensure you're logged into the right Supabase account

2. **"Permission denied"**
   - Check that your database password is correct
   - Verify your project is active and not paused

3. **"Migration failed"**
   - Check the error message for specific issues
   - Ensure your database is accessible

4. **"CLI not found"**
   - Reinstall Supabase CLI: `npm install -g supabase`
   - Restart your terminal after installation

### Getting Help

- **Supabase Documentation**: [docs.supabase.com](https://docs.supabase.com)
- **Supabase Discord**: [discord.gg/supabase](https://discord.gg/supabase)
- **GitHub Issues**: Check the main repository for known issues

## 🔐 Security Features

### Row Level Security (RLS)

- **Users table**: Users can only modify their own data
- **Deposits table**: Users can only modify their own deposits
- **Settings table**: Read-only for most users, updatable by admins
- **Audit log**: System-generated, read-only for users

### Data Protection

- **Input validation** with check constraints
- **Foreign key constraints** for referential integrity
- **Audit logging** for all data changes
- **Secure connection** via SSL

## 📊 Performance Optimization

### Indexes

- **User lookups**: `user_id` primary key
- **Username searches**: `username` index
- **Leaderboard queries**: `total_melange` descending index
- **Deposit queries**: `user_id`, `created_at`, `paid` indexes
- **Audit queries**: `action`, `user_id`, `created_at` indexes

### Views

- **`user_stats`**: Pre-computed user statistics
- **`leaderboard`**: Optimized ranking queries

## 🔄 Database Migrations

### Adding New Migrations

```bash
# Create a new migration
supabase migration new add_new_feature

# Edit the generated file in supabase/migrations/
# Then apply it
supabase db push
```

### Rolling Back

```bash
# Reset to a specific migration
supabase db reset --linked

# Or reset to a specific commit
supabase db reset --linked --commit [COMMIT_HASH]
```

## 🌐 Connection String

After setup, your database connection string will be:

```
postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

**Important**: Replace `[YOUR-PASSWORD]` with your actual database password and `[YOUR-PROJECT-REF]` with your project reference.

## 🚀 Next Steps

1. **Test your database** with the sample data
2. **Get your connection string** from Supabase dashboard
3. **Set environment variables** in Fly.io
4. **Deploy your bot** and test the database connection

---

**Happy Database Setup! 🎉**
