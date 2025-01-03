
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
import os

# Bot and intents setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Predefined schedule
schedule = []
signups = {}

# Generate times from 1PM today to 11AM tomorrow (Eastern Time)
start_time = datetime.now(pytz.timezone("US/Eastern")).replace(hour=13, minute=0, second=0, microsecond=0)
end_time = start_time + timedelta(days=1, hours=-2)

current_time = start_time
while current_time <= end_time:
    utc_time = current_time.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule.append({"time": current_time.strftime("%I%p"), "utc_time": utc_time})
    current_time += timedelta(hours=2)


@bot.event
async def on_ready():
    """Event triggered when bot is ready."""
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    print(f"Logged in as {bot.user}")


@bot.tree.command(name="times", description="Display scheduled run times.")
async def times(interaction: discord.Interaction):
    """Slash command to display run times."""
    local_times = []
    for run in schedule:
        utc_time = datetime.strptime(run["utc_time"], "%Y-%m-%dT%H:%M:%SZ")
        unix_timestamp = int(utc_time.timestamp())
        local_times.append(f"{run['time']}: <t:{unix_timestamp}:f>")
    await interaction.response.send_message("**Scheduled Runs:**\n" + "\n".join(local_times))


@bot.tree.command(name="join", description="Join a run.")
@app_commands.describe(
    time="The time of the run (e.g., '1PM').",
    role="Your role in the run (host, active, or alt).",
    host_or_names="Host's name or additional names (optional)."
)
async def join(interaction: discord.Interaction, time: str, role: str, host_or_names: str = None):
    """Slash command to join a run."""
    if time not in [run["time"] for run in schedule]:
        await interaction.response.send_message(f"{time} is not a valid run time. Use `/times` to view available times.")
        return

    if time not in signups:
        signups[time] = {}

    player_name = interaction.user.mention

    if role.lower() == "host":
        if player_name not in signups[time]:
            signups[time][player_name] = {"actives": [], "alts": []}
            await interaction.response.send_message(f"{player_name} has volunteered to host the {time} run!")
        else:
            await interaction.response.send_message(f"{player_name}, you are already hosting the {time} run!")
    elif role.lower() == "active":
        if host_or_names:
            host = host_or_names
            if host in signups[time]:
                signups[time][host]["actives"].append(player_name)
                await interaction.response.send_message(f"{player_name} has joined {host}'s group as an active player for {time}!")
            else:
                await interaction.response.send_message(f"{host} is not a registered host for {time}.")
        else:
            await interaction.response.send_message("Please specify a host to join.")
    elif role.lower() == "alt":
        if host_or_names:
            host = host_or_names.split(",")[0]
            alts = [alt.strip() for alt in host_or_names.split(",")[1:]]
            if host in signups[time]:
                signups[time][host]["alts"].extend(alts)
                await interaction.response.send_message(f"{', '.join(alts)} added as alts to {host}'s group for {time}!")
            else:
                await interaction.response.send_message(f"{host} is not a registered host for {time}.")
        else:
            await interaction.response.send_message("Please specify a host and the alts to join.")
    else:
        await interaction.response.send_message("Invalid role! Use 'host', 'active', or 'alt'.")

bot.run(os.getenv("TOKEN"))
