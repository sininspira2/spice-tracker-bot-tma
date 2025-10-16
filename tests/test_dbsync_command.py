import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the command object from the commands package
from commands import COMMANDS

dbsync_command = COMMANDS['dbsync']

@pytest.mark.asyncio
@patch('utils.base_command.check_permission', return_value=True)
@patch('commands.dbsync.get_database')
@patch('commands.dbsync.send_response')
async def test_dbsync_command_postgres(mock_send_response, mock_get_database, mock_check_permission):
    """
    Tests that the dbsync command calls the resync_sequences method on a PostgreSQL database.
    """
    # Arrange
    mock_db = MagicMock()
    mock_db.is_sqlite = False
    mock_db.resync_sequences = AsyncMock(return_value={'users_id_seq': 101})
    mock_get_database.return_value = mock_db

    mock_interaction = AsyncMock()

    # Act
    await dbsync_command(mock_interaction)

    # Assert
    mock_db.resync_sequences.assert_called_once()
    # Verifies that the success embed is sent via send_response
    call_args, call_kwargs = mock_send_response.call_args
    embed = call_kwargs['embed']
    assert "✅ Database Sync Complete" in embed.title
    assert "users_id_seq" in embed.description


@pytest.mark.asyncio
@patch('utils.base_command.check_permission', return_value=True)
@patch('commands.dbsync.get_database')
@patch('commands.dbsync.send_response')
async def test_dbsync_command_sqlite(mock_send_response, mock_get_database, mock_check_permission):
    """
    Tests that the dbsync command does not call the resync_sequences method on a SQLite database.
    """
    # Arrange
    mock_db = MagicMock()
    mock_db.is_sqlite = True
    mock_db.resync_sequences = AsyncMock()
    mock_get_database.return_value = mock_db

    mock_interaction = AsyncMock()

    # Act
    await dbsync_command(mock_interaction)

    # Assert
    mock_db.resync_sequences.assert_not_called()
    # Verifies that the sqlite warning embed is sent via send_response
    call_args, call_kwargs = mock_send_response.call_args
    embed = call_kwargs['embed']
    assert "only applicable for PostgreSQL" in embed.description