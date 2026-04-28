import os
import discord
from discord import app_commands
from dotenv import load_dotenv
import aiosqlite
from discord.ext import tasks
from datetime import datetime, timezone, timedelta
import random
roast_counts = {}

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

DB_PATH = "chaosmod.db"
last_message_time = {}
dead_chat_sent = {}
DEAD_CHAT_MINUTES = 30


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roast_counts (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.commit()

async def increment_roast(guild_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO roast_counts (guild_id, user_id, count)
            VALUES (?, ?, 1)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET count = count + 1
        """, (guild_id, user_id))
        await db.commit()


async def get_roastboard(guild_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT user_id, count
            FROM roast_counts
            WHERE guild_id = ?
            ORDER BY count DESC
            LIMIT 10
        """, (guild_id,))
        return await cursor.fetchall()

@client.event
async def on_ready():
    try:
        if not dead_chat_detector.is_running():
            dead_chat_detector.start()
        await init_db()
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

    print(f"Logged in as {client.user}")


@tree.command(name="vibecheck", description="Check the vibe")
async def vibecheck(interaction: discord.Interaction):
    import random

    vibes = [
        "🟢 Immaculate vibes. Suspiciously rare.",
        "🟡 Mid. You exist, congrats.",
        "🔴 Catastrophic. Seek help immediately.",
        "💀 Negative aura detected.",
        "🔥 Main character energy (delusional)."
    ]

    await interaction.response.send_message(random.choice(vibes))

@tree.command(name="roast", description="Roast someone with adjustable violence")
@app_commands.describe(
    user="The unfortunate target",
    level="How cooked should they be?"
)
@app_commands.choices(level=[
    app_commands.Choice(name="mild", value="mild"),
    app_commands.Choice(name="medium", value="medium"),
    app_commands.Choice(name="nuclear", value="nuclear"),
])

async def roast(
    interaction: discord.Interaction,
    user: discord.Member,
    level: app_commands.Choice[str]
):
    import random

    if user == interaction.user:
        self_roasts = [
            "Roasting yourself? Finally, some accountability.",
            "You really queued up your own execution. Respect, but still embarrassing.",
            "Self-roast detected. The call is coming from inside the clown car.",
            "Bold move. Unfortunately, you still lost to yourself.",
        ]
        await interaction.response.send_message(random.choice(self_roasts))
        return

    roasts = {
        "mild": [
            f"{user.mention} has the energy of a loading screen.",
            f"{user.mention} is built like an unsaved draft.",
            f"{user.mention} types like their keyboard is filing a complaint.",
        ],
        "medium": [
            f"{user.mention} has main character syndrome with tutorial NPC stats.",
            f"{user.mention} brings nothing to the table except the awkward silence after.",
            f"{user.mention} has the confidence of someone who has never checked the docs.",
        ],
        "nuclear": [
            f"{user.mention} is what happens when Ctrl+Z stops working.",
            f"{user.mention} has the aura of deprecated code nobody wants to maintain.",
            f"{user.mention} is proof that not every side quest deserves lore.",
        ],
    }

    chosen_roast = random.choice(roasts[level.value])
    await increment_roast(interaction.guild_id, user.id)

    await interaction.response.send_message(chosen_roast)


    return

@tree.command(name="roastboard", description="See who has been cooked the most")
async def roastboard(interaction: discord.Interaction):
    rows = await get_roastboard(interaction.guild_id)

    if not rows:
        await interaction.response.send_message("Nobody has been roasted yet. Peace was never an option.")
        return

    lines = []
    for index, (user_id, count) in enumerate(rows, start=1):
        lines.append(f"{index}. <@{user_id}> — {count} roast(s)")

    message = "🔥 **Roastboard** 🔥\n\n" + "\n".join(lines)
    await interaction.response.send_message(message)


@tree.command(name="roaststats", description="See how cooked someone is")
@app_commands.describe(user="Target user")
async def roaststats(interaction: discord.Interaction, user: discord.Member = None):
    if user is None:
        user = interaction.user

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT count FROM roast_counts
            WHERE guild_id = ? AND user_id = ?
        """, (interaction.guild_id, user.id))

        row = await cursor.fetchone()

    count = row[0] if row else 0

    # tiers (this is where personality comes in)
    if count == 0:
        verdict = "Untouched. Suspicious. Probably lurking."
    elif count < 5:
        verdict = "Lightly cooked. Early signs of concern."
    elif count < 15:
        verdict = "Moderately roasted. Reputation declining."
    elif count < 30:
        verdict = "Heavily cooked. People are noticing."
    else:
        verdict = "💀 Irrecoverable. This is your legacy now."

    await interaction.response.send_message(
        f"📊 {user.mention} has been roasted **{count}** times.\n{verdict}"
    )

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.guild:
        last_message_time[message.guild.id] = message.created_at

@tasks.loop(minutes=5)
async def dead_chat_detector():
    now = datetime.now(timezone.utc)

    for guild in client.guilds:
        last_seen = last_message_time.get(guild.id)

        if last_seen is None:
            continue

        is_dead = now - last_seen > timedelta(minutes=DEAD_CHAT_MINUTES)

        if not is_dead:
            dead_chat_sent[guild.id] = False
            continue

        if dead_chat_sent.get(guild.id):
            continue

        channel = guild.system_channel

        if channel is None:
            text_channels = [
                c for c in guild.text_channels
                if c.permissions_for(guild.me).send_messages
            ]
            channel = text_channels[0] if text_channels else None

        if channel is None:
            continue

        messages = [
            "This chat died harder than everyone’s New Year’s resolutions.",
            "Dead chat detected. Incredible work, everyone. Truly lifeless.",
            "I’ve seen abandoned side projects with more activity than this server.",
            "The vibe here is so dead I almost filed a missing persons report.",
            "Chat’s quieter than someone explaining their GitHub contribution graph.",
        ]

        await channel.send(random.choice(messages))
        dead_chat_sent[guild.id] = True

client.run(TOKEN)