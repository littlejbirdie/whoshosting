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
    {"run": "Run A", "utc_timestamp": 1735898400},  # 5AM Eastern = 10AM UTC
    {"run": "Run B", "utc_timestamp": 1735905600},  # 7AM Eastern = 12AM UTC
    {"run": "Run C", "utc_timestamp": 1735912800},  # 9AM Eastern = 2PM UTC
    {"run": "Run D", "utc_timestamp": 1735920000},  # 11AM Eastern = 4PM UTC
]

signups = {}
offline_status = {}

@bot.tree.command(name="bothelp", description="Display a list of available commands.")
async def bothelp(interaction: discord.Interaction):
    """Slash command to display all bot commands and their usage."""
    help_message = (
        "**Bot Commands:**\n"
        "`/schedule - Displays the local time for each run. Run A is 5am EST.\n"
        "`/join [time] [role] [host(optional)]` - Join or update your status for a single run. Roles: 'host', 'active', 'alt', 'unavailable'.\n"
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

@bot.tree.command(name="join", description="Join or update your status for a run.")
@app_commands.describe(
    run="The run you want to join (e.g., 'A').",
    role="Your role in the run (host, active, alt, or unavailable).",
    name="The in-game name you want to use (optional). Defaults to your Discord username.",
    host="The host's name or additional names (optional)."
)
@app_commands.choices(
    run=[
        app_commands.Choice(name="Run A", value="A"),
        app_commands.Choice(name="Run B", value="B"),
        app_commands.Choice(name="Run C", value="C"),
        app_commands.Choice(name="Run D", value="D"),
    ],
    role=[
        app_commands.Choice(name="Host", value="host"),
        app_commands.Choice(name="Active", value="active"),
        app_commands.Choice(name="Alt", value="alt"),
        app_commands.Choice(name="Unavailable", value="unavailable"),
    ]
)
async def join(
    interaction: discord.Interaction,
    run: app_commands.Choice[str],
    role: app_commands.Choice[str],
    name: str = None,
    host: str = None
):
    """Slash command to join or update your status for a single run."""
    await interaction.response.defer()

    # Extract selected values
    run_label = run.value
    role_label = role.value

    # Default to the user's Discord name if no name is provided
    player_name = name or interaction.user.display_name

    # Default to "Join Without Host" if no host is provided
    host = host or "Join Without Host"

    # Add the player to the chosen run
    if run_label not in signups:
        signups[run_label] = {}

    # Ensure the host group exists
    if host not in signups[run_label]:
        signups[run_label][host] = {"actives": [], "alts": [], "unavailable": []}

    # Handle roles
    if role_label == "host":
        signups[run_label][host] = {"actives": [], "alts": [], "unavailable": []}
    elif role_label == "active":
        if player_name not in signups[run_label][host]["actives"]:
            signups[run_label][host]["actives"].append(player_name)
    elif role_label == "alt":
        if player_name not in signups[run_label][host]["alts"]:
            signups[run_label][host]["alts"].append(player_name)
    elif role_label == "unavailable":
        if player_name not in signups[run_label][host]["unavailable"]:
            signups[run_label][host]["unavailable"].append(player_name)

    # Send confirmation
    run_time = next(r for r in schedule if r["run"].endswith(run_label))
    await interaction.followup.send(
        f"{player_name} has been added as '{role_label}' for Run {run_label} (<t:{run_time['utc_timestamp']}:f>) in the group '{host}'."
    )

@bot.tree.command(name="groups", description="View groups for a specific run.")
@app_commands.describe(
    run="The run you want to view (e.g., 'A')."
)
@app_commands.choices(
    run=[
        app_commands.Choice(name="Run A", value="A"),
        app_commands.Choice(name="Run B", value="B"),
        app_commands.Choice(name="Run C", value="C"),
        app_commands.Choice(name="Run D", value="D"),
    ]
)
async def groups(interaction: discord.Interaction, run: app_commands.Choice[str]):
    """Slash command to view groups for a specific run."""
    run_label = run.value

    # Check if there are any sign-ups for the given run
    if run_label not in signups or not signups[run_label]:
        await interaction.response.send_message(f"No sign-ups for Run {run_label}!")
        return

    # Format the groups for the given run
    formatted_groups = []
    unavailable_players = []
    for host, details in signups[run_label].items():
        actives = ", ".join(details["actives"]) if details["actives"] else "None"
        alts = ", ".join(details["alts"]) if details["alts"] else "None"
        if details["unavailable"]:
            unavailable_players.extend(details["unavailable"])  # Collect unavailable players
        formatted_groups.append(f"- Host: {host} | Actives: {actives} | Alts: {alts}")

    # Add unavailable players as a separate group
    if unavailable_players:
        formatted_groups.append(
            f"**Unavailable Players:** {', '.join(unavailable_players)}"
        )

    # Retrieve the UTC timestamp for the run and respond with the group details
    run_time = next(r for r in schedule if r["run"].endswith(run_label))
    response = f"**Run {run_label} Groups (<t:{run_time['utc_timestamp']}:f>):**\n" + "\n".join(formatted_groups)
    await interaction.response.send_message(response)

bot.run(os.getenv("TOKEN"))
