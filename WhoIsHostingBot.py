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

@bot.tree.command(name="times", description="Display scheduled run times.")
async def times(interaction: discord.Interaction):
    """Slash command to display run times in UTC, auto-adjusted for user timezones."""
    # Fixed times in UTC
    utc_times = [
        {"time": "11PM", "utc_timestamp": 1706948400},  # Replace with actual UNIX timestamps
        {"time": "1AM", "utc_timestamp": 1706955600},
        {"time": "3AM", "utc_timestamp": 1706962800},
        {"time": "5AM", "utc_timestamp": 1706970000},
        {"time": "7AM", "utc_timestamp": 1706977200},
        {"time": "9AM", "utc_timestamp": 1706984400},
        {"time": "11AM", "utc_timestamp": 1706991600},
    ]

    # Format times for display
    run_times = [
        f"{time['time']} Eastern: <t:{time['utc_timestamp']}:f>"
        for time in utc_times
    ]

    await interaction.response.send_message("**Scheduled Runs:**\n" + "\n".join(run_times))


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

#slash commands
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
@app_commands.describe(time="The time of the run (e.g., '11PM').")
async def groups(interaction: discord.Interaction, time: str):
    """Slash command to view groups for a specific time."""
    if time not in [run["time"] for run in schedule]:
        await interaction.response.send_message(f"{time} is not a valid time. Use `/times` to view available times.")
        return
    await interaction.response.send_message(format_groups(time))

@bot.tree.command(name="allgroups", description="View all groups for all scheduled runs.")
async def allgroups(interaction: discord.Interaction):
    """Slash command to view all groups."""
    if not signups:
        await interaction.response.send_message("No sign-ups yet!")
    else:
        formatted_groups = [format_groups(time["time"]) for time in schedule if time["time"] in signups]
        await interaction.response.send_message("\n\n".join(formatted_groups))

@bot.tree.command(name="bothelp", description="Display a list of available commands.")
async def bothelp(interaction: discord.Interaction):
    """Slash command to display all bot commands and their usage."""
    help_message = (
        "**Bot Commands:**\n"
        "`/times` - Display scheduled run times.\n"
        "`/join [time] [role] [host(optional)]` - Join a run. Roles: 'host', 'active', 'alt'.\n"
        "`/groups [time]` - View groups for a specific run time.\n"
        "`/allgroups` - View all groups for all scheduled runs.\n"
        "`/clear [time]` - Clear all sign-ups for a specific run (Admin Only).\n"
        "`/bulkjoin [time] [names]` - Add multiple names and times to a group at once.\n"
    )
    await interaction.response.send_message(help_message)

@bot.tree.command(name="bulkjoin", description="Add multiple names to a host's group for multiple times.")
@app_commands.describe(
    times="Comma-separated list of run times (e.g., '11PM, 1AM, 3AM').",
    names="Comma-separated list of names to add as actives or alts.",
    host="The host's name or mention for the groups."
)
async def bulkjoin(interaction: discord.Interaction, times: str, names: str, host: str):
    """Slash command to add multiple names to a host's group for multiple times."""
    # Split and clean input
    time_list = [time.strip() for time in times.split(",")]
    name_list = [name.strip() for name in names.split(",")]

    # Validate times
    valid_times = [run["time"] for run in schedule]
    invalid_times = [time for time in time_list if time not in valid_times]

    if invalid_times:
        await interaction.response.send_message(
            f"The following times are invalid: {', '.join(invalid_times)}. Use `/times` to view available times.",
            ephemeral=True
        )
        return

    # Process valid times and add names to the specified host
    for time in time_list:
        if time not in signups:
            signups[time] = {}

        # Add names to the group of the specified host
        if host not in signups[time]:
            signups[time][host] = {"actives": [], "alts": []}

        signups[time][host]["actives"].extend(name_list)

    await interaction.response.send_message(
        f"Added {', '.join(name_list)} to {host}'s group for {', '.join(time_list)}!"
    )
    
@bot.tree.command(name="clear", description="Clear all sign-ups for a specific run.")
@app_commands.describe(time="The time of the run to clear (e.g., '11PM').")
async def clear(interaction: discord.Interaction, time: str):
    """Slash command to clear all sign-ups for a specific run. Restricted to admins."""
    if not any(role.name in ["officer", "leader", "fr3e staff"] for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    if time in [run["time"] for run in schedule]:
        if time in signups:
            del signups[time]
            await interaction.response.send_message(f"All sign-ups for {time} have been cleared!")
        else:
            await interaction.response.send_message(f"No sign-ups found for {time}.")
    else:
        await interaction.response.send_message(f"{time} is not a valid time. Use `/times` to view available times.")


bot.run(os.getenv("TOKEN"))
