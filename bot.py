import discord
from discord.ext import tasks
from discord import app_commands
from discord.ui import Button, View
import os
import json
import random
import time

import helper
import uid_finder
import gambling
import minigame
# from keep_alive import keep_alive

############################ CONSTANTS ###################################
VERIFICATION_CHANNEL = 822423063697948693
GENSOC_SERVER = 822411164846653490
WELCOME_CHANNEL = 822411164846653492
WELCOME_MESSAGE = "Welcome traveller! <:GuobaWave:895891227067711548> Remember to fill out the verification form to gain access to the server. Enjoy your stay at GenSoc and feel free to chuck an intro in <#822732136515764265>."
TEST_CHANNEL = 962970271545982989

# Read json file for channel
absolute_path = os.path.dirname(os.path.abspath(__file__)) + "/json_files/"
with open(absolute_path + 'config.json', 'r') as f:
    data = json.load(f)
    VERIFICATION_CHANNEL = data['channel']
    f.close()

############################# CODE STARTS HERE ############################


def runbot():
	
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
	
	@tasks.loop(hours=24)
	async def daily_role_expiry_check():
		expired = gambling.check_role_expiry()
		print("Role expiry check done at " + str(time.time()))
	
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
	async def add_uid(interaction, uid: str):
		result = uid_finder.save_uid(str(interaction.user.id), uid)
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
				target_user.name + " has the following uid: " + result)
	
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
				  description="Check your primojem and owned roles.",
				  guild=discord.Object(id=GENSOC_SERVER))
	async def inventory(interaction):
		res = gambling.get_inventory(interaction.user.id)
	
		embed = discord.Embed(title=interaction.user.name + "\'s inventory",
							  description="Primojem: " + str(res[0]),
							  color=0x61dfff)
	
		# Add embed field for each item
		for r in range(1, len(res)):
			embed.add_field(name=res[r][0].capitalize(),
							value=res[r][1],
							inline=False)
	
		await interaction.response.send_message(embed=embed)
	
	@tree.command(name="shop",
				  description="View role shop.",
				  guild=discord.Object(id=GENSOC_SERVER))
	async def view_shop(interaction):
		res = gambling.get_inventory(interaction.user.id)
	
		price = [1500, 4500, 30000]
		if helper.is_booster(interaction.user):
			price = [int(x / 2) for x in price]
	
		description = ("7 day role costs " + str(price[0]) + "\n" +
					   "30 day role costs " + str(price[1]) + "\n" +
					   "Permanent role costs " + str(price[2]) + "\n" +
					   "Buying a role you own will increase the duration.\n\n")
	
		embed = discord.Embed(title="Shop",
							  description=description,
							  color=0x61dfff)
		embed.set_footer(text="Owned primojem: " + str(res[0]))
	
		# Add embed field for each role
		embed.add_field(name="Abyss", value="Colour = gray", inline=False)
		embed.add_field(name="Anemo", value="Colour = teal", inline=False)
		embed.add_field(name="Cryo",
						value="Colour = whitish blue",
						inline=False)
		embed.add_field(name="Dendro", value="Colour = green", inline=False)
		embed.add_field(name="Electro", value="Colour = magenta", inline=False)
		embed.add_field(name="Geo", value="Colour = yellow", inline=False)
		embed.add_field(name="Hydro", value="Colour = blue", inline=False)
		embed.add_field(name="Pyro", value="Colour = red", inline=False)
	
		await interaction.response.send_message(embed=embed)
	
	@tree.command(name="buy",
				  description="Buy item from shop.",
				  guild=discord.Object(id=GENSOC_SERVER))
	async def buy_item(interaction, item_name: str, duration: str):
		if duration.lower() == "permanent":
			duration = 999
	
		booster = helper.is_booster(interaction.user)
		res = gambling.buy_role(interaction.user.id, item_name, duration,
								booster)
	
		if res != None:
			await interaction.response.send_message(res, ephemeral=True)
		else:
			await interaction.response.send_message(
				"Successfully bought " + item_name.lower() + " for " +
				str(duration) + " days. Use **/equip** to use the role.")
	
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
			bet = helper.get_user_entry(interaction.user.id)
	
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
	async def hangman(interaction, difficulty: str):
		res = minigame.new_hangman(interaction.user.id, difficulty)
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

	# keep_alive()
	token = os.environ.get("TOKEN")
	client.run(token)
	