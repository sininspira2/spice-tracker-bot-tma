# Spice Refinery System

## Overview

The Spice Refinery Bot has been updated to use a new harvest-based system instead of tracking total sand on the user row. This allows for better tracking of individual spice harvests, payment management, and historical data within the Dune: Awakening universe.

## Key Changes

### Database Structure

- **Removed**: `total_sand` field from the `users` table
- **Added**: New `deposits` table with the following structure:
  - `id`: Unique harvest identifier
  - `user_id`: Discord user ID
  - `username`: Discord username
  - `sand_amount`: Amount of spice sand harvested
  - `paid`: Boolean flag indicating if the harvest has been paid
  - `created_at`: Timestamp when the harvest was recorded
  - `paid_at`: Timestamp when the harvest was marked as paid

### New Commands

#### Harvester Commands

- **`/ledger`** - View your complete spice harvest ledger with payment status

#### Guild Admin Commands

- **`/payment [user]`** - Process payment for a specific harvester's deposits
- **`/payroll`** - Process payments for all unpaid harvesters

### Updated Commands

- **`/harvest`** - Now creates individual harvest records instead of updating a total
- **`/refinery`** - Shows unpaid vs paid harvests separately
- **`/leaderboard`** - Calculates totals from harvest records
- **`/split`** - Split harvested spice among expedition members
- **`/conversion`** - Set refinement rate (renamed from setrate)
- **`/reset`** - Reset refinery statistics (renamed from resetstats)

## Benefits

1. **Individual Harvest Tracking**: Each spice sand harvest is recorded separately
2. **Payment Management**: Guild admins can track and manage harvester payments
3. **Historical Data**: Harvesters can see their complete harvest ledger
4. **Better Analytics**: More granular data for tracking and reporting
5. **Automatic Cleanup**: Old paid harvests are automatically removed after 30 days

## Migration

The system automatically migrates existing users with `total_sand` data:
- Creates a single harvest record for existing total sand
- Marks these harvests as unpaid (ready for payment)
- Removes the old `total_sand` column
- Preserves all existing melange production data

## Payment Workflow

1. Harvesters collect spice sand using `/harvest`
2. Harvests are marked as unpaid by default
3. Guild admins can pay individual harvesters with `/payment @username`
4. Guild admins can pay all harvesters at once with `/payroll`
5. Paid harvests are automatically cleaned up after 30 days

## Database Maintenance

- **Automatic Cleanup**: Runs on bot startup to remove harvests older than 30 days
- **Indexes**: Added for efficient querying by user_id, created_at, and paid status
- **Foreign Keys**: Ensures data integrity between users and harvests

## Example Usage

```
# Harvester collects spice sand
/harvest 250

# Harvester views their harvest ledger
/ledger

# Guild admin pays a specific harvester
/payment @username

# Guild admin processes payroll for all harvesters
/payroll
```

## Technical Details

- **Async Operations**: All database operations are asynchronous for better performance
- **Error Handling**: Comprehensive error handling with logging
- **Transaction Safety**: Uses proper database transactions for data integrity
- **Backward Compatibility**: Existing bot functionality is preserved
- **Dune: Awakening Theme**: Consistent terminology and theming throughout
