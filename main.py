import discord
from discord.ext import tasks
from discord import app_commands
from discord.ui import Button, View
from dotenv import load_dotenv
import os
import json
import random
import time
import DiscordUtils

import helper
import uid_finder
import gambling
import minigame
import followup
# from keep_alive import keep_alive

# IMPORTANT: Replit code is using a test bot on the test server. Before committing please change GENSOC_SERVER back to actual server's id

############################ CONSTANTS ###################################
WELCOME_MESSAGE = "Welcome traveller! <:GuobaWave:895891227067711548> Remember to fill out the verification form to gain access to the server. \n Enjoy your stay at GenSoc and feel free to chuck an intro in <#822732136515764265> and grab your roles from <#827393050299858965>."

# Read json file for config
absolute_path = os.path.dirname(os.path.abspath(__file__)) + "/json_files/"
with open(absolute_path + 'config.json', 'r') as f:
	data = json.load(f)
	GENSOC_SERVER = data['gensoc_server']
	VERIFICATION_CHANNEL = data['verification_channel']
	THIS_OR_THAT_CHANNEL = data['this_or_that_channel']
	COUNTING_CHANNEL = data['counting_channel']
	AUCTION_CHANNEL = data['auction_channel']
	WELCOME_CHANNEL = data['welcome_channel']
	ROLE_ICON_PREVIEW = data['role_icon_shop']
	COLOUR_ROLE_PREVIEW = data['role_colour_shop']
	
	f.close()

# NOTICE: Uncomment these two if testing on the test server
# GENSOC_SERVER = 962970271545982986 # Test server
# THIS_OR_THAT_CHANNEL = 1122138125368569868 # Test server channel
# AUCTION_CHANNEL = 1134351976738603058

CHAT_INTERVAL = 300 # 5 minute cooldown for chat primojem
CHAT_PRIMOJEM = 50

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
	run_scheduled_tasks.start()

@client.event
async def on_message(message):
	global VERIFICATION_CHANNEL
	global WELCOME_CHANNEL
	global WELCOME_MESSAGE

	####### This section deals with chat primojems ########################
	if not message.author.bot:
		data = helper.read_file("users.json")
		helper.get_user_entry(str(message.author.id))
		user_entry = data.get(str(message.author.id), None)

		if time.time() > user_entry["chat_cooldown"]:
			user_entry["chat_cooldown"] = int(time.time() + CHAT_INTERVAL)
			helper.write_file("users.json", data)
			gambling.update_user_currency(str(message.author.id), CHAT_PRIMOJEM)
			
	####### This section deals with sticky note ###########################
	if (message.channel.id == WELCOME_CHANNEL and not message.author.bot):
		welcome = await message.channel.send(WELCOME_MESSAGE)

		data = helper.read_file("config.json")
		channel = client.get_channel(WELCOME_CHANNEL)
		old_welcome = await channel.fetch_message(data["prev_welcome_message"])
		await old_welcome.delete()

		data["prev_welcome_message"] = welcome.id
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

	##### This section deals with the counting game #######################
	if (message.channel.id == COUNTING_CHANNEL and not message.author.bot):
			res = minigame.number_validity(message)
			if res == True:
				await message.add_reaction(helper.PRIMOJEM_EMOTE)
			
			if isinstance(res, str):
				channel = client.get_channel(COUNTING_CHANNEL)
				await channel.send(res)


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
		print(role.name + " removed from " + user.display_name)

@tasks.loop(hours=24)
async def make_backup():
	helper.backup_file("users.json")

@tasks.loop(minutes=1)
async def run_scheduled_tasks():
	data = helper.read_file("tasks.json")

	# Run any task that is past the time and delete it after
	update_task_file = False
	task_copy = list(data)
	
	for task in task_copy:
		if task["time"] <= time.time():
			if task["type"] == "vote":
				# Auto payout task
				channel = client.get_channel(THIS_OR_THAT_CHANNEL)
				vote_message = await channel.fetch_message(task["message_id"])
				res = gambling.auto_payout_bet(task["bracket_id"], vote_message.reactions)
				if res != None:
					await channel.send(str(res[0]) + helper.PRIMOJEM_EMOTE + 
								" has been distributed amongst " + str(res[1]) + 
								" betters who chose **" + res[3] + 
								"** for **" + res[2] + "**.")
				data.remove(task)
				update_task_file = True

	if update_task_file:
		helper.write_file("tasks.json", data)
				

########################## COMMANDS ########################################

