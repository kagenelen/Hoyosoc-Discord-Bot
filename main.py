import discord
from discord.ext import tasks
from discord import app_commands
from discord.ui import Button, View
from dotenv import load_dotenv
import os
import json
import random
import time

import helper
import uid_finder
import gambling
import minigame
# from keep_alive import keep_alive

# IMPORTANT: Replit code is using a test bot on the test server. Before committing please change GENSOC_SERVER back to actual server's id

############################ CONSTANTS ###################################
VERIFICATION_CHANNEL = 822423063697948693
GENSOC_SERVER = 822411164846653490 # Actual gensoc server
GENSOC_SERVER = 962970271545982986 # Test server
WELCOME_CHANNEL = 822411164846653492
WELCOME_MESSAGE = "Welcome traveller! <:GuobaWave:895891227067711548> Remember to fill out the verification form to gain access to the server. Enjoy your stay at GenSoc and feel free to chuck an intro in <#822732136515764265>."
PRIMOJEM_EMOTE = "<:Primojem:1108620629902626816>"
JEMDUST_EMOTE = "<:Jemdust:1108591111649362043>"

# Read json file for channel
absolute_path = os.path.dirname(os.path.abspath(__file__)) + "/json_files/"
with open(absolute_path + 'config.json', 'r') as f:
    data = json.load(f)
    VERIFICATION_CHANNEL = data['channel']
    f.close()

############################# CODE STARTS HERE ############################


# member intent has to be on, otherwise guild.members doesn't work
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
	print("*****Bot has connected*****")
	await tree.sync(guild=discord.Object(id=GENSOC_SERVER))
	daily_role_expiry_check.start()
	make_backup.start()

@client.event
async def on_message(message):
	global VERIFICATION_CHANNEL
	global WELCOME_CHANNEL
	global WELCOME_MESSAGE

	####### This section deals with sticky note ###########################
	if (message.channel.id == WELCOME_CHANNEL and not message.author.bot):
		welcome = await message.channel.send(WELCOME_MESSAGE)

		data = helper.read_file("config.json")
		channel = client.get_channel(WELCOME_CHANNEL)
		old_welcome = await channel.fetch_message(data["prev_message"])
		await old_welcome.delete()

		data["prev_message"] = welcome.id
		helper.write_file("config.json", data)
		return

	####### This section deals with verifying ##############################
	if (message.channel.id == VERIFICATION_CHANNEL):
		user = await helper.verify_user(message)
		if user == None:
			return

		# Send the user a character welcome message
		data = helper.read_file("message.json")
		welcome_character = random.choices(list(data.keys()), k=1)[0]
		character_message = "*" + data.get(welcome_character)[
			1] + "    " + data.get(welcome_character)[0] + "*"
		character_message = character_message.replace(
			"author", user.mention)
		channel = client.get_channel(WELCOME_CHANNEL)
		await channel.send(character_message)

########################## LOOPS ###########################################

@tasks.loop(hours=12)
async def daily_role_expiry_check():
	expired = gambling.check_role_expiry()
	print("Role expiry check done at " + helper.unix_to_syd(time.time()))

	if expired == None:
		return

	# Remove expired role if equipped
	for e in expired:
		gensoc_guild = client.get_guild(GENSOC_SERVER)
		user = gensoc_guild.get_member(int(e[0]))
		role = discord.utils.get(gensoc_guild.roles,
								 name=e[1][0].capitalize())
		await user.remove_roles(role, reason="Expired role.")
		print(role.name + " removed from " + user.name)

@tasks.loop(hours=24)
async def make_backup():
	helper.backup_file("users.json")

########################## COMMANDS ########################################

@tree.command(name="send_welcome",
				description="Send first welcome message",
				guild=discord.Object(id=GENSOC_SERVER))
async def send_welcome(interaction):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)

	# Send message and store id
	welcome = await client.get_channel(int(WELCOME_CHANNEL)
										 ).send(WELCOME_MESSAGE)
	data = helper.read_file("config.json")
	data["prev_message"] = welcome.id
	helper.write_file("config.json", data)

@tree.command(name="set_verification",
				description="Set verification channel",
				guild=discord.Object(id=GENSOC_SERVER))
