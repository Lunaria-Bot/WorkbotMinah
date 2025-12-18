import discord
from discord.ext import commands
import logging
import os

log = logging.getLogger("cog-lilac")

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

    # --- Slash command: /lilac ---
    @commands.hybrid_command(name="lilac", description="Open the Lilac shop")
    async def lilac(self, ctx: commands.Context):
        petals = await self.get_balance(ctx.author.id)
        tickets = await self.get_tickets(ctx.author.id)

        embed = discord.Embed(
            title="🌸 Lilac Boutique",
            description="Choose a category below to browse items.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🌸 Petals", value=f"`{petals}`", inline=True)
        embed.add_field(name="🎟️ Auction Tickets", value=f"`{tickets}`", inline=True)
        embed.set_footer(text="Select a category to continue ✨")

        view = discord.ui.View()

        # --- Bouton Discord Role ---
        async def show_roles(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ This shop is only for the command user.", ephemeral=True)
                return

            role = ctx.guild.get_role(SNORLAX_ROLE_ID)
            embed_role = discord.Embed(
                title="🌸 Lilac Shop - Discord Roles",
                description="Select a role to purchase:",
                color=discord.Color.green()
            )
            if role in ctx.author.roles:
                embed_role.add_field(name="Snorlax", value="Already bought ✅", inline=False)
            else:
                embed_role.add_field(name="Snorlax", value=f"{SNORLAX_PRICE} petals", inline=False)

            options = [
                discord.SelectOption(label="Snorlax", description=f"{SNORLAX_PRICE} petals", emoji="🌸")
            ]
            select = discord.ui.Select(placeholder="Choose a role to buy", options=options)

            async def select_callback(interaction2: discord.Interaction):
                if interaction2.user != ctx.author:
                    await interaction2.response.send_message("❌ Not your shop.", ephemeral=True)
                    return
                petals = await self.get_balance(interaction2.user.id)
                if role in interaction2.user.roles:
                    embed_confirm = discord.Embed(
                        title="❌ Purchase Failed",
                        description="You already own Snorlax.",
                        color=discord.Color.red()
                    )
                    await interaction2.response.send_message(embed=embed_confirm, ephemeral=True)
                    return
                if petals < SNORLAX_PRICE:
                    embed_confirm = discord.Embed(
                        title="❌ Purchase Failed",
                        description=f"Not enough petals. Need {SNORLAX_PRICE}, you have {petals}.",
                        color=discord.Color.red()
                    )
                    await interaction2.response.send_message(embed=embed_confirm, ephemeral=True)
                    return
                await self.add_balance(interaction2.user.id, -SNORLAX_PRICE)
                await interaction2.user.add_roles(role)
                embed_confirm = discord.Embed(
                    title="✅ Purchase Successful",
                    description=f"You bought **Snorlax** for {SNORLAX_PRICE} petals! Role assigned.",
                    color=discord.Color.green()
                )
                await interaction2.response.send_message(embed=embed_confirm, ephemeral=True)

            select.callback = select_callback
            view_role = discord.ui.View()
            view_role.add_item(select)

            await interaction.response.send_message(embed=embed_role, view=view_role, ephemeral=True)

        btn_role = discord.ui.Button(label="Discord Role", style=discord.ButtonStyle.primary, emoji="🌸")
        btn_role.callback = show_roles
        view.add_item(btn_role)

        # --- Bouton Auction Ticket ---
        async def show_tickets(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ This shop is only for the command user.", ephemeral=True)
                return

            embed_ticket = discord.Embed(
                title="🎟️ Lilac Shop - Auction Tickets",
                description="Select a ticket to purchase:",
                color=discord.Color.blue()
            )
            embed_ticket.add_field(name="Auction Ticket", value=f"{AUCTION_TICKET_PRICE} petals", inline=False)

            options = [
                discord.SelectOption(label="Auction Ticket", description=f"{AUCTION_TICKET_PRICE} petals", emoji="🎟️")
            ]
            select = discord.ui.Select(placeholder="Choose a ticket to buy", options=options)

            async def select_callback(interaction2: discord.Interaction):
                if interaction2.user != ctx.author:
                    await interaction2.response.send_message("❌ Not your shop.", ephemeral=True)
                    return
                petals = await self.get_balance(interaction2.user.id)
                if petals < AUCTION_TICKET_PRICE:
                    embed_confirm = discord.Embed(
                        title="❌ Purchase Failed",
                        description=f"Not enough petals. Need {AUCTION_TICKET_PRICE}, you have {petals}.",
                        color=discord.Color.red()
                    )
                    await interaction2.response.send_message(embed=embed_confirm, ephemeral=True)
                    return
                await self.add_balance(interaction2.user.id, -AUCTION_TICKET_PRICE)
                await self.add_tickets(interaction2.user.id, 1)
                embed_confirm = discord.Embed(
                    title="✅ Purchase Successful",
                    description=f"You bought **Auction Ticket** for {AUCTION_TICKET_PRICE} petals! 🎟️",
                    color=discord.Color.green()
                )
                await interaction2.response.send_message(embed=embed_confirm, ephemeral=True)

            select.callback = select_callback
            view_ticket = discord.ui.View()
            view_ticket.add_item(select)

            await interaction.response.send_message(embed=embed_ticket, view=view_ticket, ephemeral=True)

        btn_ticket = discord.ui.Button(label="Auction Ticket", style=discord.ButtonStyle.secondary, emoji="🎟️")
        btn_ticket.callback = show_tickets
        view.add_item(btn_ticket)

        await ctx.send(embed=embed, view=view)

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


async def setup(bot: commands.Bot):
    await bot.add_cog(LilacShop(bot))
    log.info("⚙️ LilacShop cog loaded")
