import pytest
from unittest.mock import AsyncMock, MagicMock
from commands.split import split

@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = "12345"
    interaction.user.display_name = "Test User"
    interaction.created_at = MagicMock()
    interaction.guild.fetch_member.return_value = MagicMock(display_name="Fetched User")
    interaction.client.fetch_user.return_value = MagicMock(display_name="Fetched User")
    return interaction

@pytest.fixture
def split_mocks(mocker):
    """Mocks dependencies for the split command."""
    mock_db_instance = AsyncMock()
    mocker.patch('commands.split.get_database', return_value=mock_db_instance)
    mocker.patch('commands.split.logger')

    # Mock helpers from utils.helpers
    mocker.patch('commands.split.get_user_cut', return_value=None)
    mocker.patch('commands.split.get_guild_cut', return_value=10)
    mocker.patch('commands.split.get_sand_per_melange_with_bonus', AsyncMock(return_value=50))
    mocker.patch('commands.split.convert_sand_to_melange', AsyncMock(side_effect=lambda x: (x // 50, x % 50)))
    mock_send_response = mocker.patch('commands.split.send_response', new_callable=AsyncMock)

    # Mock helpers from utils.database_utils (imported within the function)
    mocker.patch('utils.database_utils.validate_user_exists', new_callable=AsyncMock)

    # Mock helpers from utils.embed_utils (imported within the function)
    mock_build_embed = mocker.patch('utils.embed_utils.build_status_embed', return_value=MagicMock(build=lambda: "embed_obj"))

    return mock_db_instance, mock_send_response, mock_build_embed

@pytest.mark.asyncio
async def test_split_command_success_equal_split(mock_interaction, split_mocks):
    # Given
    db_mock, send_response_mock, build_embed_mock = split_mocks
    db_mock.create_expedition.return_value = 1 # expedition_id
    total_sand = 10000
    users_str = "<@1> <@2>"

    # When
    await split.__wrapped__(mock_interaction, command_start=0, total_sand=total_sand, users=users_str, guild=10, user_cut=None, use_followup=True)

    # Then
    db_mock.create_expedition.assert_called_once()
    assert db_mock.add_expedition_participant.call_count == 2
    send_response_mock.assert_called_once_with(mock_interaction, embed="embed_obj", use_followup=True)

@pytest.mark.asyncio
async def test_split_command_percentage_split(mock_interaction, split_mocks):
    # Given
    db_mock, send_response_mock, build_embed_mock = split_mocks
    db_mock.create_expedition.return_value = 2
    total_sand = 10000
    users_str = "<@1> 60 <@2> 30"

    # When
    await split.__wrapped__(mock_interaction, command_start=0, total_sand=total_sand, users=users_str, guild=10, user_cut=None, use_followup=True)

    # Then
    db_mock.create_expedition.assert_called_once()
    assert db_mock.add_expedition_participant.call_count == 2
    send_response_mock.assert_called_once_with(mock_interaction, embed="embed_obj", use_followup=True)

@pytest.mark.asyncio
async def test_split_command_invalid_input(mock_interaction, split_mocks):
    # Given
    db_mock, send_response_mock, _ = split_mocks

    # When
    await split.__wrapped__(mock_interaction, command_start=0, total_sand=0, users="<@1>", guild=10, user_cut=None, use_followup=True)

    # Then
    db_mock.create_expedition.assert_not_called()
    send_response_mock.assert_called_once()
    assert "Total spice sand must be at least 1" in send_response_mock.call_args.args[1]