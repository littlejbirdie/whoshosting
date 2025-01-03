import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
import asyncio
import os

# Bot and intents setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Predefined schedule
schedule = []
signups = {}
offline_status = {}

# Generate times from 1PM today to 11AM tomorrow (Eastern Time)
# Generate times from 11PM today to 9PM tomorrow (Eastern Time)
start_time = datetime.now(pytz.timezone("US/Eastern")).replace(hour=23, minute=0, second=0, microsecond=0)
end_time = start_time + timedelta(days=0, hours=22)  # Adjust for desired end time

current_time = start_time
while current_time <= end_time:
    utc_time = current_time.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule.append({"time": current_time.strftime("%I%p"), "utc_time": utc_time})
    current_time += timedelta(hours=2)


def format_groups(time):
    """Format group information for display."""
    if time not in signups:
        return f"No sign-ups for {time}!"

    formatted = f"**{time} Run Groups:**\n"
    for host, details in signups[time].items():
        formatted += f"- Host: {host} | Actives: {', '.join(details['actives'])} | Alts: {', '.join(details['alts'])}\n"
    return formatted

@bot.event
async def on_ready():
    """Event triggered when bot is ready."""
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    print(f"Logged in as {bot.user}")

# Slash Commands
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

@bot.tree.command(name="groups", description="View groups for a specific run time.")
@app_commands.describe(time="The time of the run (e.g., '1PM').")
async def groups(interaction: discord.Interaction, time: str):
    """Slash command to view groups for a specific time."""
    await interaction.response.send_message(format_groups(time))

@bot.tree.command(name="allgroups", description="View all groups for all scheduled runs.")
async def allgroups(interaction: discord.Interaction):
    """Slash command to view all groups."""
    if not signups:
        await interaction.response.send_message("No sign-ups yet!")
    else:
        for time in signups:
            await interaction.channel.send(format_groups(time))

@bot.tree.command(name="clear", description="Clear all sign-ups for a specific run.")
@app_commands.describe(time="The time of the run to clear (e.g., '1PM').")
async def clear(interaction: discord.Interaction, time: str):
    """Slash command to clear all sign-ups for a specific run. Restricted to admins."""
    if not any(role.name in ["officer", "leader", "fr3e staff"] for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if time in signups:
        await interaction.response.send_message(f"Are you sure you want to clear all sign-ups for {time}? Reply with `yes` in the next message.")

        def check(m):
            return m.author == interaction.user and m.content.lower() == "yes"

        try:
            confirmation = await bot.wait_for("message", check=check, timeout=30.0)
            if confirmation:
                del signups[time]
                await interaction.channel.send(f"All sign-ups for {time} have been cleared!")
        except asyncio.TimeoutError:
            await interaction.channel.send("Clear command timed out. No changes were made.")
    else:
        await interaction.response.send_message(f"No sign-ups found for {time}.")

bot.run(os.getenv("TOKEN"))
