import discord
from datetime import datetime

class EmbedBuilder:
    """Utility class for building Discord embeds more concisely"""
    
    def __init__(self, title, color=0xF39C12, timestamp=None, description=None):
        self.embed = discord.Embed(
            title=title, 
            color=color, 
            timestamp=timestamp or datetime.now(),
            description=description
        )
    
    def add_field(self, name, value, inline=True):
        """Add a field to the embed"""
        self.embed.add_field(name=name, value=value, inline=inline)
        return self
    
    def set_footer(self, text, icon_url=None):
        """Set the footer of the embed"""
        self.embed.set_footer(text=text, icon_url=icon_url)
        return self
    
    def set_description(self, description):
        """Set the description of the embed"""
        self.embed.description = description
        return self
    
    def set_thumbnail(self, url):
        """Set the thumbnail of the embed"""
        self.embed.set_thumbnail(url=url)
        return self
    
    def build(self):
        """Return the built embed"""
        return self.embed
    
    def __str__(self):
        return f"EmbedBuilder(title='{self.embed.title}')"
