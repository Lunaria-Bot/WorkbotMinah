import discord
from discord.ext import commands
import logging

log = logging.getLogger("cog-petal-rewards")

ROLE_PETAL_REWARDS = {
    1297161398274625660: 2,
    1297161587744047106: 4,
    1297161626910462016: 6,
    1297161678823227464: 8,
    1297174883213639691: 10,
    1297161785954275448: 12,
}

MONTHLY_ROLES = [1296505433674088451, 1295761591895064577]
MONTHLY_PETALS = 2
MONTHLY_SKIP_TICKET = 1

LOG_CHANNEL_ID = 1421465080238964796


class PetalRewards(commands.Cog):
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

    async def log_action(self, guild: discord.Guild, message: str):
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(message)

    # --- Event: attribution de rôle ---
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        new_roles = [r for r in after.roles if r not in before.roles]
        for role in new_roles:
            if role.id in ROLE_PETAL_REWARDS:
                reward = ROLE_PETAL_REWARDS[role.id]
                await self.add_balance(after.id, reward)
                try:
                    await after.send(f"🌸 You received **{reward} petals** for obtaining the role `{role.name}`!")
                except discord.Forbidden:
                    log.info(f"Could not DM {after} for petal reward.")
                await self.log_action(after.guild, f"🌸 {after.mention} received **{reward} petals** for role `{role.name}`")

    # --- Commande: /monthly ---
    @commands.hybrid_command(name="monthly", description="Distribute monthly rewards to specific roles")
    @commands.has_permissions(administrator=True)
    async def monthly(self, ctx: commands.Context):
        count = 0
        for role_id in MONTHLY_ROLES:
            role = ctx.guild.get_role(role_id)
            if not role:
                continue
            for member in role.members:
                await self.add_balance(member.id, MONTHLY_PETALS)
                await self.add_tickets(member.id, MONTHLY_SKIP_TICKET)
                count += 1
                await self.log_action(ctx.guild, f"🌸 {member.mention} received {MONTHLY_PETALS} petals and {MONTHLY_SKIP_TICKET} Skip Queue Ticket (monthly)")

        embed = discord.Embed(
            title="🌸 Monthly Rewards",
            description=f"Distributed rewards to **{count} members** in monthly roles.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    # --- Commande: /retroactive ---
    @commands.hybrid_command(name="retroactive", description="Grant petal rewards to members who already have the roles")
    @commands.has_permissions(administrator=True)
    async def retroactive(self, ctx: commands.Context):
        count = 0
        for role_id, reward in ROLE_PETAL_REWARDS.items():
            role = ctx.guild.get_role(role_id)
            if not role:
                continue
            for member in role.members:
                await self.add_balance(member.id, reward)
                count += 1
                await self.log_action(ctx.guild, f"🌸 {member.mention} retroactively received **{reward} petals** for role `{role.name}`")

        embed = discord.Embed(
            title="🌸 Retroactive Rewards",
            description=f"Granted role-based petal rewards to **{count} members** who already had the roles.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PetalRewards(bot))
    log.info("⚙️ PetalRewards cog loaded")