@tree.command(name="send_welcome",
				description="Send first welcome message. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def send_welcome(interaction):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	# Send message and store id
	welcome = await client.get_channel(int(WELCOME_CHANNEL)
										 ).send(WELCOME_MESSAGE)
	data = helper.read_file("config.json")
	data["prev_welcome_message"] = welcome.id
	helper.write_file("config.json", data)

@tree.command(name="set_verification",
				description="Set verification channel. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def set_verification(interaction, verify_channel: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	# Set verification channel
	await interaction.response.send_message(
		"Verification channel has been set to " + verify_channel,
		ephemeral=True)
	data = helper.read_file("config.json")
	data['channel'] = int(verify_channel)
	helper.write_file("config.json", data)

@tree.command(name="view_tasks",
				description="View all scheduled tasks.",
				guild=discord.Object(id=GENSOC_SERVER))
async def view_tasks(interaction):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	embed = discord.Embed(title="Scheduled Tasks", color=0x61dff)
	tasks = helper.list_tasks()
	for t in tasks:
		embed.add_field(name=t[0], value=t[1], inline=False)

	await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="set_count",
				description="Set counting game current number.",
				guild=discord.Object(id=GENSOC_SERVER))
async def set_count(interaction, number: int):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	data = helper.read_file("minigame_session.json")
	session = data.get("1", None)
	session["next_valid_number"] = number + 1
	session["last_user"] = 1
	helper.write_file("minigame_session.json", data)

	await interaction.response.send_message("Count has been set to " + str(number))
	

@tree.command(name="help",
				description="View all available bot commands.",
				guild=discord.Object(id=GENSOC_SERVER))
async def help_commands(interaction):
	embed_general = discord.Embed(title="General Commands", color=0x61dff)
	embed_general.set_footer(text="Page 1/4")
	embed_primojem = discord.Embed(title="Primojem Commands", color=0x61dff)
	embed_primojem.set_footer(text="Page 2/4")
	embed_minigame = discord.Embed(title="Minigame Commands", color=0x61dff)
	embed_minigame.set_footer(text="Page 3/4")
	embed_poll = discord.Embed(title="Betting Commands", color=0x61dff)
	embed_poll.set_footer(text="Page 4/4")
	
	paginator = DiscordUtils.Pagination.AutoEmbedPaginator(interaction)
	
	embed_primojem.add_field(name="**/checkin**", value="Daily free primojems.", inline=False)
	embed_primojem.add_field(name="**/leaderboard**", value="See top 10 primojem earners and your own rank.", inline=False)
	embed_primojem.add_field(name="**/shop**", value="See which roles and role icons you can buy.", inline=False)
	embed_primojem.add_field(name="**/buy**", value="Buy a role from the shop.", inline=False)
	embed_primojem.add_field(name="**/equip**", value="Equip or unequip a role.", inline=False)
	embed_primojem.add_field(name="**/inventory**", value="Check primojem, jemdust and owned roles.", inline=False)
	embed_primojem.add_field(name="**/salvage**", value="Sell a role icon for jemdust.", inline=False)
	
	embed_minigame.add_field(name="**/blackjack**", value="Play blackjack.", inline=False)
	embed_minigame.add_field(name="**/hangman**", value="Play hangman.", inline=False)
	embed_minigame.add_field(name="**/coinflip**", value="Play heads or tails.", inline=False)
	embed_minigame.add_field(name="**/connect4**", value="Play connect 4.", inline=False)
	embed_minigame.add_field(name="**/gacha**", value="Gacha for role icons.", inline=False)
	
	embed_poll.add_field(name="**/bet**", value="Make a bet on this-or-that bracket.", inline=False)
	embed_poll.add_field(name="**/ongoing_bets**", value="See the bracket id of ongoing bets.", inline=False)
	embed_poll.add_field(name="**/my_bets**", value="See which brackets you have betted on.", inline=False)
	embed_poll.add_field(name="**/bid**", value="Bid on an auction.", inline=False)
	embed_poll.add_field(name="**/auction_info**", value="Get info about an auction.", inline=False)
	
	embed_general.add_field(name="**/add_uid**", value="Add UID to bot database.", inline=False)
	embed_general.add_field(name="**/remove_uid**", value="Remove UID from bot database.", inline=False)
	embed_general.add_field(name="**/find_uid**", value="List all UIDs of an user.", inline=False)
	embed_general.add_field(name="**/whose_uid**", value="Find the owner of an UID.", inline=False)

	# await interaction.response.defer()
	embeds = [embed_general, embed_primojem, embed_minigame, embed_poll]
	await paginator.run(embeds)
	

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
			target_user.display_name + " does not have any uid saved.")
	else:
		await interaction.response.send_message(
			"**" + target_user.display_name + " has the following uid** \n" + result)

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
			owner.display_name + " owns the uid " + uid)

