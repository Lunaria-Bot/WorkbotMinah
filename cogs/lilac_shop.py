import discord
from discord.ext import commands
import logging
import os

log = logging.getLogger("cog-lilac")

GUILD_ID = int(os.getenv("GUILD_ID", "0"))

SNORLAX_ROLE_ID = 1447310242911359109
SNORLAX_PRICE = 50
AUCTION_TICKET_PRICE = 10

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

    # --- Slash command: /lilac (shop interface) ---
    @commands.hybrid_command(name="lilac", description="Open the Lilac shop")
    async def lilac(self, ctx: commands.Context):
        petals = await self.get_balance(ctx.author.id)
        tickets = await self.get_tickets(ctx.author.id)

        embed = discord.Embed(
            title="🌸 Lilac General Shop",
            description="Choose a category below to browse items.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="Petals", value=f"{petals} 🌸", inline=True)
        embed.add_field(name="Auction Tickets", value=f"{tickets} 🎟️", inline=True)

        # Catégorie Discord Role
        role = ctx.guild.get_role(SNORLAX_ROLE_ID)
        if role in ctx.author.roles:
            embed.add_field(name="Snorlax (Role)", value=f"Already bought ✅", inline=False)
        else:
            embed.add_field(name="Snorlax (Role)", value=f"{SNORLAX_PRICE} petals", inline=False)

        # Catégorie Auction Ticket
        embed.add_field(name="Auction Ticket", value=f"{AUCTION_TICKET_PRICE} petals", inline=False)

        embed.set_footer(text="Use /buy <item> to purchase")

        await ctx.send(embed=embed)

    # --- Slash command: /balance ---
    @commands.hybrid_command(name="balance", description="Check your Lilac wallet")
    async def balance(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        petals = await self.get_balance(member.id)
        tickets = await self.get_tickets(member.id)

        embed = discord.Embed(
            title=f"Minah : Wallet of {member.display_name}",
            description="Your enchanted inventory pouch ✨",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🌸 Petals", value=f"`{petals}`", inline=True)
        embed.add_field(name="🎟️ Auction Tickets", value=f"`{tickets}`", inline=True)
        embed.set_footer(text="Use /lilac to open the shop")

        await ctx.send(embed=embed)

    # --- Slash command: /buy ---
    @commands.hybrid_command(name="buy", description="Buy an item from the Lilac shop")
    async def buy(self, ctx: commands.Context, item: str):
        member = ctx.author
        petals = await self.get_balance(member.id)

        # --- Item: Snorlax Role ---
        if item.lower() == "snorlax":
            role = ctx.guild.get_role(SNORLAX_ROLE_ID)
            price = SNORLAX_PRICE

            if role in member.roles:
                await ctx.send("❌ You already own the Snorlax role (Already bought).")
                return

            if petals < price:
                await ctx.send(f"❌ Not enough petals. You need {price}, you have {petals}.")
                return

            await self.add_balance(member.id, -price)
            await member.add_roles(role)
            await ctx.send(f"✅ You bought **Snorlax** for {price} petals! Role assigned.")

        # --- Item: Auction Ticket ---
        elif item.lower() in ["auctionticket", "auction", "ticket"]:
            price = AUCTION_TICKET_PRICE
            if petals < price:
                await ctx.send(f"❌ Not enough petals. You need {price}, you have {petals}.")
                return

            await self.add_balance(member.id, -price)
            await self.add_tickets(member.id, 1)
            await ctx.send(f"✅ You bought **Auction Ticket** for {price} petals! 🎟️")

        else:
            await ctx.send("❌ Unknown item. Available: `Snorlax`, `Auction Ticket`")

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

    # --- Admin: add/remove items (optionnel si tu veux étendre le shop) ---
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
