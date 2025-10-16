import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the command object from the commands package
from commands import COMMANDS

dbsync_command = COMMANDS['dbsync']

@pytest.mark.asyncio
@patch('os.getenv')
@patch('commands.dbsync.get_database')
@patch('commands.dbsync.send_response')
async def test_dbsync_command_postgres_owner(mock_send_response, mock_get_database, mock_getenv):
    """
    Tests that the dbsync command calls the resync_sequences method when called by the bot owner.
    """
    # Arrange
    mock_getenv.return_value = '12345'
    mock_db = MagicMock()
    mock_db.is_sqlite = False
    mock_db.resync_sequences = AsyncMock(return_value={'users_id_seq': 101})
    mock_get_database.return_value = mock_db

    mock_interaction = AsyncMock()
    mock_interaction.user.id = 12345

    # Act
    await dbsync_command(mock_interaction)

    # Assert
    mock_db.resync_sequences.assert_called_once()
    call_args, call_kwargs = mock_send_response.call_args
    embed = call_kwargs['embed']
    assert "✅ Database Sync Complete" in embed.title
    assert "users_id_seq" in embed.description

@pytest.mark.asyncio
@patch('os.getenv')
@patch('commands.dbsync.send_response')
async def test_dbsync_command_not_owner(mock_send_response, mock_getenv):
    """
    Tests that the dbsync command sends a permission error when called by a non-owner.
    """
    # Arrange
    mock_getenv.return_value = '12345'
    mock_interaction = AsyncMock()
    mock_interaction.user.id = 54321

    # Act
    await dbsync_command(mock_interaction)

    # Assert
    mock_send_response.assert_called_once()
    call_args, call_kwargs = mock_send_response.call_args
    # The message is the second positional argument passed to send_response
    assert "❌ Only the bot owner can use this command." in call_args[1]

@pytest.mark.asyncio
@patch('os.getenv')
@patch('commands.dbsync.get_database')
@patch('commands.dbsync.send_response')
async def test_dbsync_command_sqlite(mock_send_response, mock_get_database, mock_getenv):
    """
    Tests that the dbsync command does not call the resync_sequences method on a SQLite database.
    """
    # Arrange
    mock_getenv.return_value = '12345'
    mock_db = MagicMock()
    mock_db.is_sqlite = True
    mock_db.resync_sequences = AsyncMock()
    mock_get_database.return_value = mock_db

    mock_interaction = AsyncMock()
    mock_interaction.user.id = 12345

    # Act
    await dbsync_command(mock_interaction)

    # Assert
    mock_db.resync_sequences.assert_not_called()
    # Verifies that the sqlite warning embed is sent via send_response
    call_args, call_kwargs = mock_send_response.call_args
    embed = call_kwargs['embed']
    assert "only applicable for PostgreSQL" in embed.description