import discord
from discord.ext import commands
import logging

log = logging.getLogger("cog-lilac")

# --- Constants ---
SNORLAX_ROLE_ID = 1447310242911359109
SNORLAX_PRICE = 50
AUCTION_TICKET_PRICE = 10
CARD_EX_MINAH_PRICE = 20
CARD_UR_RUMAN_PRICE = 35
PING_USER_ID = 723441401211256842  # Mentioned on card purchase


class LilacShop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Redis helpers ---
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

    # --- Command: /lilacshop (simplified UX: category dropdown -> item dropdown -> Redeem button) ---
    @commands.hybrid_command(name="lilacshop", description="Open the simplified Lilac shop")
    async def lilacshop(self, ctx: commands.Context):
        petals = await self.get_balance(ctx.author.id)
        tickets = await self.get_tickets(ctx.author.id)

        embed = discord.Embed(
            title="🌸 Lilac Shop",
            description="Select a category from the dropdown below.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🌸 Petals", value=f"`{petals}`", inline=True)
        embed.add_field(name="🎟️ Auction Tickets", value=f"`{tickets}`", inline=True)
        embed.set_footer(text="Choose a category to continue ✨")

        # Category dropdown
        categories = [
            discord.SelectOption(label="Discord Role", description="Special server roles", emoji="🌸"),
            discord.SelectOption(label="Auction Ticket", description="Bid in auctions", emoji="🎟️"),
            discord.SelectOption(label="Cards", description="Collectible cards", emoji="🃏"),
        ]
        select_category = discord.ui.Select(placeholder="Choose a category", min_values=1, max_values=1, options=categories)

        async def category_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Not your shop.", ephemeral=True)
                return

            chosen = select_category.values[0]

            # Items per category
            if chosen == "Discord Role":
                item_options = [
                    discord.SelectOption(label="Snorlax", description=f"{SNORLAX_PRICE} petals", emoji="🌸"),
                ]
            elif chosen == "Auction Ticket":
                item_options = [
                    discord.SelectOption(label="Auction Ticket", description=f"{AUCTION_TICKET_PRICE} petals", emoji="🎟️"),
                ]
            else:  # Cards
                item_options = [
                    discord.SelectOption(label="EX Minah vCM", description=f"{CARD_EX_MINAH_PRICE} petals", emoji="✨"),
                    discord.SelectOption(label="UR Ruman AFK vCM", description=f"{CARD_UR_RUMAN_PRICE} petals", emoji="💎"),
                ]

            select_item = discord.ui.Select(placeholder=f"Choose an item from {chosen}", min_values=1, max_values=1, options=item_options)

            async def item_callback(interaction2: discord.Interaction):
                if interaction2.user != ctx.author:
                    await interaction2.response.send_message("❌ Not your shop.", ephemeral=True)
                    return

                chosen_item = select_item.values[0]

                # Redeem button
                redeem_btn = discord.ui.Button(label="Redeem", style=discord.ButtonStyle.success, emoji="✅")

                async def redeem_callback(interaction3: discord.Interaction):
                    if interaction3.user != ctx.author:
                        await interaction3.response.send_message("❌ Not your shop.", ephemeral=True)
                        return

                    petals_local = await self.get_balance(interaction3.user.id)

                    # Purchase logic
                    if chosen_item == "Snorlax":
                        price = SNORLAX_PRICE
                        role = ctx.guild.get_role(SNORLAX_ROLE_ID)
                        if role is None:
                            await interaction3.response.send_message("❌ Role not found. Contact an admin.", ephemeral=True)
                            return
                        if role in interaction3.user.roles:
                            await interaction3.response.send_message("❌ You already own Snorlax.", ephemeral=True)
                            return
                        if petals_local < price:
                            await interaction3.response.send_message(f"❌ Not enough petals. Need {price}, you have {petals_local}.", ephemeral=True)
                            return
                        await self.add_balance(interaction3.user.id, -price)
                        await interaction3.user.add_roles(role, reason="LilacShop purchase: Snorlax")
                        await interaction3.response.send_message(f"✅ Redeemed **Snorlax** for {price} petals!", ephemeral=True)

                    elif chosen_item == "Auction Ticket":
                        price = AUCTION_TICKET_PRICE
                        if petals_local < price:
                            await interaction3.response.send_message(f"❌ Not enough petals. Need {price}, you have {petals_local}.", ephemeral=True)
                            return
                        await self.add_balance(interaction3.user.id, -price)
                        await self.add_tickets(interaction3.user.id, 1)
                        await interaction3.response.send_message(f"✅ Redeemed **Auction Ticket** for {price} petals!", ephemeral=True)

                    elif chosen_item == "EX Minah vCM":
                        price = CARD_EX_MINAH_PRICE
                        if petals_local < price:
                            await interaction3.response.send_message(f"❌ Not enough petals. Need {price}, you have {petals_local}.", ephemeral=True)
                            return
                        await self.add_balance(interaction3.user.id, -price)
                        await interaction3.response.send_message(f"✅ Redeemed **EX Minah vCM** for {price} petals!", ephemeral=True)
                        # Public announcement in English + ping target user
                        await ctx.channel.send(
                            f"🃏 {interaction3.user.mention} has just purchased **EX Minah vCM** for {price} petals! <@{PING_USER_ID}>"
                        )

                    elif chosen_item == "UR Ruman AFK vCM":
                        price = CARD_UR_RUMAN_PRICE
                        if petals_local < price:
                            await interaction3.response.send_message(f"❌ Not enough petals. Need {price}, you have {petals_local}.", ephemeral=True)
                            return
                        await self.add_balance(interaction3.user.id, -price)
                        await interaction3.response.send_message(f"✅ Redeemed **UR Ruman AFK vCM** for {price} petals!", ephemeral=True)
                        # Public announcement in English + ping target user
                        await ctx.channel.send(
                            f"🃏 {interaction3.user.mention} has just purchased **UR Ruman AFK vCM** for {price} petals! <@{PING_USER_ID}>"
                        )

                redeem_btn.callback = redeem_callback
                view_redeem = discord.ui.View()
                view_redeem.add_item(redeem_btn)

                await interaction2.response.send_message(
                    f"You selected **{chosen_item}**. Click Redeem to confirm.",
                    view=view_redeem,
                    ephemeral=True
                )

            select_item.callback = item_callback
            view_items = discord.ui.View()
            view_items.add_item(select_item)

            await interaction.response.send_message(
                f"Category **{chosen}** selected. Now choose an item:",
                view=view_items,
                ephemeral=True
            )

        select_category.callback = category_callback
        view = discord.ui.View()
        view.add_item(select_category)

        await ctx.send(embed=embed, view=view)

    # --- Command: /balance (thumbnail avatar, minimal fields) ---
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
        embed.set_footer(text="Use /lilacshop to open the shop")

        await ctx.send(embed=embed)

    # --- Admin: /payout (distribute petals to all members with a role) ---
    @commands.hybrid_command(name="payout", description="Admin: distribute petals to all members with a role")
    @commands.has_permissions(administrator=True)
    async def payout(self, ctx: commands.Context, role: discord.Role, amount: int):
        count = 0
        for member in role.members:
            await self.add_balance(member.id, amount)
            count += 1
        embed = discord.Embed(
            title="🌸 Payout Successful",
            description=f"Gave **{amount} petals** to **{count} members** with role `{role.name}`.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LilacShop(bot))
    log.info("⚙️ LilacShop cog loaded")