async def set_verification(interaction, verify_channel: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)

	# Set verification channel
	await interaction.response.send_message(
		"Verification channel has been set to " + verify_channel,
		ephemeral=True)
	data = helper.read_file("config.json")
	data['channel'] = int(verify_channel)
	helper.write_file("config.json", data)

################################ UID #################################

@tree.command(name="add_uid",
				description="Add your UID to be easily found",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(game=[
	discord.app_commands.Choice(name="Genshin Impact", value="genshin"),
	discord.app_commands.Choice(name="Honkai Star Rail", value="hsr"),
])
async def add_uid(interaction, game: app_commands.Choice[str], uid: str):
	result = uid_finder.save_uid(str(interaction.user.id), uid, game.value)
	if result == False:
		await interaction.response.send_message("Invalid UID",
												ephemeral=True)
	else:
		await interaction.response.send_message(
			str(uid) + " has been added.")

@tree.command(name="remove_uid",
				description="Remove a UID from our database",
				guild=discord.Object(id=GENSOC_SERVER))
async def remove_uid(interaction, uid: str):
	result = uid_finder.remove_uid(str(interaction.user.id), uid)
	if result == False:
		await interaction.response.send_message("UID cannot be found.",
												ephemeral=True)
	else:
		await interaction.response.send_message(str(uid) +
												" has been removed.",
												ephemeral=True)

@tree.command(name="find_uid",
				description="Find the mentioned user's uid.",
				guild=discord.Object(id=GENSOC_SERVER))
async def find_uid(interaction, target_user: discord.Member):
	result = uid_finder.find_uid(str(target_user.id))
	if result == False:
		await interaction.response.send_message(
			target_user.name + " does not have any uid saved.")
	else:
		await interaction.response.send_message(
			target_user.name + " has the following uid: \n" + result)

@tree.command(name="whose_uid",
				description="Find the owner of an uid",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(game=[
	discord.app_commands.Choice(name="Genshin Impact", value="genshin"),
	discord.app_commands.Choice(name="Honkai Star Rail", value="hsr"),
])
async def reverse_find_uid(interaction, game:app_commands.Choice[str], uid: str):
	if not uid.isnumeric() or int(uid) >= 999999999 or int(uid) <= 0:
		await interaction.response.send_message("Invalid uid.", ephemeral=True)
		return
		
	result = uid_finder.whose_uid(uid, game)
	if result == False:
		await interaction.response.send_message(
			uid + " does not belong to anyone in this server.")
	else:
		owner = await client.fetch_user(int(result))
		await interaction.response.send_message(
			owner.name + " owns the uid " + uid)

@tree.command(name="scrape_uid",
				description="Add all uids from a channel",
				guild=discord.Object(id=GENSOC_SERVER))
async def scrape_uid_message(interaction, channel: int):
	uid_finder.scrape_uid(channel)
	await interaction.response.send_message("Scraping uid in progress.", ephemeral=True)
	

#################################### BETTING ###################################

@tree.command(name="create_bet",
				description="Create a betting bracket. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def start_bet(interaction, bracket_id: str, candidates: str,
					end_time: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	gambling.create_bet(bracket_id, candidates, end_time)
	await interaction.response.send_message(bracket_id +
											" has been created.")

@tree.command(name="payout_bet",
				description="Give earning to bet winners. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def payout_bet(interaction, bracket_id: str, winning_candidate: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	gambling.give_bet_rewards(bracket_id, winning_candidate)
	await interaction.response.send_message("Earnings for " + winning_candidate +
											" bets in bracket " + bracket_id + " has been sent.")

@tree.command(name="bet",
				description="Bet on a candidate for a bracket.",
				guild=discord.Object(id=GENSOC_SERVER))
async def make_bet(interaction, bracket_id: str, candidate: str,
					 amount: int):
	res = gambling.submit_bet(interaction.user.id, bracket_id, candidate,
								amount)
	if res != None:
		await interaction.response.send_message(res, ephemeral=True)
	else:
		await interaction.response.send_message(
			"Successfully made a bet of " + str(amount) + " for " +
			candidate.lower(),
			ephemeral=True)

@tree.command(name="my_bets",
				description="Check your 5 most recent bets.",
				guild=discord.Object(id=GENSOC_SERVER))
async def my_bets(interaction):
	res = gambling.view_own_bets(interaction.user.id)

	embed = discord.Embed(title=interaction.user.name + "\'s recent bets",
							color=0x61dfff)

	# Add embed field for each recent bet
	# Format:
	# bracket_id
	# Candidate: candidate | Amount: amount
	for r in range(0, len(res)):
		embed.add_field(name="ID: " + res[r][0].title(),
						value="Candidate: " + res[r][2].title() +
						" | Amount: " + str(res[r][1]),
						inline=False)

	await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="ongoing_bets",
				description="Check ongoing bets.",
				guild=discord.Object(id=GENSOC_SERVER))
async def ongoing_bets(interaction):
	res = gambling.view_ongoing_bets()

	embed = discord.Embed(title="Ongoing bets", color=0x61dfff)

	# Add embed field for each ongoing bet
	# Format:
	# bracket_id | Ending: end_date
	# candidates
	for r in range(0, len(res)):
		embed.add_field(name="ID: " + res[r][0].title() + " | Current Prize Pool: " + str(res[r][3]) + " | Ending: " + res[r][2],
						value=res[r][1],
						inline=False)

	await interaction.response.send_message(embed=embed)

################################ CURRENCY ###########################################

@tree.command(name="checkin",
				description="Obtain primojem for daily check in.",
				guild=discord.Object(id=GENSOC_SERVER))
async def checkin(interaction):
	res = gambling.currency_checkin(interaction.user.id)
	if res == None:
		await interaction.response.send_message(
			"Check in is still in cooldown. Try again tomorrow at 12am (UTC 0).",
			ephemeral=True)
	else:
		await interaction.response.send_message(
			"You got " + str(res[0]) +
			" primojems from the check in. Current streak: " +
			str(res[1]) + ".")

@tree.command(name="inventory",
				description="Check your primojem, jemdust and owned roles.",
				guild=discord.Object(id=GENSOC_SERVER))
async def inventory(interaction):
	res = gambling.get_inventory(interaction.user.id)

	embed = discord.Embed(title=interaction.user.name + "\'s inventory",
							description=str(res[0]) + " " + PRIMOJEM_EMOTE + "  |  " + 
						  		str(res[1]) + " " + JEMDUST_EMOTE,
							color=0x61dfff)

	# Add embed field for each roles
	for r in res[2]:
		embed.add_field(name=r[0].capitalize(),
						value=r[1],
						inline=False)
	
	if len(res[3]) != 0:
		embed.add_field(name="Role Icons",
							value=res[3],
							inline=False)

	await interaction.response.send_message(embed=embed)

@tree.command(name="shop",
				description="View role shop.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(shop=[
	discord.app_commands.Choice(name="Primojem/Role Shop", value="primojem"),
	discord.app_commands.Choice(name="Jemdust/Role Icon Shop", value="jemdust"),
])
async def view_shop(interaction, shop: app_commands.Choice[str]):
	res = gambling.get_inventory(interaction.user.id)
	gacha_pool = helper.read_file("role_icon.json")

	price = [1500, 4500, 30000, 160]
	if helper.is_booster(interaction.user):
		price = [int(x / 2) for x in price]

	description = ""
	if shop.value == "primojem":
		description = ("7 days: " + str(price[0]) + " " + PRIMOJEM_EMOTE + "  |  " +
			"30 day: " + str(price[1]) + " " + PRIMOJEM_EMOTE + "  |  " +
			"Permanent: " + str(price[2]) + " " + PRIMOJEM_EMOTE + "\n" +
			"1 pull: " + str(price[3]) + " " + PRIMOJEM_EMOTE + "\n" + 
			"Use **/shop jemdust** to see the role icons shop.\n" + 
			"Use **/gacha** to pull for role icons.\n\n")
	elif shop.value == "jemdust":
		description = ("5 star role icon: 180 " + JEMDUST_EMOTE + "  |  " +
			"4 star role icon: 34 " + JEMDUST_EMOTE + "\n")

	embed = discord.Embed(title="Shop",
							description=description,
							color=0x61dfff)
	embed.set_footer(text="Primojems: " + str(res[0]) + "  |  " + "Jemdust: " + str(res[1]))
	
	# Add embed field for each role
	if shop.value == "primojem":
		embed.add_field(name="Abyss", value="Colour = gray", inline=False)
		embed.add_field(name="Anemo", value="Colour = teal", inline=False)
		embed.add_field(name="Cryo", value="Colour = whitish blue", inline=False)
		embed.add_field(name="Dendro", value="Colour = green", inline=False)
		embed.add_field(name="Electro", value="Colour = magenta", inline=False)
		embed.add_field(name="Geo", value="Colour = yellow", inline=False)
		embed.add_field(name="Hydro", value="Colour = blue", inline=False)
		embed.add_field(name="Pyro", value="Colour = red", inline=False)
	elif shop.value == "jemdust":
		embed.add_field(name="5 Star Role Icons", value=", ".join(gacha_pool["5"]), inline=False)
		embed.add_field(name="4 Star Role Icons", value=", ".join(gacha_pool["4"]), inline=False)

	await interaction.response.send_message(embed=embed)

@tree.command(name="buy",
				description="Buy item from shop.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(duration=[
	discord.app_commands.Choice(name="7 days", value=7),
	discord.app_commands.Choice(name="30 days", value=30),
	discord.app_commands.Choice(name="Permanent role", value=5000)
])
async def buy_item(interaction, item_name: str, duration: app_commands.Choice[int]):
	booster = helper.is_booster(interaction.user)
	res = gambling.buy_role(interaction.user.id, item_name, duration.value, booster)

	if res != None:
		await interaction.response.send_message(res, ephemeral=True)
	elif duration == None or duration == 5000:
		await interaction.response.send_message(
			"Successfully bought " + item_name.title() + " role. Use **/equip** to use the role.")
	else:
		await interaction.response.send_message(
			"Successfully bought " + item_name.title() + " role for " +
			str(duration.value) + " days. Use **/equip** to use the role.")

@tree.command(name="equip",
				description="Equip or unequip an owned role.",
				guild=discord.Object(id=GENSOC_SERVER))
async def equip_role(interaction, role_name: str):
	if gambling.is_role_owned(interaction.user.id, role_name):
		role = discord.utils.get(interaction.guild.roles,
								 name=role_name.capitalize())

		# Check if role is equipped already
		if role in interaction.user.roles:
			# Unequip role
			await interaction.user.remove_roles(
				role, reason="Unequip shop role.")
			await interaction.response.send_message(
				"You have unequipped " + role_name.lower() + ".")
		else:
			# Equip role
			await interaction.user.add_roles(role,
											 reason="Equip shop role.")
			await interaction.response.send_message("You have equipped " +
													role_name.lower() +
													".")

	else:
		await interaction.response.send_message(
			"Invalid role or you do not own the role.")

@tree.command(name="leaderboard",
				description="Primojem leaderboard.",
				guild=discord.Object(id=GENSOC_SERVER))
async def leaderboard(interaction):
	res = gambling.get_leaderboard()
	
	embed = discord.Embed(title="Leaderboard", color=0x61dfff)
	
	# Add embed field for each person in top 10
	rank = 0
	for r in range(0, len(res)):
		user = client.get_user(int(res[r][0]))
		if user == None:
			continue
		if r < 10:
			embed.add_field(name=str(r + 1) + ". " + user.name,
							value=str(res[r][1]),
							inline=False)
		if user.id == interaction.user.id:
			rank = r + 1
	
	embed.set_footer(text="Your rank: " + str(rank))
	
	await interaction.response.send_message(embed=embed)

@tree.command(
	name="payout_attendance",
	description="Give primojems to list of attendees. Admin only.",
	guild=discord.Object(id=GENSOC_SERVER))
async def payout_attendance(interaction, attendee_list: str, amount: int):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	res = gambling.update_user_list_currency(attendee_list, amount,
											 interaction.guild)
	await interaction.response.send_message(
		str(amount) + " given to these users: " + ", ".join(res),
		ephemeral=True)

################### MINIGAMES ####################################################

@tree.command(
	name="coinflip",
	description=
	"Flip a number of coins and guess how many will land on head.",
	guild=discord.Object(id=GENSOC_SERVER))
async def flip(interaction, coin_amount: int, head_amount: int, bet: int):
	res = minigame.coinflip(interaction.user.id, coin_amount, head_amount,
							bet)

	if isinstance(res, str):
		await interaction.response.send_message(res)
		return

	description = str(res[0].count("H")) + " heads. "
	if res[1] == 0:
		description += "You have lost the bet.\n\n"
	else:
		description += "You have won " + str(res[1]) + " primojems.\n\n"

	flip_string = " ".join(res[0])
	description += flip_string

	embed = discord.Embed(title=interaction.user.name + "\'s Coinflip",
							description=description,
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.avatar.url)

	await interaction.response.send_message(embed=embed)

@tree.command(
	name="blackjack",
	description="Play blackjack with primojems. You can specify \'all\'",
	guild=discord.Object(id=GENSOC_SERVER))
async def blackjack(interaction, bet: str):
	if "all" in bet:
		bet = helper.get_user_entry(interaction.user.id)["currency"]
		
	res = minigame.new_blackjack(interaction.user.id, int(bet))

	if isinstance(res, str):
		await interaction.response.send_message(res)
		return

	embed = discord.Embed(
		title=interaction.user.name + "\'s Blackjack Game",
		description="Use **/hit** or **/stand**\n" + res[0],
		color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.avatar.url)

	dealer_value = str(minigame.blackjack_get_value(res[1]))
	better_value = str(minigame.blackjack_get_value(res[2]))
	embed.add_field(name="Dealer's Hand: " + dealer_value,
					value=", ".join(res[1]),
					inline=False)
	embed.add_field(name="Your Hand: " + better_value,
					value=", ".join(res[2]),
					inline=False)

	await interaction.response.send_message(embed=embed)

@tree.command(name="hit",
				description="Hit in blackjack.",
				guild=discord.Object(id=GENSOC_SERVER))
async def hit(interaction):
	res = minigame.blackjack_action(interaction.user.id, "hit")

	if isinstance(res, str):
		await interaction.response.send_message(res)
		return

	embed = discord.Embed(title=interaction.user.name +
							"\'s Blackjack Game",
							description=res[0],
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.avatar.url)

	dealer_value = str(minigame.blackjack_get_value(res[1]))
	better_value = str(minigame.blackjack_get_value(res[2]))
	embed.add_field(name="Dealer's Hand: " + dealer_value,
					value=", ".join(res[1]),
					inline=False)
	embed.add_field(name="Your Hand: " + better_value,
					value=", ".join(res[2]),
					inline=False)

	await interaction.response.send_message(embed=embed)

@tree.command(name="stand",
				description="Stand in blackjack.",
				guild=discord.Object(id=GENSOC_SERVER))
async def stand(interaction):
	res = minigame.blackjack_action(interaction.user.id, "stand")

	if isinstance(res, str):
		await interaction.response.send_message(res)
		return

	embed = discord.Embed(title=interaction.user.name +
							"\'s Blackjack Game",
							description=res[0],
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.avatar.url)

	dealer_value = str(minigame.blackjack_get_value(res[1]))
	better_value = str(minigame.blackjack_get_value(res[2]))
	embed.add_field(name="Dealer's Hand: " + dealer_value,
					value=", ".join(res[1]),
					inline=False)
	embed.add_field(name="Your Hand: " + better_value,
					value=", ".join(res[2]),
					inline=False)

	await interaction.response.send_message(embed=embed)

@tree.command(
	name="hangman",
	description=
	"Play hangman at Normal (9 lives), Hard (6 lives), or Extreme (3 lives) difficulty.",
	guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(difficulty=[
	discord.app_commands.Choice(name="Normal", value="normal"),
	discord.app_commands.Choice(name="Hard", value="hard"),
	discord.app_commands.Choice(name="Extreme", value="extreme"),
])
async def hangman(interaction, difficulty: app_commands.Choice[str]):
	res = minigame.new_hangman(interaction.user.id, difficulty.value)
	if res[0] == -1:
		await interaction.response.send_message(res[1][0])
	else:
		embed = discord.Embed(
			title=interaction.user.name + "\'s Hangman Game",
			description="Use **/guess [letter]**\n",
			color=0x61dfff)
		embed.set_thumbnail(url=interaction.user.avatar.url)
		embed.add_field(name="Hint: ", value=res[1][0], inline=True)
		embed.add_field(name="Difficulty: ", value=res[1][1], inline=True)
		embed.add_field(name="Lives: ", value=res[1][2], inline=True)
		await interaction.response.send_message(embed=embed)

@tree.command(name="guess",
				description="Guess in hangman. Accepts either one character or the whole word.",
				guild=discord.Object(id=GENSOC_SERVER))
async def hangman_guess(interaction, guess: str):
	res = minigame.hangman_guess(interaction.user.id, guess)
	if res[0] == -1:
		await interaction.response.send_message(res[1][0])
	elif res[0] == -2:
		await interaction.response.send_message(res[1][0] + "\n" +
												res[1][1])
	elif res[0] == 0:
		embed = discord.Embed(title=interaction.user.name +
								"\'s Hangman Game",
								description=res[1][0],
								color=0x61dfff)
		embed.set_thumbnail(url=interaction.user.avatar.url)
		embed.add_field(name="Your word was: ",
						value=res[1][1],
						inline=True)
		await interaction.response.send_message(embed=embed)
	elif res[0] == 1:
		embed = discord.Embed(title=interaction.user.name +
								"\'s Hangman Game",
								description=res[1][0],
								color=0x61dfff)
		embed.set_thumbnail(url=interaction.user.avatar.url)
		embed.add_field(name="Hint: ",
						value=res[1][1],
						inline=True)
		embed.add_field(name="Incorrect letters: ",
						value=res[1][2],
						inline=True)
		embed.add_field(name="Lives: ", value=res[1][3], inline=True)
		await interaction.response.send_message(embed=embed)
	else:  #res[0] == 2
		embed = discord.Embed(title=interaction.user.name +
								"\'s Hangman Game",
								description=res[1][0],
								color=0x61dfff)
		embed.set_thumbnail(url=interaction.user.avatar.url)
		embed.add_field(name="Your word was: ",
						value=res[1][1],
						inline=True)
		embed.add_field(name="Lives: ", value=res[1][3], inline=True)
		embed.add_field(name=res[1][4], value="", inline=True)
		await interaction.response.send_message(embed=embed)

################### GACHA ####################################################

@tree.command(name="gacha",
				description="Gacha for role icons. Max 10 pulls per multi.",
				guild=discord.Object(id=GENSOC_SERVER))
async def role_icon_gacha(interaction, pull_amount: int):
	booster = helper.is_booster(interaction.user)
	res = gambling.gacha(interaction.user.id, pull_amount, booster)

	if isinstance(res, str):
		await interaction.response.send_message(res, ephemeral=True)
		return

	embed = discord.Embed(title=interaction.user.name + "'s Gacha",
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.avatar.url)
	
	# Add embed field for each gacha result item
	for item in res:
		embed.add_field(name=item[0], value=item[1], inline=False)

	await interaction.response.send_message(embed=embed)

'''
@tree.command(name="salvage",
				description="Salvage a role icon for jemdust",
				guild=discord.Object(id=GENSOC_SERVER))
async def salvage_role(interaction, role: str):
	res = gambling.scrap_role_icon(interaction.user.id, role)

	if res == None:
		await interaction.response.send_message("Invalid or you do not own this role.", ephemeral=True)
	else:
		# Unequip the salvaged role
		role_obj = discord.utils.get(interaction.guild.roles, name=role.title())
		if role_obj in interaction.user.roles:
			await interaction.user.remove_roles(role_obj, reason="Salvaged role.")
		
		await interaction.response.send_message("Successfully salvaged " + role.title() + " role for " + 
													str(res) + " " + JEMDUST_EMOTE)
'''



# keep_alive()
# token = os.environ.get("TOKEN")
load_dotenv()
token = os.getenv("TOKEN")
client.run(token)
