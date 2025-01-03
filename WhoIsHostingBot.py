import discord
from discord import app_commands
from discord.ext import commands
import os

import discord
from discord import app_commands
from discord.ext import commands
import os

# Bot and intents setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Predefined schedule with Run labels
schedule = [
    {"run": "Run A", "utc_timestamp": 1735881600},  # 3AM Eastern = 8AM UTC
    {"run": "Run B", "utc_timestamp": 1735888800},  # 5AM Eastern = 10AM UTC
    {"run": "Run C", "utc_timestamp": 1735896000},  # 7AM Eastern = 12PM UTC
    {"run": "Run D", "utc_timestamp": 1735903200},  # 9AM Eastern = 2PM UTC
    {"run": "Run E", "utc_timestamp": 1735910400},  # 11AM Eastern = 4PM UTC
]

signups = {}
offline_status = {}

@bot.tree.command(name="bothelp", description="Display a list of available commands.")
async def bothelp(interaction: discord.Interaction):
    """Slash command to display all bot commands and their usage."""
    help_message = (
        "**Bot Commands:**\n"
        "`/schedule - Displays the local time for each run. Run A is 3am EST.\n"
        "`/join [time] [role] [host(optional)]` - Join or update your status for a run. Roles: 'host', 'active', 'alt', 'unavailable'.\n"
        "`/groups [time]` - View groups for a specific run time.\n"
    )
    await interaction.response.send_message(help_message)
    
@bot.event
async def on_ready():
    """Event triggered when bot is ready."""
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands successfully.")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="schedule", description="View the full schedule with local times.")
async def schedule_command(interaction: discord.Interaction):
    """Slash command to display the full schedule with local times."""
    schedule_message = "**Run Schedule:**\n"
    for run in schedule:
        schedule_message += f"{run['run']}: <t:{run['utc_timestamp']}:f>\n"
    await interaction.response.send_message(schedule_message)

@bot.tree.command(name="join", description="Join or update your status for one or more runs.")
@app_commands.describe(
    runs="The run(s) you want to join (e.g., 'Run A').",
    role="Your role in the run(s) (host, active, alt, or unavailable).",
    name="The in-game name you want to use (optional). Defaults to your Discord username.",
    host="The host's name or additional names (optional)."
)
@app_commands.choices(
    runs=[
        app_commands.Choice(name="Run A", value="Run A"),
        app_commands.Choice(name="Run B", value="Run B"),
        app_commands.Choice(name="Run C", value="Run C"),
        app_commands.Choice(name="Run D", value="Run D"),
        app_commands.Choice(name="Run E", value="Run E"),
    ]
)
async def join(
    interaction: discord.Interaction,
    runs: app_commands.Choice[str],
    role: str,
    name: str = None,
    host: str = None
):
    """Slash command to join or update your status for one or more runs."""
    await interaction.response.defer()

    run_label = runs.value

    # Default to the user's Discord name if no name is provided
    player_name = name or interaction.user.display_name

    # Default to "Join Without Host" if no host is provided
    host = host or "Join Without Host"

    # Add the player to the chosen run
    run = next(run for run in schedule if run["run"] == run_label)
    utc_timestamp = run["utc_timestamp"]

    if run_label not in signups:
        signups[run_label] = {}

    # Ensure the host group exists
    if host not in signups[run_label]:
        signups[run_label][host] = {"actives": [], "alts": [], "unavailable": []}

    # Handle roles
    if role.lower() == "host":
        signups[run_label][host] = {"actives": [], "alts": [], "unavailable": []}
    elif role.lower() == "active":
        if player_name not in signups[run_label][host]["actives"]:
            signups[run_label][host]["actives"].append(player_name)
    elif role.lower() == "alt":
        if player_name not in signups[run_label][host]["alts"]:
            signups[run_label][host]["alts"].append(player_name)
    elif role.lower() == "unavailable":
        if player_name not in signups[run_label][host]["unavailable"]:
            signups[run_label][host]["unavailable"].append(player_name)

    # Send confirmation
    await interaction.followup.send(
        f"{player_name} has been added as '{role}' for {run_label} (<t:{utc_timestamp}:f>) in the group '{host}'."
    )

@bot.tree.command(name="groups", description="View groups for a specific run.")
@app_commands.describe(
    run="The run you want to view (e.g., 'Run A')."
)
@app_commands.choices(
    run=[
        app_commands.Choice(name="Run A", value="Run A"),
        app_commands.Choice(name="Run B", value="Run B"),
        app_commands.Choice(name="Run C", value="Run C"),
        app_commands.Choice(name="Run D", value="Run D"),
        app_commands.Choice(name="Run E", value="Run E"),
    ]
)
async def groups(interaction: discord.Interaction, run: app_commands.Choice[str]):
    """Slash command to view groups for a specific run."""
    run_label = run.value

    if run_label not in signups or not signups[run_label]:
        await interaction.response.send_message(f"No sign-ups for {run_label}!")
        return

    formatted_groups = []
    for host, details in signups[run_label].items():
        actives = ", ".join(details["actives"]) if details["actives"] else "None"
        alts = ", ".join(details["alts"]) if details["alts"] else "None"
        formatted_groups.append(f"- Host: {host} | Actives: {actives} | Alts: {alts}")

    run_time = next(r for r in schedule if r["run"] == run_label)
    response = f"**{run_label} Groups (<t:{run_time['utc_timestamp']}:f>):**\n" + "\n".join(formatted_groups)
    await interaction.response.send_message(response)

bot.run(os.getenv("TOKEN"))
