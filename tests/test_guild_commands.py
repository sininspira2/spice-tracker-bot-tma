import pytest
from unittest.mock import AsyncMock, MagicMock

# Import the class to be tested
from commands.guild import Guild

@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    # Mock the user object with required attributes
    interaction.user = MagicMock()
    interaction.user.id = 12345
    interaction.user.display_name = "Test User"
    interaction.created_at = MagicMock()
    return interaction

@pytest.fixture
def guild_cog(mocker):
    """Provides a Guild cog instance with mocked dependencies."""
    mock_bot = MagicMock()

    # This async function will be the side_effect for our mock of timed_database_operation
    async def mock_timed_db_op(name, coro_func, *args, **kwargs):
        # Await the coroutine function passed to it, which simulates the DB call
        result = await coro_func(*args, **kwargs)
        # Return the result and a dummy time, matching the original function's signature
        return result, 0.1

    # Mock dependencies used by the commands in the 'commands.guild' module
    mock_db_instance = AsyncMock()
    mocker.patch('commands.guild.get_database', return_value=mock_db_instance)
    mocker.patch('commands.guild.log_command_metrics')
    mocker.patch('commands.guild.logger')
    mocker.patch('commands.guild.build_status_embed', return_value=MagicMock(build=lambda: "embed_obj"))
    mocker.patch('commands.guild.timed_database_operation', side_effect=mock_timed_db_op)

    cog = Guild(mock_bot)
    # Attach the mock database instance to the cog for easy access in tests
    cog.mock_db = mock_db_instance
    return cog

@pytest.mark.asyncio
async def test_guild_treasury_success(guild_cog, mock_interaction):
    # Given: Configure the mock database to return a specific treasury value
    guild_cog.mock_db.get_guild_treasury.return_value = {'total_melange': 5000}

    # When: The treasury command is executed
    await guild_cog.treasury.callback(guild_cog, mock_interaction)

    # Then: Verify the command's behavior
    mock_interaction.response.defer.assert_called_once()
    guild_cog.mock_db.get_guild_treasury.assert_called_once()
    # Check that the followup message was sent with the correct embed
    mock_interaction.followup.send.assert_called_once_with(embed="embed_obj")

@pytest.mark.asyncio
async def test_guild_withdraw_success(guild_cog, mock_interaction):
    # Given: Configure the mock database for a successful withdrawal
    guild_cog.mock_db.get_guild_treasury.return_value = {'total_melange': 5000}
    guild_cog.mock_db.guild_withdraw.return_value = 4000

    mock_user = MagicMock()
    mock_user.id = 67890
    mock_user.display_name = "Recipient"
    amount = 1000

    # When: The withdraw command is executed
    await guild_cog.withdraw.callback(guild_cog, mock_interaction, user=mock_user, amount=amount)

    # Then: Verify the command's behavior
    mock_interaction.response.defer.assert_called_once()
    guild_cog.mock_db.get_guild_treasury.assert_called_once()
    guild_cog.mock_db.guild_withdraw.assert_called_once_with(
        str(mock_interaction.user.id), mock_interaction.user.display_name,
        str(mock_user.id), mock_user.display_name, amount
    )
    mock_interaction.followup.send.assert_called_once_with(embed="embed_obj")

@pytest.mark.asyncio
async def test_guild_withdraw_insufficient_funds(guild_cog, mock_interaction):
    # Given: Configure the mock database to have insufficient funds
    guild_cog.mock_db.get_guild_treasury.return_value = {'total_melange': 500}

    mock_user = MagicMock()
    amount = 1000

    # When: The withdraw command is executed
    await guild_cog.withdraw.callback(guild_cog, mock_interaction, user=mock_user, amount=amount)

    # Then: Verify the command's behavior
    mock_interaction.response.defer.assert_called_once()
    guild_cog.mock_db.get_guild_treasury.assert_called_once()
    guild_cog.mock_db.guild_withdraw.assert_not_called()
    # Check that an error message about insufficient funds was sent
    mock_interaction.followup.send.assert_called_once()
    # The message is passed as the first positional argument.
    sent_message = mock_interaction.followup.send.call_args.args[0]
    assert "Insufficient guild treasury funds" in sent_message