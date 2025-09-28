import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from commands.settings import Settings

@pytest.fixture
def mock_interaction():
    """Provides a default mock interaction object."""
    interaction = AsyncMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 12345
    interaction.user.display_name = "Test Admin"
    return interaction

@pytest.fixture
def settings_cog(mocker):
    """Provides a Settings cog instance with mocked dependencies."""
    mock_bot = MagicMock()

    # Mock dependencies used by the commands in the 'commands.settings' module
    mock_db_instance = AsyncMock()
    mocker.patch('commands.settings.get_database', return_value=mock_db_instance)
    mocker.patch('commands.settings.check_permission', return_value=True) # Assume admin for all tests
    mocker.patch('commands.settings.log_command_metrics')
    mocker.patch('commands.settings.logger')
    mocker.patch('commands.settings.build_status_embed', return_value=MagicMock(build=lambda: "embed_obj"))
    mocker.patch('commands.settings.update_landsraad_bonus_status')
    mocker.patch('commands.settings.get_sand_per_melange_with_bonus', return_value=50)

    async def mock_timed_db_op(name, coro_func, *args, **kwargs):
        result = await coro_func(*args, **kwargs)
        return result, 0.1

    mocker.patch('commands.settings.timed_database_operation', side_effect=mock_timed_db_op)

    cog = Settings(mock_bot)
    cog.mock_db = mock_db_instance
    return cog

@pytest.mark.asyncio
async def test_settings_landsraad_status(settings_cog, mock_interaction):
    # Given
    settings_cog.mock_db.get_global_setting.return_value = 'true'

    # When
    await settings_cog.landsraad.callback(settings_cog, mock_interaction, action='status')

    # Then
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    settings_cog.mock_db.get_global_setting.assert_called_once_with('landsraad_bonus_active')
    mock_interaction.followup.send.assert_called_once_with(embed="embed_obj")

@pytest.mark.asyncio
async def test_settings_landsraad_enable(settings_cog, mock_interaction):
    # Given
    settings_cog.mock_db.set_global_setting = AsyncMock()

    # When
    await settings_cog.landsraad.callback(settings_cog, mock_interaction, action='enable', confirm=True)

    # Then
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    settings_cog.mock_db.set_global_setting.assert_called_once_with(
        'landsraad_bonus_active',
        'true',
        'Whether the landsraad bonus is active (37.5 sand = 1 melange instead of 50)'
    )
    mock_interaction.followup.send.assert_called_once_with(embed="embed_obj")