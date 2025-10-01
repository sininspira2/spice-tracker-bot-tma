"""
Tests for the refactored ledger command.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime

from commands.ledger import ledger, format_deposit_item, build_ledger_embed
from utils.pagination_utils import PaginatedView

@pytest.fixture
def mock_db():
    """Provides a mock database object."""
    db = AsyncMock()
    db.get_user.return_value = {
        'user_id': '123', 'username': 'TestUser', 'total_melange': 100, 'paid_melange': 50
    }
    return db

class TestLedgerCommandRefactored:
    """Test the refactored ledger command."""

    @pytest.mark.asyncio
    async def test_ledger_no_deposits(self, mock_interaction, mock_db):
        """Test ledger command for a user with no deposits."""
        mock_interaction.created_at = datetime.now()
        mock_db.get_user_deposits_count.return_value = 0

        with patch('commands.ledger.get_database', return_value=mock_db):
            await ledger(mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        sent_embed = mock_interaction.followup.send.call_args[1]['embed']
        assert "You haven't made any melange yet!" in sent_embed.description

    @pytest.mark.asyncio
    async def test_ledger_with_deposits_sends_paginated_view(self, mock_interaction, mock_db):
        """Test that the ledger command sends a PaginatedView when there are deposits."""
        mock_interaction.created_at = datetime.now()
        mock_db.get_user_deposits_count.return_value = 15
        mock_db.get_user_deposits.return_value = [
            {'sand_amount': 100, 'created_at': datetime.now(), 'type': 'solo', 'melange_amount': 2}
        ]

        with patch('commands.ledger.get_database', return_value=mock_db), \
             patch('commands.ledger.PaginatedView', autospec=True) as MockPaginatedView:
            # Configure the mock instance that PaginatedView() will return
            mock_view_instance = MockPaginatedView.return_value
            mock_view_instance.total_pages = 2  # Based on 15 items / 10 per page

            await ledger(mock_interaction)

        mock_interaction.followup.send.assert_called_once()
        # Ensure PaginatedView was instantiated correctly
        MockPaginatedView.assert_called_once_with(
            interaction=mock_interaction,
            total_items=15,
            fetch_data_func=ANY,  # Using ANY because the partial is hard to match
            format_embed_func=build_ledger_embed,
            extra_embed_data={"user": await mock_db.get_user()}
        )
        # Ensure the view instance was passed to send
        assert mock_interaction.followup.send.call_args[1]['view'] is mock_view_instance

    def test_format_deposit_item(self):
        """Test the formatting of a single deposit item."""
        deposit = {
            'created_at': datetime.now(),
            'sand_amount': 500,
            'melange_amount': 10,
            'type': 'expedition'
        }
        formatted_str = format_deposit_item(deposit)
        assert "**500 sand**" in formatted_str
        assert "**10 melange**" in formatted_str
        assert "🚀 Expedition" in formatted_str

    def test_format_guild_deposit_item(self):
        """Test the formatting of a guild deposit item."""
        deposit = {
            'created_at': datetime.now(),
            'sand_amount': 0,
            'melange_amount': 50,
            'type': 'Guild'
        }
        formatted_str = format_deposit_item(deposit)
        assert "sand" not in formatted_str
        assert "**50 melange**" in formatted_str
        assert "🏛️ Guild" in formatted_str

    @pytest.mark.asyncio
    async def test_build_ledger_embed(self, mock_interaction):
        """Test the ledger embed builder."""
        user_data = {'total_melange': 1000, 'paid_melange': 300}
        deposits = [{'sand_amount': 100, 'created_at': datetime.now(), 'type': 'solo', 'melange_amount': 2}]

        embed = await build_ledger_embed(
            interaction=mock_interaction,
            data=deposits,
            current_page=1,
            total_pages=1,
            extra_data={"user": user_data}
        )

        assert "📋 Conversion History" in embed.title
        # Check for pending melange calculation
        assert "700** pending" in embed.fields[0].value
        assert "Page 1/1" in embed.footer.text