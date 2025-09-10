import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from commands.ledger import ledger, PAGE_SIZE
from database import Database

@pytest.fixture
def mock_interaction():
    interaction = MagicMock()
    interaction.user.id = "12345"
    interaction.user.display_name = "TestUser"
    interaction.created_at = datetime.now()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.fixture
def mock_db():
    db = MagicMock(spec=Database)
    db.get_user.return_value = {
        "user_id": "12345",
        "username": "TestUser",
        "total_melange": 1000,
        "paid_melange": 500
    }

    deposits = []
    for i in range(25):
        deposits.append({
            "id": i,
            "user_id": "12345",
            "username": "TestUser",
            "sand_amount": 1000,
            "type": "solo" if i % 2 == 0 else "expedition",
            "expedition_id": i if i % 2 != 0 else None,
            "created_at": datetime.now()
        })

    async def mock_get_deposits_paginated(user_id, page, page_size):
        sand_per_melange_str = await db.get_setting('sand_per_melange')
        try:
            sand_per_melange = int(sand_per_melange_str)
        except (ValueError, TypeError):
            sand_per_melange = 50

        paginated_deposits = deposits[(page - 1) * page_size : page * page_size]
        for deposit in paginated_deposits:
            deposit["melange_amount"] = deposit["sand_amount"] // sand_per_melange
        return paginated_deposits

    db.get_user_deposits_paginated.side_effect = mock_get_deposits_paginated
    db.get_user_deposits_count.return_value = len(deposits)

    # Make get_setting an async mock
    async def get_setting_side_effect(key):
        if key == 'sand_per_melange':
            return "100"
        return None

    db.get_setting = AsyncMock(side_effect=get_setting_side_effect)

    return db

@pytest.mark.asyncio
@patch('commands.ledger.get_database')
async def test_ledger_first_page(mock_get_database, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    await ledger(mock_interaction)

    mock_interaction.followup.send.assert_called_once()
    kwargs = mock_interaction.followup.send.call_args.kwargs

    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert "Page 1 of 3" in embed.footer.text
    assert len(embed.description.strip().split('\n')) == PAGE_SIZE

    assert "view" in kwargs
    view = kwargs["view"]
    assert view.previous_button.disabled
    assert not view.next_button.disabled

@pytest.mark.asyncio
@patch('commands.ledger.get_database')
async def test_ledger_pagination(mock_get_database, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    await ledger(mock_interaction)

    view = mock_interaction.followup.send.call_args.kwargs["view"]

    # Simulate clicking "Next"
    await view.next_button.callback(mock_interaction)

    # Check that the embed was updated to page 2
    kwargs = mock_interaction.response.edit_message.call_args.kwargs
    embed = kwargs["embed"]
    assert "Page 2 of 3" in embed.footer.text

    # Simulate clicking "Previous"
    await view.previous_button.callback(mock_interaction)

    # Check that the embed was updated back to page 1
    kwargs = mock_interaction.response.edit_message.call_args.kwargs
    embed = kwargs["embed"]
    assert "Page 1 of 3" in embed.footer.text

@pytest.mark.asyncio
@patch('commands.ledger.get_database')
async def test_ledger_melange_display(mock_get_database, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    # sand_per_melange is 100 from the fixture
    # 1000 sand / 100 = 10 melange
    await ledger(mock_interaction)

    kwargs = mock_interaction.followup.send.call_args.kwargs
    embed = kwargs["embed"]

    assert "(10 melange)" in embed.description
    assert "**1,000** total | **500** paid | **500** pending" in embed.fields[0].value

@pytest.mark.asyncio
@patch('commands.ledger.get_database')
async def test_ledger_invalid_sand_per_melange(mock_get_database, mock_interaction, mock_db):
    mock_get_database.return_value = mock_db

    # Set the setting to an invalid value
    async def invalid_get_setting(key):
        if key == 'sand_per_melange':
            return "abc"
        return None
    mock_db.get_setting.side_effect = invalid_get_setting

    await ledger(mock_interaction)

    kwargs = mock_interaction.followup.send.call_args.kwargs
    embed = kwargs["embed"]

    # 1000 sand / 50 default rate = 20 melange
    assert "(20 melange)" in embed.description
