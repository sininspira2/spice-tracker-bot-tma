import unittest
from commands import discover_commands


class TestCommandDiscovery(unittest.TestCase):
    def test_discover_class_based_command_groups(self):
        # When
        commands, _, _, command_groups = discover_commands()

        # Then
        self.assertIn("guild", command_groups)
        self.assertIn("settings", command_groups)
        self.assertNotIn("guild", commands)
        self.assertNotIn("settings", commands)
