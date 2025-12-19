import discord
from discord.ext import commands
import logging

log = logging.getLogger("cog-lilac")

SNORLAX_ROLE_ID = 1447310242911359109
SNORLAX_PRICE = 50
AUCTION_TICKET_PRICE = 10
SKIP_QUEUE_TICKET_PRICE = 25
CARD_EX_MINAH_PRICE = 20
CARD_UR_RUMAN_PRICE = 35
PING_USER_ID = 723441401211256842  # Ping on card purchase


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

    # --- Command: /lilacshop (dynamic embed with Back navigation) ---
    @commands.hybrid_command(name="lilacshop", description="Open the dynamic Lilac shop")
    async def lilacshop(self, ctx: commands.Context):
        petals = await self.get_balance(ctx.author.id)
        tickets = await self.get_tickets(ctx.author.id)

        base_embed = discord.Embed(
            title="🌸 Lilac Shop",
            description="Select a category from the dropdown below.",
            color=discord.Color.purple()
        )
        base_embed.set_thumbnail(url=ctx.author.display_avatar.url)
        base_embed.add_field(name="🌸 Petals", value=f"`{petals}`", inline=True)
        base_embed.add_field(name="🎟️ Auction Tickets", value=f"`{tickets}`", inline=True)
        base_embed.add_field(name="Categories", value="🌸 Discord Role\n🎟️ Auction Ticket\n🃏 Cards", inline=False)

        categories = [
            discord.SelectOption(label="Discord Role", description="Special server roles", emoji="🌸"),
            discord.SelectOption(label="Auction Ticket", description="Bid in auctions", emoji="🎟️"),
            discord.SelectOption(label="Cards", description="Collectible cards", emoji="🃏"),
        ]
        select_category = discord.ui.Select(placeholder="Choose a category", min_values=1, max_values=1, options=categories)

        async def category_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("❌ Not your shop.", ephemeral=True)
                return

            chosen = select_category.values[0]

            # Live wallet
            live_petals = await self.get_balance(ctx.author.id)
            live_tickets = await self.get_tickets(ctx.author.id)

            base_embed.clear_fields()
            base_embed.add_field(name="🌸 Petals", value=f"`{live_petals}`", inline=True)
            base_embed.add_field(name="🎟️ Auction Tickets", value=f"`{live_tickets}`", inline=True)

            # Category items + descriptions
            if chosen == "Discord Role":
                items_text = (
                    f"🌸 Snorlax — {SNORLAX_PRICE} petals\n"
                    f"*Special server role with cozy vibes.*"
                )
                item_options = [
                    discord.SelectOption(label="Snorlax", description=f"{SNORLAX_PRICE} petals", emoji="🌸"),
                ]
            elif chosen == "Auction Ticket":
                items_text = (
                    f"🎟️ Normal Queue Auction Ticket — {AUCTION_TICKET_PRICE} petals\n"
                    f"*Join the standard auction queue.*\n\n"
                    f"🚀 Skip Queue Auction Ticket — {SKIP_QUEUE_TICKET_PRICE} petals\n"
                    f"*Jump ahead in the auction queue for priority bidding.*"
                )
                item_options = [
                    discord.SelectOption(label="Normal Queue Auction Ticket", description=f"{AUCTION_TICKET_PRICE} petals", emoji="🎟️"),
                    discord.SelectOption(label="Skip Queue Auction Ticket", description=f"{SKIP_QUEUE_TICKET_PRICE} petals", emoji="🚀"),
                ]
            else:  # Cards
                items_text = (
                    f"✨ EX Minah vCM — {CARD_EX_MINAH_PRICE} petals\n"
                    f"*Exclusive collectible card.*\n\n"
                    f"💎 UR Ruman AFK vCM — {CARD_UR_RUMAN_PRICE} petals\n"
                    f"*Ultra rare collectible card.*"
                )
                item_options = [
                    discord.SelectOption(label="EX Minah vCM", description=f"{CARD_EX_MINAH_PRICE} petals", emoji="✨"),
                    discord.SelectOption(label="UR Ruman AFK vCM", description=f"{CARD_UR_RUMAN_PRICE} petals", emoji="💎"),
                ]

            base_embed.add_field(name="Items", value=items_text, inline=False)

            # Back to categories button
            back_to_categories = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, emoji="↩️")

            async def back_categories_callback(inter2: discord.Interaction):
                if inter2.user.id != ctx.author.id:
                    await inter2.response.send_message("❌ Not your shop.", ephemeral=True)
                    return

                # Refresh base view
                reset_embed = discord.Embed(
                    title="🌸 Lilac Shop",
                    description="Select a category from the dropdown below.",
                    color=discord.Color.purple()
                )
                reset_embed.set_thumbnail(url=ctx.author.display_avatar.url)
                reset_embed.add_field(name="🌸 Petals", value=f"`{await self.get_balance(ctx.author.id)}`", inline=True)
                reset_embed.add_field(name="🎟️ Auction Tickets", value=f"`{await self.get_tickets(ctx.author.id)}`", inline=True)
                reset_embed.add_field(name="Categories", value="🌸 Discord Role\n🎟️ Auction Ticket\n🃏 Cards", inline=False)

                base_view = discord.ui.View(timeout=180)
                select_category.callback = category_callback
                base_view.add_item(select_category)
                await inter2.response.edit_message(embed=reset_embed, view=base_view)

            # Items dropdown
            select_item = discord.ui.Select(placeholder="Choose an item", min_values=1, max_values=1, options=item_options)

            async def item_callback(interaction2: discord.Interaction):
                if interaction2.user.id != ctx.author.id:
                    await interaction2.response.send_message("❌ Not your shop.", ephemeral=True)
                    return

                chosen_item = select_item.values[0]

                # Keep an "items" state snapshot to go back to
                embed_items = discord.Embed(
                    title="🌸 Lilac Shop",
                    description=f"{chosen} — items",
                    color=discord.Color.purple()
                )
                embed_items.set_thumbnail(url=ctx.author.display_avatar.url)
                embed_items.add_field(name="🌸 Petals", value=f"`{await self.get_balance(ctx.author.id)}`", inline=True)
                embed_items.add_field(name="🎟️ Auction Tickets", value=f"`{await self.get_tickets(ctx.author.id)}`", inline=True)
                embed_items.add_field(name="Items", value=items_text, inline=False)

                view_items = discord.ui.View(timeout=180)
                select_item.callback = item_callback
                view_items.add_item(select_item)
                # Back button at items level
                back_to_categories.callback = back_categories_callback
                view_items.add_item(back_to_categories)

                # Now show selected item screen
                base_embed.clear_fields()
                base_embed.add_field(name="🌸 Petals", value=f"`{await self.get_balance(ctx.author.id)}`", inline=True)
                base_embed.add_field(name="🎟️ Auction Tickets", value=f"`{await self.get_tickets(ctx.author.id)}`", inline=True)
                base_embed.add_field(name="Selected item", value=f"✅ {chosen_item}", inline=False)

                redeem_btn = discord.ui.Button(label="Redeem", style=discord.ButtonStyle.success, emoji="✅")
                back_to_items = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary, emoji="↩️")

                async def redeem_callback(interaction3: discord.Interaction):
                    if interaction3.user.id != ctx.author.id:
                        await interaction3.response.send_message("❌ Not your shop.", ephemeral=True)
                        return

                    petals_local = await self.get_balance(interaction3.user.id)

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

                    elif chosen_item == "Normal Queue Auction Ticket":
                        price = AUCTION_TICKET_PRICE
                        if petals_local < price:
                            await interaction3.response.send_message(f"❌ Not enough petals. Need {price}, you have {petals_local}.", ephemeral=True)
                            return
                        await self.add_balance(interaction3.user.id, -price)
                        await self.add_tickets(interaction3.user.id, 1)
                        await interaction3.response.send_message(f"✅ Redeemed **Normal Queue Auction Ticket** for {price} petals!", ephemeral=True)

                    elif chosen_item == "Skip Queue Auction Ticket":
                        price = SKIP_QUEUE_TICKET_PRICE
                        if petals_local < price:
                            await interaction3.response.send_message(f"❌ Not enough petals. Need {price}, you have {petals_local}.", ephemeral=True)
                            return
                        await self.add_balance(interaction3.user.id, -price)
                        await self.add_tickets(interaction3.user.id, 1)
                        await interaction3.response.send_message(f"✅ Redeemed **Skip Queue Auction Ticket** for {price} petals!", ephemeral=True)

                    elif chosen_item == "EX Minah vCM":
                        price = CARD_EX_MINAH_PRICE
                        if petals_local < price:
                            await interaction3.response.send_message(f"❌ Not enough petals. Need {price}, you have {petals_local}.", ephemeral=True)
                            return
                        await self.add_balance(interaction3.user.id, -price)
                        await interaction3.response.send_message(f"✅ Redeemed **EX Minah vCM** for {price} petals!", ephemeral=True)
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
                        await ctx.channel.send(
                            f"🃏 {interaction3.user.mention} has just purchased **UR Ruman AFK vCM** for {price} petals! <@{PING_USER_ID}>"
                        )

                    # Refresh embed status after purchase
                    refreshed_petals = await self.get_balance(ctx.author.id)
                    refreshed_tickets = await self.get_tickets(ctx.author.id)
                    status_embed = discord.Embed(
                        title="🌸 Lilac Shop",
                        description="Purchase complete ✅",
                        color=discord.Color.green()
                    )
                    status_embed.set_thumbnail(url=ctx.author.display_avatar.url)
                    status_embed.add_field(name="🌸 Petals", value=f"`{refreshed_petals}`", inline=True)
                    status_embed.add_field(name="🎟️ Auction Tickets", value=f"`{refreshed_tickets}`", inline=True)
                    status_embed.add_field(name="Tip", value="Use Back to continue shopping.", inline=False)
                    # Keep Back to items available after purchase
                    post_view = discord.ui.View(timeout=180)
                    back_to_items.callback = back_items_callback
                    post_view.add_item(back_to_items)
                    await interaction3.message.edit(embed=status_embed, view=post_view)

                async def back_items_callback(interaction3: discord.Interaction):
                    if interaction3.user.id != ctx.author.id:
                        await interaction3.response.send_message("❌ Not your shop.", ephemeral=True)
                        return
                    # Return to the items list view for current category
                    await interaction3.response.edit_message(embed=embed_items, view=view_items)

                redeem_btn.callback = redeem_callback
                back_to_items.callback = back_items_callback

                selected_view = discord.ui.View(timeout=180)
                selected_view.add_item(redeem_btn)
                selected_view.add_item(back_to_items)

                await interaction2.response.edit_message(embed=base_embed, view=selected_view)

            select_item.callback = item_callback

            # View for items + Back to categories
            items_view = discord.ui.View(timeout=180)
            items_view.add_item(select_item)
            back_to_categories.callback = back_categories_callback
            items_view.add_item(back_to_categories)

            await interaction.response.edit_message(embed=base_embed, view=items_view)

        select_category.callback = category_callback
        base_view = discord.ui.View(timeout=180)
        base_view.add_item(select_category)
        await ctx.send(embed=base_embed, view=base_view)

    # --- Command: /balance ---
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

    # --- Admin: /payout ---
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
