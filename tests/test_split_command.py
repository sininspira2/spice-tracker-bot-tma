import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from commands.split import split
import datetime

@pytest.fixture
def mock_interaction():
    """Fixture for a mock Discord interaction."""
    interaction = MagicMock()
    interaction.user.id = 'user123'
    interaction.user.display_name = 'TestUser'
    interaction.guild.fetch_member = AsyncMock()
    interaction.client.fetch_user = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.created_at = datetime.datetime.now(datetime.timezone.utc)
    # Add a mock for send_response
    interaction.response.send = AsyncMock()
    return interaction

@pytest.fixture
def mock_database():
    """Fixture for a mock database."""
    db = MagicMock()
    db.create_expedition = AsyncMock(return_value=1)
    db.add_expedition_participant = AsyncMock()
    db.add_deposit = AsyncMock()
    db.update_user_melange = AsyncMock()
    db.update_guild_treasury = AsyncMock()
    db.add_guild_transaction = AsyncMock()
    db.get_user_melange = AsyncMock(return_value=1000)
    db.get_sand_per_melange = AsyncMock(return_value=50)
    db.get_user = AsyncMock(return_value=None)
    db.upsert_user = AsyncMock()
    return db

@pytest.mark.asyncio
@patch('commands.split.send_response')
@patch('commands.split.get_database')
@patch('commands.split.convert_sand_to_melange')
@patch('utils.helpers.get_sand_per_melange_with_bonus')
async def test_split_invalid_mixed_split(mock_get_sand_per_melange, mock_convert_sand, mock_get_db, mock_send_response, mock_interaction, mock_database):
    """Test the validation for an invalid mixed split that would result in negative melange."""
    mock_get_db.return_value = mock_database
    mock_convert_sand.return_value = (1000, 0)
    mock_get_sand_per_melange.return_value = 1

    await split.__wrapped__(mock_interaction, "start", 1000, "<@101> 95 <@102>", guild=10, use_followup=True)

    mock_send_response.assert_called_once()
    call_args, call_kwargs = mock_send_response.call_args
    assert "Invalid split" in call_args[1]
    assert mock_database.update_guild_treasury.call_count == 0

@pytest.mark.asyncio
@patch('commands.split.get_database')
@patch('commands.split.convert_sand_to_melange')
@patch('utils.helpers.get_sand_per_melange_with_bonus')
async def test_split_all_percentage(mock_get_sand_per_melange, mock_convert_sand, mock_get_db, mock_interaction, mock_database):
    """Test the /split command with all users having percentages."""
    mock_get_db.return_value = mock_database
    mock_convert_sand.return_value = (2000, 0)
    mock_get_sand_per_melange.return_value = 37.5

    await split.__wrapped__(mock_interaction, "start", 75000, "<@101> 5 <@102> 5", guild=10, use_followup=False)

    mock_database.update_guild_treasury.assert_called_once_with(0, 1800)
    calls = mock_database.add_deposit.call_args_list
    user_101 = next(c for c in calls if c[0][0] == '101')
    user_102 = next(c for c in calls if c[0][0] == '102')
    assert user_101[1]['melange_amount'] == 100
    assert user_102[1]['melange_amount'] == 100

@pytest.mark.asyncio
@patch('commands.split.get_database')
@patch('commands.split.convert_sand_to_melange')
@patch('utils.helpers.get_sand_per_melange_with_bonus')
async def test_split_equal(mock_get_sand_per_melange, mock_convert_sand, mock_get_db, mock_interaction, mock_database):
    """Test the /split command with equal split."""
    mock_get_db.return_value = mock_database
    mock_convert_sand.return_value = (2000, 0)
    mock_get_sand_per_melange.return_value = 37.5

    await split.__wrapped__(mock_interaction, "start", 75000, "<@101> <@102>", guild=10, use_followup=False)

    mock_database.update_guild_treasury.assert_called_once_with(0, 200)
    calls = mock_database.add_deposit.call_args_list
    user_101 = next(c for c in calls if c[0][0] == '101')
    user_102 = next(c for c in calls if c[0][0] == '102')
    assert user_101[1]['melange_amount'] == 900
    assert user_102[1]['melange_amount'] == 900

@pytest.mark.asyncio
@patch('commands.split.get_database')
@patch('commands.split.convert_sand_to_melange')
@patch('utils.helpers.get_sand_per_melange_with_bonus')
async def test_split_mixed(mock_get_sand_per_melange, mock_convert_sand, mock_get_db, mock_interaction, mock_database):
    """Test the /split command with mixed percentages and equal split."""
    mock_get_db.return_value = mock_database
    mock_convert_sand.return_value = (2000, 0)
    mock_get_sand_per_melange.return_value = 37.5

    await split.__wrapped__(mock_interaction, "start", 75000, "<@101> 5 <@102>", guild=10, use_followup=False)

    mock_database.update_guild_treasury.assert_called_once_with(0, 200)
    calls = mock_database.add_deposit.call_args_list
    user_101 = next(c for c in calls if c[0][0] == '101')
    user_102 = next(c for c in calls if c[0][0] == '102')
    assert user_101[1]['melange_amount'] == 100
    assert user_102[1]['melange_amount'] == 1700
