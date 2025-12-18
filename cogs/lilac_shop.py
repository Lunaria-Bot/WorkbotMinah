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

    # --- Slash command: /lilac (shop interface) ---
    @commands.hybrid_command(name="lilac", description="Open the Lilac shop")
    async def lilac(self, ctx: commands.Context):
        petals = await self.get_balance(ctx.author.id)
        tickets = await self.get_tickets(ctx.author.id)

        embed = discord.Embed(
            title="🌸 Lilac General Shop",
            description="Welcome to the enchanted Lilac shop! Choose a category below to browse items.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Petals", value=f"{petals} 🌸", inline=True)
        embed.add_field(name="Auction Tickets", value=f"{tickets} 🎟️", inline=True)
        embed.set_footer(text="Use /buy <item> <amount> to purchase")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Discord Role", style=discord.ButtonStyle.primary, custom_id="shop_role"))
        view.add_item(discord.ui.Button(label="Auction Ticket", style=discord.ButtonStyle.primary, custom_id="shop_ticket"))

        async def interaction_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ You can't use this shop interface.", ephemeral=True)
                return

            category = "role" if interaction.data["custom_id"] == "shop_role" else "ticket"
            items = await self.list_items(category)
            if not items:
                await interaction.response.send_message(f"❌ No items found in category `{category}`", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"Lilac Shop - {category.capitalize()}",
                description=f"Items available in the `{category}` category:",
                color=discord.Color.purple()
            )
            for name, price in items.items():
                embed.add_field(name=name, value=f"{price} petals", inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        view.children[0].callback = interaction_callback
        view.children[1].callback = interaction_callback

        await ctx.send(embed=embed, view=view)

    # --- Slash command: /balance (stylisé avec avatar en grand) ---
    @commands.hybrid_command(name="balance", description="Check your Lilac wallet")
    async def balance(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        petals = await self.get_balance(member.id)
        tickets = await self.get_tickets(member.id)

        embed = discord.Embed(
            title=f"Minah : Wallet of {member.display_name}",
            description="Your enchanted currency pouch ✨",
            color=discord.Color.purple()
        )
        embed.set_image(url=member.display_avatar.url)
        embed.add_field(name="🌸 Petals", value=f"`{petals}`", inline=True)
        embed.add_field(name="🎟️ Auction Tickets", value=f"`{tickets}`", inline=True)
        embed.set_footer(text="Use /lilac to open the shop")

        await ctx.send(embed=embed)

    # --- Admin: payout petals ---
    @commands.hybrid_command(name="payout", description="Auto payout petals to members with a role")
    @commands.has_permissions(administrator=True)
    async def payout(self, ctx: commands.Context, role: discord.Role, amount: int):
        count = 0
        for member in role.members:
            await self.add_balance(member.id, amount)
            count += 1
        await ctx.send(f"✅ Gave {amount} petals to {count} members with role {role.name}")

    # --- Admin: give auction tickets ---
    @commands.hybrid_command(name="give_ticket", description="Admin: give auction tickets to members with a role")
    @commands.has_permissions(administrator=True)
    async def give_ticket(self, ctx: commands.Context, role: discord.Role, amount: int):
        count = 0
        for member in role.members:
            await self.add_tickets(member.id, amount)
            count += 1
        await ctx.send(f"🎟️ Gave {amount} Auction Tickets to {count} members with role {role.name}")

    # --- Admin: add/remove items ---
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
