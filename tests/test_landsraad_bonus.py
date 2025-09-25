"""
Tests for landsraad bonus functionality using real database.
"""

import pytest
from unittest.mock import AsyncMock, patch
from utils.helpers import convert_sand_to_melange, get_sand_per_melange_with_bonus, initialize_global_settings, is_landsraad_bonus_active, update_landsraad_bonus_status
from database_orm import Database

@pytest.fixture(autouse=True)
async def run_before_tests():
    """Ensure the bonus status is initialized before each test in this module."""
    await initialize_global_settings()

class TestLandsraadBonus:
    """Test landsraad bonus conversion functionality."""

    @pytest.mark.asyncio
    async def test_convert_sand_to_melange_normal_rate(self):
        """Test sand to melange conversion with normal rate (50:1)."""
        with patch('utils.helpers.get_sand_per_melange_with_bonus', return_value=50.0):
            melange, remaining = await convert_sand_to_melange(250)
            assert melange == 5
            assert remaining == 0

    @pytest.mark.asyncio
    async def test_convert_sand_to_melange_landsraad_rate(self):
        """Test sand to melange conversion with landsraad bonus rate (37.5:1)."""
        with patch('utils.helpers.get_sand_per_melange_with_bonus', return_value=37.5):
            melange, remaining = await convert_sand_to_melange(250)
            assert melange == 6
            assert remaining == 25

    @pytest.mark.asyncio
    async def test_get_sand_per_melange_with_bonus_active(self):
        """Test getting conversion rate when landsraad bonus is active."""
        with patch('utils.helpers.is_landsraad_bonus_active', return_value=True):
            rate = await get_sand_per_melange_with_bonus()
            assert rate == 37.5

    @pytest.mark.asyncio
    async def test_get_sand_per_melange_with_bonus_inactive(self):
        """Test getting conversion rate when landsraad bonus is inactive."""
        with patch('utils.helpers.is_landsraad_bonus_active', return_value=False):
            rate = await get_sand_per_melange_with_bonus()
            assert rate == 50.0

    @pytest.mark.asyncio
    async def test_initialize_bonus_status_error_fallback(self):
        """Test fallback to False when database error occurs during initialization."""
        with patch('utils.helpers.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.get_global_setting.side_effect = Exception("Database error")
            mock_get_db.return_value = mock_db

            await initialize_global_settings()
            assert is_landsraad_bonus_active() is False

    @pytest.mark.asyncio
    async def test_initialize_bonus_status_none_result(self):
        """Test handling when database returns None during initialization."""
        with patch('utils.helpers.get_database') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.get_global_setting.return_value = None
            mock_get_db.return_value = mock_db

            await initialize_global_settings()
            assert is_landsraad_bonus_active() is False

class TestDatabaseLandsraadBonus:
    """Test database methods for landsraad bonus management with real database."""

    @pytest.mark.asyncio
    async def test_landsraad_bonus_conversion_rates_with_cache(self, test_database):
        """Test that landsraad bonus affects conversion rates correctly with caching."""
        await test_database.set_global_setting('landsraad_bonus_active', 'true')
        update_landsraad_bonus_status(True)

        rate = await get_sand_per_melange_with_bonus()
        assert rate == 37.5

        await test_database.set_global_setting('landsraad_bonus_active', 'false')
        update_landsraad_bonus_status(False)

        rate = await get_sand_per_melange_with_bonus()
        assert rate == 50.0