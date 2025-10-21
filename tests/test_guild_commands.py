import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

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
    interaction.created_at = datetime.now()  # Use a real datetime
    return interaction


@pytest.fixture
def guild_cog(mocker):
    """Provides a Guild cog instance with mocked dependencies."""
    mock_bot = MagicMock()

    async def mock_timed_db_op(name, coro_func, *args, **kwargs):
        result = await coro_func(*args, **kwargs)
        return result, 0.1

    mock_db_instance = AsyncMock()
    mocker.patch("commands.guild.get_database", return_value=mock_db_instance)
    mocker.patch("commands.guild.log_command_metrics")
    mocker.patch("commands.guild.logger")
    mocker.patch(
        "commands.guild.timed_database_operation", side_effect=mock_timed_db_op
    )

    # Create a more realistic mock for EmbedBuilder
    mock_embed_builder = MagicMock()
    mock_embed_builder.set_footer.return_value = mock_embed_builder
    # The built embed is also a mock, so we can inspect its attributes
    built_embed = MagicMock()
    # Let's give it a default description that can be changed per-test
    built_embed.description = "Default Mock Embed Description"
    mock_embed_builder.build.return_value = built_embed

    # Patch build_status_embed where it is used. This is key.
    # The commands call functions in pagination_utils, which then call build_status_embed.
    mocker.patch(
        "utils.pagination_utils.build_status_embed", return_value=mock_embed_builder
    )
    mocker.patch("commands.guild.build_status_embed", return_value=mock_embed_builder)

    cog = Guild(mock_bot)
    cog.mock_db = mock_db_instance
    # Attach the built embed to the cog for easy access in tests
    cog.built_embed = built_embed
    return cog


@pytest.mark.asyncio
async def test_guild_treasury_success(guild_cog, mock_interaction):
    # Given: Configure the mock database to return a specific treasury value
    guild_cog.mock_db.get_guild_treasury.return_value = {
        "total_melange": 5000,
        "last_updated": datetime.now(),
    }

    # When: The treasury command is executed
    await guild_cog.treasury.callback(guild_cog, mock_interaction)

    # Then: Verify the command's behavior
    mock_interaction.response.defer.assert_called_once()
    guild_cog.mock_db.get_guild_treasury.assert_called_once()
    # Check that the followup message was sent with the correct embed
    mock_interaction.followup.send.assert_called_once_with(embed=guild_cog.built_embed)


@pytest.mark.asyncio
async def test_guild_withdraw_success(guild_cog, mock_interaction):
    # Given: Configure the mock database for a successful withdrawal
    guild_cog.mock_db.get_guild_treasury.return_value = {"total_melange": 5000}
    guild_cog.mock_db.guild_withdraw.return_value = 4000

    mock_user = MagicMock()
    mock_user.id = 67890
    mock_user.display_name = "Recipient"
    amount = 1000

    # When: The withdraw command is executed
    await guild_cog.withdraw.callback(
        guild_cog, mock_interaction, user=mock_user, amount=amount
    )

    # Then: Verify the command's behavior
    mock_interaction.response.defer.assert_called_once()
    guild_cog.mock_db.get_guild_treasury.assert_called_once()
    guild_cog.mock_db.guild_withdraw.assert_called_once_with(
        str(mock_interaction.user.id),
        mock_interaction.user.display_name,
        str(mock_user.id),
        mock_user.display_name,
        amount,
    )
    mock_interaction.followup.send.assert_called_once_with(embed=guild_cog.built_embed)


@pytest.mark.asyncio
async def test_guild_withdraw_insufficient_funds(guild_cog, mock_interaction):
    # Given: Configure the mock database to have insufficient funds
    guild_cog.mock_db.get_guild_treasury.return_value = {"total_melange": 500}

    mock_user = MagicMock()
    amount = 1000

    # When: The withdraw command is executed
    await guild_cog.withdraw.callback(
        guild_cog, mock_interaction, user=mock_user, amount=amount
    )

    # Then: Verify the command's behavior
    mock_interaction.response.defer.assert_called_once()
    guild_cog.mock_db.get_guild_treasury.assert_called_once()
    guild_cog.mock_db.guild_withdraw.assert_not_called()
    # Check that an error message about insufficient funds was sent
    mock_interaction.followup.send.assert_called_once()
    # The message is passed as the first positional argument.
    sent_message = mock_interaction.followup.send.call_args.args[0]
    assert "Insufficient guild treasury funds" in sent_message