@tree.command(name="scrape_uid",
				description="Add all uids from a channel. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def scrape_uid_message(interaction, channel_id: str, game: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return
		
	channel = client.get_channel(int(channel_id))
	res = await uid_finder.scrape_uid(channel, game)
	if res == False:
			await interaction.response.send_message("Scraping failed", ephemeral=True)
	else:
		await interaction.response.send_message("Scraping finished.", ephemeral=True)
	

#################################### BETTING ###################################

@tree.command(name="create_bet",
				description="Create a betting bracket. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def start_bet(interaction, bracket_id: str, candidates: str, end_time: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	gambling.create_bet(bracket_id, candidates, end_time)
	await interaction.response.send_message(bracket_id + " has been created.", ephemeral=True)

@tree.command(name="payout_bet",
				description="Give earning to bet winners. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def payout_bet(interaction, bracket_id: str, winning_candidate: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	res = gambling.give_bet_rewards(bracket_id, winning_candidate)
	await interaction.response.send_message(str(res[0]) + helper.PRIMOJEM_EMOTE + 
											" has been distributed amongst " + str(res[1]) + 
										   	" betters who chose **" + winning_candidate + 
											"** for **" + bracket_id + "**.")

@tree.command(name="bet",
				description="Bet on a candidate for a bracket.",
				guild=discord.Object(id=GENSOC_SERVER))
async def make_bet(interaction, bracket_id: str, candidate: str, amount: int):
	res = gambling.submit_bet(interaction.user.id, bracket_id, candidate,
								amount)
	if isinstance(res, str):
		await interaction.response.send_message(res, ephemeral=True)
	else:
		if res[0] != None:
			channel = client.get_channel(THIS_OR_THAT_CHANNEL)
			bet_message = await channel.fetch_message(int(res[0]))
			await bet_message.edit(embed=res[1])
		
		await interaction.response.send_message(
			"Successfully made a bet of " + str(amount) + " for " + candidate.lower(), ephemeral=True)
		

@tree.command(name="my_bets",
				description="Check your 5 most recent bets.",
				guild=discord.Object(id=GENSOC_SERVER))
async def my_bets(interaction):
	res = gambling.view_own_bets(interaction.user.id)

	embed = discord.Embed(title=interaction.user.display_name + "\'s recent bets",
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

	embed = discord.Embed(title="Ongoing Bets", color=0x61dfff)

	# Add embed field for each ongoing bet
	# Format:
	# bracket_id | Ending: end_date
	# candidates
	for r in range(0, len(res)):
		embed.add_field(name="ID: " + res[r][0].title() + " | Current Prize Pool: " + str(res[r][3]) + " | Ending: " + res[r][2],
						value=res[r][1],
						inline=False)

	await interaction.response.send_message(embed=embed)

@tree.command(name="send_bet_info",
				description="Create a bet live update message. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def send_bet_message(interaction, bracket_id: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return
	
	res = gambling.create_bet_message(bracket_id)
	await interaction.response.send_message(embed=res[1])
	message = await interaction.original_response()
	gambling.set_bet_message(bracket_id, message.id)

@tree.command(name="auto_payout",
				description="Schedule auto bet payout based on vote. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def schedule_payout(interaction, message_id: str, bracket_id: str, end_time: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.", ephemeral=True)
		return

	res = gambling.add_auto_payout_bet(message_id, bracket_id, end_time)
	if res != None:
		await interaction.response.send_message(res, ephemeral=True)
	else:
		await interaction.response.send_message("Successfully scheduled auto payout for " + bracket_id,
											   ephemeral=True)



#################################### AUCTION ###################################

@tree.command(name="create_auction",
				description="Start an auction. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def start_auction(interaction, auction_name: str, end_time: str, auction_description: str):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	gambling.create_auction(auction_name, end_time, auction_description)
	await interaction.response.send_message(auction_name + " has been created.", ephemeral=True)

@tree.command(name="bid",
				description="Bid on an auction.",
				guild=discord.Object(id=GENSOC_SERVER))
async def make_bid(interaction, auction_name: str, amount: int):
	res = gambling.submit_bid(interaction.user, auction_name, amount)
	if isinstance(res, str):
		await interaction.response.send_message(res, ephemeral=True)
	else:
		if res[0] != None:
			channel = client.get_channel(AUCTION_CHANNEL)
			auction_message = await channel.fetch_message(int(res[0]))
			res[1].set_thumbnail(url=interaction.user.display_avatar.url)
			await auction_message.edit(embed=res[1])

		response_message = "Successfully made a bid of " + str(amount) + " for " + auction_name + "."
		if res[3] != str(interaction.user.id):
			# Ping previous bidder that they have been outbid
			response_message += "\n\n<@" + res[3] + ">" + " you have been outbid by " + interaction.user.display_name
		
		await interaction.response.send_message(response_message)

@tree.command(name="auction_info",
				description="Get info about an auction.",
				guild=discord.Object(id=GENSOC_SERVER))
async def send_auction_info(interaction, auction_name: str):
	res = gambling.create_auction_message(auction_name)
	user = client.get_user(int(res[2]))
	res[1].set_thumbnail(url=user.display_avatar.url)
	await interaction.response.send_message(embed=res[1])
	
	if helper.is_team(interaction):
		# Only update auction message id if gensoc team uses this command
		message = await interaction.original_response()
		gambling.set_auction_message(auction_name, message.id)


################################ CURRENCY ###########################################

@tree.command(name="checkin",
				description="Obtain primojem for daily check-in.",
				guild=discord.Object(id=GENSOC_SERVER))
async def checkin(interaction):
	res = gambling.currency_checkin(interaction.user.id)
	if res == None:
		await interaction.response.send_message(
			"Check-in is still in cooldown. Try again tomorrow at 12am (UTC +10).",
			ephemeral=True)
	else:
		await interaction.response.send_message(
			"You got " + str(res[0]) +
			" primojems from the check-in. Current streak: " +
			str(res[1]) + ".")

@tree.command(name="inventory",
				description="Check your primojem, jemdust and owned roles.",
				guild=discord.Object(id=GENSOC_SERVER))
async def inventory(interaction):
	res = gambling.get_inventory(interaction.user.id)

	embed = discord.Embed(title=interaction.user.display_name + "\'s inventory",
							description=str(res[0]) + " " + helper.PRIMOJEM_EMOTE + "  |  " + 
						  		str(res[1]) + " " + helper.JEMDUST_EMOTE,
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

	price = [gambling.ONE_WEEK_ROLE, gambling.PERMANENT_ROLE, gambling.ONE_PULL]
	if helper.is_booster(interaction.user):
		price = [int(x / 2) for x in price]

	description = ""
	if shop.value == "primojem":
		description = ("7 days: " + str(price[0]) + " " + helper.PRIMOJEM_EMOTE + "  |  " +
			"Permanent: " + str(price[1]) + " " + helper.PRIMOJEM_EMOTE + "\n" +
			"1 pull: " + str(price[2]) + " " + helper.PRIMOJEM_EMOTE + "\n" + 
			"Use **/shop jemdust** to see the role icons shop.\n" + 
			"Use **/gacha** to pull for role icons.\n\n")
	elif shop.value == "jemdust":
		description = ("5 star role icon: 180 " + helper.JEMDUST_EMOTE + "  |  " +
			"4 star role icon: 34 " + helper.JEMDUST_EMOTE + "\n")

	embed = discord.Embed(title="Shop",
							description=description,
							color=0x61dfff)
	embed.set_footer(text="Primojems: " + str(res[0]) + "  |  " + "Jemdust: " + str(res[1]))
	
	# Add embed field for each role
	if shop.value == "primojem":
		embed.add_field(name="Anemo", value="(teal)", inline=True)
		embed.add_field(name="Cryo", value="(whitish blue)", inline=True)
		embed.add_field(name="Dendro", value="(green)", inline=True)
		embed.add_field(name="Electro", value="(dark pink)", inline=True)
		embed.add_field(name="Geo", value="(orange)", inline=True)
		embed.add_field(name="Hydro", value="(blue)", inline=True)
		embed.add_field(name="Pyro", value="(red)", inline=True)
		embed.add_field(name="Physical", value="(gray)", inline=True)
		embed.add_field(name="Imaginary", value="(yellow)", inline=True)
		embed.add_field(name="Quantum", value="(indigo)", inline=True)
		embed.set_image(url=COLOUR_ROLE_PREVIEW)
		
	elif shop.value == "jemdust":
		embed.add_field(name="5 Star Role Icons", value=", ".join(gacha_pool["5"]), inline=False)
		embed.add_field(name="4 Star Role Icons", value=", ".join(gacha_pool["4"]), inline=False)
		embed.set_image(url=ROLE_ICON_PREVIEW)

	await interaction.response.send_message(embed=embed)

@tree.command(name="buy",
				description="Buy item from shop.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(duration=[
	discord.app_commands.Choice(name="7 days", value=7),
	discord.app_commands.Choice(name="Permanent role", value=5000)
])
async def buy_item(interaction, item_name: str, duration: app_commands.Choice[int], gift_recipient: discord.Member = None):
	booster = helper.is_booster(interaction.user)
	res = gambling.buy_role(interaction.user.id, item_name, duration.value, booster, gift_recipient)

	if res != None:
		await interaction.response.send_message(res, ephemeral=True)
	elif gift_recipient != None:
		await interaction.response.send_message(
			"<@" + str(gift_recipient.id) + "> has been gifted the " + item_name.title() + " role.")
	elif duration.value == 5000:
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
								 name=role_name.title())

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
@app_commands.choices(category=[
	discord.app_commands.Choice(name="Primojem", value="currency"),
	discord.app_commands.Choice(name="Gambling Profit", value="gambling_profit"),
	discord.app_commands.Choice(name="Gambling Loss", value="gambling_loss"),
])
async def leaderboard(interaction, category: app_commands.Choice[str]):
	res = gambling.get_leaderboard(category.value)
	
	embed = discord.Embed(title=category.name + " Leaderboard", color=0x61dfff)
	
	# Add embed field for each person in top 10
	rank = 0
	for r in range(0, len(res)):
		user = client.get_user(int(res[r][0]))
		if user == None:
			continue
			
		if r < 10:
			embed.add_field(name=str(r + 1) + ". " + user.display_name,
							value=str(res[r][1]),
							inline=False)
		if user.id == interaction.user.id:
			rank = r + 1
	
	embed.set_footer(text="Your rank: " + str(rank))
	
	await interaction.response.send_message(embed=embed)

@tree.command(
	name="give_primojems",
	description="Give primojems to list of people. Admin only.",
	guild=discord.Object(id=GENSOC_SERVER))
async def give_primojem(interaction, attendee_list: str, amount: int):
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
async def flip(interaction, coin_amount: int, head_amount: int, bet: str):
	if "all" in bet:
		bet = helper.get_user_entry(interaction.user.id)["currency"]
		
	res = minigame.coinflip(interaction.user.id, coin_amount, head_amount, int(bet))

	if isinstance(res, str):
		await interaction.response.send_message(res)
		return

	description = ""
	if res[1] == 0:
		description += "You have lost the bet.\n\n"
	else:
		description += "You have won " + str(res[1]) + " primojems.\n\n"

	embed = discord.Embed(title=interaction.user.display_name + "\'s Coinflip",
							description=description,
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.display_avatar.url)
	
	emote_string = [helper.HEADS_EMOTE if item == "H" else helper.TAILS_EMOTE for item in res[0]]
	embed.add_field(name=str(res[0].count("H")) + " Heads", value=" ".join(emote_string), )

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
		title=interaction.user.display_name + "\'s Blackjack Game",
		description="Use **/hit** or **/stand**\n" + res[0],
		color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.display_avatar.url)

	dealer_value = str(minigame.blackjack_get_value(res[1]))
	better_value = str(minigame.blackjack_get_value(res[2]))
	embed.add_field(name="Dealer's Hand: " + dealer_value,
					value=", ".join(res[1]),
					inline=False)
	embed.add_field(name="Your Hand: " + better_value,
					value=", ".join(res[2]),
					inline=False)

	# Buttons
	view = View(timeout=60)

	# Hit button
	hit_button = Button(label="Hit", style=discord.ButtonStyle.blurple)
	async def hit_callback(b_interaction):
		if b_interaction.user.id == interaction.user.id:
			await b_interaction.response.defer()
			await followup.hit_followup(interaction)
	hit_button.callback = hit_callback
	view.add_item(hit_button)

	# Stand button
	stand_button = Button(label="Stand", style=discord.ButtonStyle.red)
	async def stand_callback(b_interaction):
		if b_interaction.user.id == interaction.user.id:
			await b_interaction.response.defer()
			await followup.stand_followup(interaction)
	stand_button.callback = stand_callback
	view.add_item(stand_button)

	await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="hit",
				description="Hit in blackjack.",
				guild=discord.Object(id=GENSOC_SERVER))
async def hit(interaction):
	res = minigame.blackjack_action(interaction.user.id, "hit")

	if isinstance(res, str):
		await interaction.response.send_message(res)
		return

	embed = discord.Embed(title=interaction.user.display_name +
							"\'s Blackjack Game",
							description=res[0],
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.display_avatar.url)

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

	embed = discord.Embed(title=interaction.user.display_name +
							"\'s Blackjack Game",
							description=res[0],
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.display_avatar.url)

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
	"Play hangman at normal (9 lives), hard (6 lives), or extreme (3 lives) difficulty.",
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
			title=interaction.user.display_name + "\'s Hangman Game",
			description="Use **/guess [letter]**\n",
			color=0x61dfff)
		embed.set_thumbnail(url=interaction.user.display_avatar.url)
		embed.add_field(name="Hint: ", value=res[1][0], inline=True)
		embed.add_field(name="Difficulty: ", value=res[1][1], inline=True)
		embed.add_field(name="Lives: ", value=res[1][2], inline=True)
		await interaction.response.send_message(embed=embed)

		# Save interaction response message id
		data = helper.read_file("minigame_session.json")
		response_message = await interaction.original_response()
		data[str(interaction.user.id)]["message_id"] = response_message.id
		helper.write_file("minigame_session.json", data)

@tree.command(name="guess",
				description="Guess in hangman. Accepts either one character or the whole word.",
				guild=discord.Object(id=GENSOC_SERVER))
async def hangman_guess(interaction, guess: str):
	# Delete previous hangman message
	data = helper.read_file("minigame_session.json")
	user_session = data.get(str(interaction.user.id), None)
	if user_session != None:
		try:
			previous_message = await interaction.channel.fetch_message(user_session["message_id"])
			await previous_message.delete()
		except: 
			pass
		
	res = minigame.hangman_guess(interaction.user.id, guess)
	
	if res[0] == -1:
		await interaction.response.send_message(res[1][0])
	elif res[0] == -2:
		await interaction.response.send_message(res[1][0] + "\n" +
												res[1][1])
	elif res[0] == 0:
		embed = discord.Embed(title=interaction.user.display_name +
								"\'s Hangman Game",
								description=res[1][0],
								color=0x61dfff)
		embed.set_thumbnail(url=interaction.user.display_avatar.url)
		embed.add_field(name="Your word was: ",
						value=res[1][1],
						inline=True)
		await interaction.response.send_message(embed=embed)
	elif res[0] == 1:
		embed = discord.Embed(title=interaction.user.display_name +
								"\'s Hangman Game",
								description=res[1][0],
								color=0x61dfff)
		embed.set_thumbnail(url=interaction.user.display_avatar.url)
		embed.add_field(name="Hint: ",
						value=res[1][1],
						inline=True)
		embed.add_field(name="Incorrect letters: ",
						value=res[1][2],
						inline=True)
		embed.add_field(name="Lives: ", value=res[1][3], inline=True)
		await interaction.response.send_message(embed=embed)
	else:  #res[0] == 2
		embed = discord.Embed(title=interaction.user.display_name +
								"\'s Hangman Game",
								description=res[1][0],
								color=0x61dfff)
		embed.set_thumbnail(url=interaction.user.display_avatar.url)
		embed.add_field(name="Your word was: ",
						value=res[1][1],
						inline=True)
		embed.add_field(name="Lives: ", value=res[1][3], inline=True)
		embed.add_field(name=res[1][4], value="", inline=True)
		await interaction.response.send_message(embed=embed)

	# Update interaction response message_id
	data = helper.read_file("minigame_session.json")
	response_message = await interaction.original_response()
	user_session = data.get(str(interaction.user.id), None)
	if user_session != None:
		user_session["message_id"] = response_message.id
		helper.write_file("minigame_session.json", data)


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

	embed = discord.Embed(title=interaction.user.display_name + "'s Gacha",
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.display_avatar.url)
	
	# Add embed field for each gacha result item
	for item in res:
		embed.add_field(name=item[0], value=item[1], inline=False)

	await interaction.response.send_message(embed=embed)

@tree.command(name="salvage",
				description="Sell a role icon for jemdust",
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
													str(res) + " " + helper.JEMDUST_EMOTE)

# keep_alive()
# token = os.environ.get("TOKEN")
load_dotenv()
token = os.getenv("TOKEN")
client.run(token)
