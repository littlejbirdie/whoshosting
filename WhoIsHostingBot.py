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
    name="The in-game name you want to use (optional). Defaults to your Discord username.",
    host="The host's name or additional names (optional)."
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
async def join(interaction: discord.Interaction, time: app_commands.Choice[str], role: str, name: str = None, host: str = None):
    """Slash command to join or update your status for a run."""
    await interaction.response.defer()  # Defer response to prevent timeout
    time_value = time.value

    if time_value not in [run["time"] for run in schedule]:
        await interaction.followup.send(f"{time_value} is not a valid run time. Use `/join` to view available times.")
        return

    if time_value not in signups:
        signups[time_value] = {}

    # Default to the user's Discord name if no name is provided
    player_name = name or interaction.user.display_name

    # Default to "Join Without Host" if no host is provided
    host = host or "Join Without Host"

    # Ensure the host group exists
    if host not in signups[time_value]:
        signups[time_value][host] = {"actives": [], "alts": [], "unavailable": []}

    # Handle roles
    if role.lower() == "host":
        # Update host role
        signups[time_value][host] = {"actives": [], "alts": [], "unavailable": []}
        await interaction.followup.send(f"{player_name} has volunteered to host the {time_value} run under the group '{host}'!")
    elif role.lower() == "active":
        # Remove player from any existing group
        for group in signups[time_value].values():
            if player_name in group["actives"]:
                group["actives"].remove(player_name)

        # Add to the specified host group
        signups[time_value][host]["actives"].append(player_name)
        await interaction.followup.send(f"{player_name} has joined the {time_value} run as an active player in the group '{host}'.")
    elif role.lower() == "alt":
        # Add player to alts for the specified host
        signups[time_value][host]["alts"].append(player_name)
        await interaction.followup.send(f"{player_name} has joined the {time_value} run as an alt in the group '{host}'.")
    elif role.lower() == "unavailable":
        # Remove player from all groups for the time slot
        for group in signups[time_value].values():
            if player_name in group["actives"]:
                group["actives"].remove(player_name)
            if player_name in group["alts"]:
                group["alts"].remove(player_name)

        # Mark the player as unavailable
        signups[time_value][host]["unavailable"].append(player_name)
        await interaction.followup.send(f"{player_name} has marked themselves as unavailable for the {time_value} run.")
    else:
        await interaction.followup.send("Invalid role! Use 'host', 'active', 'alt', or 'unavailable'.")

@bot.tree.command(name="bulkjoin", description="Add multiple names to a host's group for multiple times.")
@app_commands.describe(
    times="Comma-separated list of run times (e.g., '3AM, 5AM, 7AM').",
    names="Comma-separated list of names to add.",
    role="The role for the names being added (active or alt).",
    host="The host's name or mention for the groups (optional). Defaults to 'Join Without Host'."
)
async def bulkjoin(interaction: discord.Interaction, times: str, names: str, role: str, host: str = None):
    """Slash command to add multiple names to a host's group for multiple times."""
    await interaction.response.defer()  # Defer response to prevent timeout

    # Split and clean input
    time_list = [time.strip() for time in times.split(",")]
    name_list = [name.strip() for name in names.split(",")]

    # Default host to "Join Without Host" if none is provided
    host = host or "Join Without Host"

    # Validate times
    valid_times = [run["time"] for run in schedule]
    invalid_times = [time for time in time_list if time not in valid_times]

    if invalid_times:
        await interaction.followup.send(
            f"The following times are invalid: {', '.join(invalid_times)}. Use `/join` to view available times.",
            ephemeral=True
        )
        return

    # Validate role
    if role.lower() not in ["active", "alt"]:
        await interaction.followup.send(
            "Invalid role! Please use 'active' or 'alt'.",
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

        # Add each name to the correct role for the host
        for name in name_list:
            if role.lower() == "active":
                if name not in signups[time][host]["actives"]:
                    signups[time][host]["actives"].append(name)
            elif role.lower() == "alt":
                if name not in signups[time][host]["alts"]:
                    signups[time][host]["alts"].append(name)

    # Send confirmation
    await interaction.followup.send(
        f"Added {', '.join(name_list)} as '{role}' to '{host}' for {', '.join(time_list)}!"
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

@bot.tree.command(name="groups", description="View groups for a specific run time.")
@app_commands.describe(time="The time of the run to view (e.g., '3AM').")
@app_commands.choices(
    time=[
        app_commands.Choice(name="3AM", value="3AM"),
        app_commands.Choice(name="5AM", value="5AM"),
        app_commands.Choice(name="7AM", value="7AM"),
        app_commands.Choice(name="9AM", value="9AM"),
        app_commands.Choice(name="11AM", value="11AM"),
    ]
)
async def groups(interaction: discord.Interaction, time: app_commands.Choice[str]):
    """Slash command to view groups for a specific time."""
    time_value = time.value

    if time_value not in signups or not signups[time_value]:
        await interaction.response.send_message(f"No sign-ups for {time_value}!")
        return

    formatted_groups = []
    for host, details in signups[time_value].items():
        actives = ", ".join(details["actives"]) if details["actives"] else "None"
        alts = ", ".join(details["alts"]) if details["alts"] else "None"
        formatted_groups.append(f"- Host: {host} | Actives: {actives} | Alts: {alts}")

    response = f"**{time_value} Run Groups:**\n" + "\n".join(formatted_groups)
    await interaction.response.send_message(response)

bot.run(os.getenv("TOKEN"))