@pytest.mark.asyncio
async def test_guild_transactions_success(guild_cog, mock_interaction, mocker):
    """Test the guild transactions command with existing transactions."""
    # Given
    guild_cog.mock_db.get_guild_transactions_count.return_value = 1
    mock_transaction = {
        "created_at": datetime.now(),
        "melange_amount": 100,
        "sand_amount": 0,
        "transaction_type": "guild_withdraw",
        "target_username": "some_user",
        "admin_username": "some_admin",
        "expedition_id": None,
    }
    guild_cog.mock_db.get_guild_transactions_paginated.return_value = [mock_transaction]

    mock_view_instance = mocker.patch(
        "commands.guild.PaginatedView", autospec=True
    ).return_value
    mock_view_instance.total_pages = 1

    # When
    await guild_cog.transactions.callback(guild_cog, mock_interaction)

    # Then
    guild_cog.mock_db.get_guild_transactions_count.assert_called_once()
    guild_cog.mock_db.get_guild_transactions_paginated.assert_called_once()
    mock_interaction.followup.send.assert_called_once_with(
        embed=guild_cog.built_embed, view=mock_view_instance, ephemeral=True
    )


@pytest.mark.asyncio
async def test_guild_transactions_no_results(guild_cog, mock_interaction):
    """Test the guild transactions command with no transactions."""
    # Given
    guild_cog.mock_db.get_guild_transactions_count.return_value = 0
    guild_cog.built_embed.description = "No guild transactions found."

    # When
    await guild_cog.transactions.callback(guild_cog, mock_interaction)

    # Then
    guild_cog.mock_db.get_guild_transactions_count.assert_called_once()
    guild_cog.mock_db.get_guild_transactions_paginated.assert_not_called()
    mock_interaction.followup.send.assert_called_once()
    sent_embed = mock_interaction.followup.send.call_args.kwargs["embed"]
    assert "No guild transactions found" in sent_embed.description


@pytest.mark.asyncio
async def test_guild_payouts_success(guild_cog, mock_interaction, mocker):
    """Test the guild payouts command with existing payouts."""
    # Given
    guild_cog.mock_db.get_melange_payouts_count.return_value = 1
    mock_payout = {
        "created_at": datetime.now(),
        "melange_amount": 200,
        "username": "recipient_user",
        "admin_username": "admin_user",
    }
    guild_cog.mock_db.get_melange_payouts.return_value = [mock_payout]

    mock_view_instance = mocker.patch(
        "commands.guild.PaginatedView", autospec=True
    ).return_value
    mock_view_instance.total_pages = 1

    # When
    await guild_cog.payouts.callback(guild_cog, mock_interaction)

    # Then
    guild_cog.mock_db.get_melange_payouts_count.assert_called_once()
    guild_cog.mock_db.get_melange_payouts.assert_called_once()
    mock_interaction.followup.send.assert_called_once_with(
        embed=guild_cog.built_embed, view=mock_view_instance, ephemeral=True
    )


@pytest.mark.asyncio
async def test_guild_payouts_no_results(guild_cog, mock_interaction):
    """Test the guild payouts command with no payouts."""
    # Given
    guild_cog.mock_db.get_melange_payouts_count.return_value = 0
    guild_cog.built_embed.description = "No melange payouts found."

    # When
    await guild_cog.payouts.callback(guild_cog, mock_interaction)

    # Then
    guild_cog.mock_db.get_melange_payouts_count.assert_called_once()
    guild_cog.mock_db.get_melange_payouts.assert_not_called()
    mock_interaction.followup.send.assert_called_once()
    sent_embed = mock_interaction.followup.send.call_args.kwargs["embed"]
    assert "No melange payouts found" in sent_embed.description
