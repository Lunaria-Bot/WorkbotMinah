import discord
from discord.ext import commands
import logging
import os

log = logging.getLogger("cog-lilac")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))

class LilacShop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Helpers Redis ---
    async def get_balance(self, user_id: int) -> int:
        if not getattr(self.bot, "redis", None):
            return 0
        val = await self.bot.redis.get(f"petals:{user_id}")
        return int(val or 0)

    async def add_balance(self, user_id: int, amount: int):
        if not getattr(self.bot, "redis", None):
            return
        current = await self.get_balance(user_id)
        await self.bot.redis.set(f"petals:{user_id}", current + amount)

    async def get_tickets(self, user_id: int) -> int:
        if not getattr(self.bot, "redis", None):
            return 0
        val = await self.bot.redis.get(f"tickets:{user_id}")
        return int(val or 0)

    async def add_tickets(self, user_id: int, amount: int):
        if not getattr(self.bot, "redis", None):
            return
        current = await self.get_tickets(user_id)
        await self.bot.redis.set(f"tickets:{user_id}", current + amount)

    async def add_item(self, category: str, name: str, price: int):
        if not getattr(self.bot, "redis", None):
            return
        key = f"shop:{category}"
        await self.bot.redis.hset(key, name, price)

    async def remove_item(self, category: str, name: str):
        if not getattr(self.bot, "redis", None):
            return
        key = f"shop:{category}"
        await self.bot.redis.hdel(key, name)

    async def list_items(self, category: str):
        if not getattr(self.bot, "redis", None):
            return {}
        key = f"shop:{category}"
        return await self.bot.redis.hgetall(key)

    # --- Slash commands ---
    @commands.hybrid_command(name="lilac", description="Open the Lilac shop")
    async def lilac(self, ctx: commands.Context, category: str = None):
        """Open shop and show items by category"""
        if not category:
            await ctx.send("🌸 Available categories: potions, weapons, decorations")
            return

        items = await self.list_items(category)
        if not items:
            await ctx.send(f"❌ No items found in category `{category}`")
            return

        embed = discord.Embed(title=f"Lilac Shop - {category}", color=discord.Color.purple())
        for name, price in items.items():
            embed.add_field(name=name, value=f"{price} petals", inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="balance", description="Check your Lilac balance")
    async def balance(self, ctx: commands.Context, member: discord.Member = None):
        """Show petals and auction tickets with avatar"""
        member = member or ctx.author
        petals = await self.get_balance(member.id)
        tickets = await self.get_tickets(member.id)

        embed = discord.Embed(
            title=f"{member.display_name}'s Balance 🌸",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Petals", value=str(petals), inline=True)
        embed.add_field(name="Auction Tickets", value=str(tickets), inline=True)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="payout", description="Auto payout petals to members with a role")
    @commands.has_permissions(administrator=True)
    async def payout(self, ctx: commands.Context, role: discord.Role, amount: int):
        """Give petals to all members with a specific role"""
        count = 0
        for member in role.members:
            await self.add_balance(member.id, amount)
            count += 1
        await ctx.send(f"✅ Gave {amount} petals to {count} members with role {role.name}")

    @commands.hybrid_command(name="give_ticket", description="Admin: give auction tickets to members with a role")
    @commands.has_permissions(administrator=True)
    async def give_ticket(self, ctx: commands.Context, role: discord.Role, amount: int):
        """Give auction tickets to all members with a specific role"""
        count = 0
        for member in role.members:
            await self.add_tickets(member.id, amount)
            count += 1
        await ctx.send(f"🎟️ Gave {amount} Auction Tickets to {count} members with role {role.name}")

    @commands.hybrid_command(name="add_item", description="Admin: add item to shop")
    @commands.has_permissions(administrator=True)
    async def add_item_cmd(self, ctx: commands.Context, category: str, name: str, price: int):
        await self.add_item(category, name, price)
        await ctx.send(f"✅ Added `{name}` ({price} petals) to category `{category}`")

    @commands.hybrid_command(name="remove_item", description="Admin: remove item from shop")
    @commands.has_permissions(administrator=True)
    async def remove_item_cmd(self, ctx: commands.Context, category: str, name: str):
        await self.remove_item(category, name)
        await ctx.send(f"✅ Removed `{name}` from category `{category}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(LilacShop(bot))
    log.info("⚙️ LilacShop cog loaded")
