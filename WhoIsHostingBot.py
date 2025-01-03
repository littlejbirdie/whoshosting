import discord
from discord import app_commands
from discord.ext import commands
import os

# Bot and intents setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Predefined schedule starting at 3AM
schedule = [
    {"time": "3AM", "utc_timestamp": 1706953200},  # 3AM Eastern = 8AM UTC
    {"time": "5AM", "utc_timestamp": 1706960400},  # 5AM Eastern = 10AM UTC
    {"time": "7AM", "utc_timestamp": 1706967600},  # 7AM Eastern = 12PM UTC
    {"time": "9AM", "utc_timestamp": 1706974800},  # 9AM Eastern = 2PM UTC
    {"time": "11AM", "utc_timestamp": 1706982000}, # 11AM Eastern = 4PM UTC
]
signups = {}
offline_status = {}

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
        print(f"Synced {len(synced)} commands successfully.")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="bothelp", description="Display a list of available commands.")
async def bothelp(interaction: discord.Interaction):
    """Slash command to display all bot commands and their usage."""
    help_message = (
        "**Bot Commands:**\n"
        "`/join [time] [role] [host(optional)]` - Join or update your status for a run. Roles: 'host', 'active', 'alt', 'unavailable'.\n"
        "`/groups [time]` - View groups for a specific run time.\n"
        "`/allgroups` - View all groups for all scheduled runs.\n"
        "`/clear [time]` - Clear all sign-ups for a specific run OFFICERS ONLY.\n"
        "`/bulkjoin [times] [names] [host]` - Add multiple names to a host's group for multiple times. Example: `/bulkjoin times: 3AM, 5AM names: John, Jane host: HostName`.\n"
    )
    await interaction.response.send_message(help_message)

@bot.tree.command(name="join", description="Join or update your status for a run.")
@app_commands.describe(
    time="The time of the run (e.g., '3AM').",
    role="Your role in the run (host, active, alt, or unavailable).",
    host_or_names="Host's name or additional names (optional)."
)
@app_commands.choices(
    time=[
        app_commands.Choice(name="3AM", value="3AM"),
        app_commands.Choice(name="5AM", value="5AM"),
        app_commands.Choice(name="7AM", value="7AM"),
        app_commands.Choice(name="9AM", value="9AM"),
        app_commands.Choice(name="11AM", value="11AM"),
    ]
)
async def join(interaction: discord.Interaction, time: app_commands.Choice[str], role: str, host_or_names: str = None):
    """Slash command to join or update your status for a run."""
    time_value = time.value
    if time_value not in [run["time"] for run in schedule]:
        await interaction.response.send_message(f"{time_value} is not a valid run time. Use `/join` to view available times.")
        return

    if time_value not in signups:
        signups[time_value] = {}

    player_name = interaction.user.mention

    # Set default host to "Join Without Host" if no host is specified
    host = host_or_names or "Join Without Host"

    # Ensure the host group exists
    if host not in signups[time_value]:
        signups[time_value][host] = {"actives": [], "alts": [], "unavailable": []}

    # Handle roles
    if role.lower() == "host":
        # Update host role
        signups[time_value][host] = {"actives": [], "alts": [], "unavailable": []}
        await interaction.response.send_message(f"{player_name} has volunteered to host the {time_value} run under the group '{host}'!")
    elif role.lower() == "active":
        # Remove player from any existing group
        for group in signups[time_value].values():
            if player_name in group["actives"]:
                group["actives"].remove(player_name)

        # Add to the specified host group
        signups[time_value][host]["actives"].append(player_name)
        await interaction.response.send_message(f"{player_name} has joined the {time_value} run as an active player in the group '{host}'.")
    elif role.lower() == "alt":
        # Add player to alts for the specified host
        signups[time_value][host]["alts"].append(player_name)
        await interaction.response.send_message(f"{player_name} has joined the {time_value} run as an alt in the group '{host}'.")
    elif role.lower() == "unavailable":
        # Remove player from all groups for the time slot
        for group in signups[time_value].values():
            if player_name in group["actives"]:
                group["actives"].remove(player_name)
            if player_name in group["alts"]:
                group["alts"].remove(player_name)

        # Mark the player as unavailable
        signups[time_value][host]["unavailable"].append(player_name)
        await interaction.response.send_message(f"{player_name} has marked themselves as unavailable for the {time_value} run.")
    else:
        await interaction.response.send_message("Invalid role! Use 'host', 'active', 'alt', or 'unavailable'.")

@bot.tree.command(name="bulkjoin", description="Add multiple names to a host's group for multiple times.")
@app_commands.describe(
    times="Comma-separated list of run times (e.g., '3AM, 5AM, 7AM').",
    names="Comma-separated list of names to add as actives.",
    host="The host's name or mention for the groups (optional)."
)
async def bulkjoin(interaction: discord.Interaction, times: str, names: str, host: str = None):
    """Slash command to add multiple names to a host's group for multiple times."""
    # Split and clean input
    time_list = [time.strip() for time in times.split(",")]
    name_list = [name.strip() for name in names.split(",")]

    # Default host to "Join Without Host" if none is provided
    host = host or "Join Without Host"

    # Validate times
    valid_times = [run["time"] for run in schedule]
    invalid_times = [time for time in time_list if time not in valid_times]

    if invalid_times:
        await interaction.response.send_message(
            f"The following times are invalid: {', '.join(invalid_times)}. Use `/join` to view available times.",
            ephemeral=True
        )
        return

    # Process valid times and add names to the specified host
    for time in time_list:
        if time not in signups:
            signups[time] = {}

        # Ensure the host group exists
        if host not in signups[time]:
            signups[time][host] = {"actives": [], "alts": [], "unavailable": []}

        # Add each name to the actives list for the host
        for name in name_list:
            # Prevent duplicates
            if name not in signups[time][host]["actives"]:
                signups[time][host]["actives"].append(name)

    # Send confirmation
    await interaction.response.send_message(
        f"Added {', '.join(name_list)} to '{host}' for {', '.join(time_list)}!"
    )

@bot.tree.command(name="clear", description="Clear all sign-ups for a specific run.")
@app_commands.describe(time="The time of the run to clear (e.g., '3AM').")
@app_commands.choices(
    time=[
        app_commands.Choice(name="3AM", value="3AM"),
        app_commands.Choice(name="5AM", value="5AM"),
        app_commands.Choice(name="7AM", value="7AM"),
        app_commands.Choice(name="9AM", value="9AM"),
        app_commands.Choice(name="11AM", value="11AM"),
    ]
)
async def clear(interaction: discord.Interaction, time: app_commands.Choice[str]):
    """Slash command to clear all sign-ups for a specific run."""
    time_value = time.value
    if time_value in signups:
        del signups[time_value]
        await interaction.response.send_message(f"All sign-ups for {time_value} have been cleared!")
    else:
        await interaction.response.send_message(f"No sign-ups found for {time_value}.")

bot.run(os.getenv("TOKEN"))
