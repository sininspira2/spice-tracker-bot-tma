"""
Tests for the '/perms' command.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from commands.perms import perms

@pytest.fixture(autouse=True)
def mock_get_db(mocker, test_database):
    """Fixture to automatically mock get_database in the perms command module."""
    mocker.patch('utils.helpers.get_database', return_value=test_database)
    mocker.patch('commands.perms.get_database', return_value=test_database, create=True)

@pytest.mark.asyncio
async def test_perms_command_formats_roles_as_mentions(mocker, mock_interaction):
    """Test that the /perms command correctly formats role IDs as mentions in the embed."""
    # Mock all external dependencies to isolate the command logic
    mock_send_response = mocker.patch('commands.perms.send_response', new_callable=AsyncMock)
    mocker.patch('commands.perms.is_admin', return_value=True)
    mocker.patch('commands.perms.is_officer', return_value=True)
    mocker.patch('commands.perms.is_allowed_user', return_value=True)
    mocker.patch('commands.perms.get_admin_role_ids', return_value=[101, 102])
    mocker.patch('commands.perms.get_officer_role_ids', return_value=[201, 202])
    mocker.patch('commands.perms.get_allowed_role_ids', return_value=[301, 302])

    # Correctly create mock roles by setting attributes, not using 'name' in constructor
    admin_role = Mock()
    admin_role.id = 101
    admin_role.name = "Admin Role"

    officer_role = Mock()
    officer_role.id = 202
    officer_role.name = "Officer Role"

    allowed_role = Mock()
    allowed_role.id = 301
    allowed_role.name = "Allowed Role"

    other_role = Mock()
    other_role.id = 999
    other_role.name = "Other Role"

    mock_interaction.user.roles = [admin_role, officer_role, allowed_role, other_role]
    mock_interaction.user.display_name = "TestUser"

    # Call the command's wrapper
    await perms(mock_interaction)

    # Assert that send_response was called once
    mock_send_response.assert_called_once()

    # Get the embed from the call
    call_args = mock_send_response.call_args
    embed = call_args.kwargs['embed']

    # Check "Configured Role IDs" field for correct formatting
    configured_field = embed.fields[1]
    assert "Configured Role IDs" in configured_field.name
    assert "<@&101>, <@&102>" in configured_field.value
    assert "<@&201>, <@&202>" in configured_field.value
    assert "<@&301>, <@&302>" in configured_field.value

    # Check "Matches" field for correct formatting
    matches_field = embed.fields[3]
    assert "Matches" in matches_field.name
    assert "admin roles: <@&101>" in matches_field.value
    assert "officer roles: <@&202>" in matches_field.value
    assert "allowed roles: <@&301>" in matches_field.value