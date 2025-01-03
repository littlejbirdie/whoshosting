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
    )
    await interaction.response.send_message(help_message)

@bot.tree.command(name="join", description="Join or update your status for one or more runs.")
@app_commands.describe(
    times="The time(s) of the run(s) (e.g., '3AM', '5AM').",
    role="Your role in the run(s) (host, active, alt, or unavailable).",
    name="The in-game name you want to use (optional). Defaults to your Discord username.",
    host="The host's name or additional names (optional)."
)
@app_commands.choices(
    times=[
        app_commands.Choice(name="3AM", value="3AM"),
        app_commands.Choice(name="5AM", value="5AM"),
        app_commands.Choice(name="7AM", value="7AM"),
        app_commands.Choice(name="9AM", value="9AM"),
        app_commands.Choice(name="11AM", value="11AM"),
    ]
)
async def join(interaction: discord.Interaction, times: str, role: str, name: str = None, host: str = None):
    """Slash command to join or update your status for multiple runs."""
    await interaction.response.defer()  # Prevent timeout

    time_list = [time.strip() for time in times.split(",")]

    # Validate times
    valid_times = [run["time"] for run in schedule]
    invalid_times = [time for time in time_list if time not in valid_times]

    if invalid_times:
        await interaction.followup.send(
            f"The following times are invalid: {', '.join(invalid_times)}. Use valid times: {', '.join(valid_times)}.",
            ephemeral=True
        )
        return

    # Default to the user's Discord name if no name is provided
    player_name = name or interaction.user.display_name

    # Default to "Join Without Host" if no host is provided
    host = host or "Join Without Host"

    # Process each valid time
    for time_value in time_list:
        if time_value not in signups:
            signups[time_value] = {}

        # Ensure the host group exists
        if host not in signups[time_value]:
            signups[time_value][host] = {"actives": [], "alts": [], "unavailable": []}

        # Handle roles
        if role.lower() == "host":
            signups[time_value][host] = {"actives": [], "alts": [], "unavailable": []}
        elif role.lower() == "active":
            if player_name not in signups[time_value][host]["actives"]:
                signups[time_value][host]["actives"].append(player_name)
        elif role.lower() == "alt":
            if player_name not in signups[time_value][host]["alts"]:
                signups[time_value][host]["alts"].append(player_name)
        elif role.lower() == "unavailable":
            if player_name not in signups[time_value][host]["unavailable"]:
                signups[time_value][host]["unavailable"].append(player_name)

    # Send confirmation
    await interaction.followup.send(
        f"{player_name} has been added as '{role}' for the following times: {', '.join(time_list)} in the group '{host}'."
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
