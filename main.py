import discord
from discord.ext import tasks
from discord import app_commands
from discord.ui import Button, View
from dotenv import load_dotenv
import os
import json
import time
import DiscordUtils
import re
import asyncio

import helper
import misc
import uid_finder
import gambling
import minigame
import followup
# from keep_alive import keep_alive

# IMPORTANT: Replit code is using a test bot on the test server. Before committing please change GENSOC_SERVER back to actual server's id

############################ CONSTANTS ###################################
WELCOME_MESSAGE = "Welcome traveller! <:GuobaWave:895891227067711548> Remember to go to <#1198949485498347520> and fill out the form to gain access to the server. \n\n Enjoy your stay at HoyoSoc and feel free to chuck an intro in <#822732136515764265> and grab your roles from <#827393050299858965>."

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
	CODE_CHANNEL = data['code_channel']
	CARD_SPAM_CHANNEL = data['card_spam_channel']
	MODERATION_CHANNEL = data['moderation_channel']
	COLOUR_ROLE_PREVIEW = data['role_colour_shop']
	
	f.close()

# NOTICE: Uncomment these variables if testing on the test server
"""
GENSOC_SERVER = 962970271545982986 
CARD_SPAM_CHANNEL = 1158232410299846747
VERIFICATION_CHANNEL = 986440303655399454
MODERATION_CHANNEL = 1181463563722833961
WELCOME_CHANNEL = 962970271545982989
CODE_CHANNEL = 1275044091486539804
"""

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
	card_spam_description_update.start()

	# helper.write_encrypted_file("wordlist.json", str(helper.read_file("wordbank_decrypted.json")))

@client.event
async def on_member_join(member):
	unverified = discord.utils.get(member.guild.roles, name="Unverified")
	await member.add_roles(unverified)

@client.event
async def on_message(message):
	global WELCOME_MESSAGE

	####### This section deals with antispam ########################
	if not message.author.bot:
		match_obj = re.search("^(.)\\1*$", message.content)
		if match_obj != None and "­" in message.content:
			await message.delete()
			mod_channel = client.get_channel(MODERATION_CHANNEL)
			await mod_channel.send("Message deleted from " + message.author.name + ". Reason: Invisible character spam.")

	####### This section deals with chat primojems ########################
	if not message.author.bot:
		helper.get_user_entry(str(message.author.id))
		data = helper.read_file("users.json")
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
		try:
			old_welcome = await channel.fetch_message(data["prev_welcome_message"])
			await old_welcome.delete()
		except:
			pass

		data["prev_welcome_message"] = welcome.id
		helper.write_file("config.json", data)
		return

	####### This section deals with verifying ##############################
	if (message.channel.id == VERIFICATION_CHANNEL):
		user = await misc.verify_form(message)
		if user == None:
			return

		data = helper.read_file("config.json")
		if data['verification_level'] == 'low':
			user_welcome = misc.create_welcome(user)
			welcome_channel = client.get_channel(WELCOME_CHANNEL)
			await welcome_channel.send(user_welcome)  

	##### This section deals with the counting game #######################
	if (message.channel.id == COUNTING_CHANNEL and not message.author.bot):
		res = minigame.number_validity(message)
		if res == True:
			await message.add_reaction(helper.PRIMOJEM_EMOTE)
		
		if isinstance(res, str):
			channel = client.get_channel(COUNTING_CHANNEL)
			await channel.send(res)

	##### This section deals with card spam #######################
	if (message.channel.id == CARD_SPAM_CHANNEL and not message.author.bot):
		all_matches = re.findall("<:\w*[Cc][Aa][Rr][Dd]\w*:[0-9]+>", message.content) # Change regex to suit needs
		if len(all_matches) != 0:
			data = helper.read_file("config.json")
			data["card_spam_counter"] += len(all_matches)
			helper.write_file("config.json", data)

@client.event
async def on_message_delete(message):
	##### This section deals with counting game deletions #######################
	if message.channel.id == COUNTING_CHANNEL:
		if minigame.counting_deletion_check(message):
			# Valid number deleted, send moderation log message
			mod_channel = client.get_channel(MODERATION_CHANNEL)
			await mod_channel.send("<@" + str(message.author.id) + "> has deleted the message \"" + 
				message.content + "\" in the counting game.")
	

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
								 name=e[1][0].title())
		await user.remove_roles(role, reason="Expired role.")
		print(role.name + " removed from " + user.display_name)

@tasks.loop(hours=24)
async def make_backup():
	helper.backup_file("users.json")
	minigame.minigame_earnings = {}

@tasks.loop(minutes=30)
async def card_spam_description_update():
	channel = client.get_channel(CARD_SPAM_CHANNEL)
	await misc.card_update(channel)

@tasks.loop(minutes=1)
async def run_scheduled_tasks():
	data = helper.read_file("tasks.json")

	# Run any task that is past the time and delete it after
	update_task_file = False
	task_copy = list(data)
	
	for task in task_copy:
		if task["time"] <= time.time():
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
	welcome = await client.get_channel(WELCOME_CHANNEL).send(WELCOME_MESSAGE)
	data = helper.read_file("config.json")
	data["prev_welcome_message"] = welcome.id
	helper.write_file("config.json", data)

@tree.command(name="set_verification",
				description="Set verification security level. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(security=[
	discord.app_commands.Choice(name="Automatic verification upon form completion", value="low"),
	discord.app_commands.Choice(name="Automatic verification for any email", value="medium"),
	discord.app_commands.Choice(name="Automatic verification for UNSW students", value="high")
])
async def set_verification(interaction, security: app_commands.Choice[str]):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	# Set verification channel
	data = helper.read_file("config.json")
	data['verification_level'] = security.value
	helper.write_file("config.json", data)
	await interaction.response.send_message(
		"Verification security level has been set to " + security.name,
		ephemeral=True)


@tree.command(name="daylight_savings",
				description="Daylight savings settings. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(mode=[
	discord.app_commands.Choice(name="Daylight savings", value="on"),
	discord.app_commands.Choice(name="No daylight savings", value="off")
])
async def set_daylight(interaction, mode: app_commands.Choice[str]):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	# Set daylight savings setting
	misc.switch_daylight(mode.value)
	await interaction.response.send_message(
		"Daylight savings has been switched " + mode.value,
		ephemeral=True)

	
@tree.command(name="blacklist_user",
				description="Blacklist user from verification. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(action=[
	discord.app_commands.Choice(name="Add", value=1),
	discord.app_commands.Choice(name="Remove", value=2),
])
async def blacklist_user(interaction, action: app_commands.Choice[int], target_user: discord.Member = None, zid: str = None):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	
	data = helper.read_file("config.json")
	blacklist = data["user_blacklist"]
	
	if action.value == 1:
		if zid != None and zid not in blacklist: blacklist.append(zid)
		if target_user != None and target_user.id not in blacklist : blacklist.append(target_user)
		await interaction.response.send_message("Blacklist successful.")
		
	else:
		if zid != None:
			blacklist = [j for j in blacklist if j != zid]
		if target_user != None:
			blacklist = [j for j in blacklist if j != target_user.id]
		data["user_blacklist"] = blacklist
		await interaction.response.send_message("Removal successful.")

	helper.write_file("config.json", data)


@tree.command(name="show_blacklist",
				description="Show blacklisted users. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def show_blacklist(interaction):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	blacklist = helper.read_file("config.json")["user_blacklist"]
	await interaction.response.send_message("\n".join([str(x) for x in blacklist]))


@tree.command(name="edit_shop",
				description="Add/remove role icon to shop. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(action=[
	discord.app_commands.Choice(name="Add", value=1),
	discord.app_commands.Choice(name="Remove", value=2),
])
async def edit_shop(interaction, role_name: str, rarity: int, action: app_commands.Choice[int], shop_image: str = None):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.", ephemeral=True)
		return

	if rarity != 4 and rarity != 5:
		await interaction.response.send_message("Rarity can only be 4 or 5", ephemeral=True)
		return

	data = helper.read_file("role_icon.json")
	if action.value == 1:
		data[str(rarity)].append(role_name.title())
		await interaction.response.send_message(role_name.title() + " has been added to the shop.")
	else:
		data[str(rarity)].remove(role_name.title())
		await interaction.response.send_message(role_name.title() + " has been removed from the shop.")

	if shop_image != None:
		config = helper.read_file("config.json")
		config["role_icon_shop"] = shop_image
		helper.write_file("config.json", config)

	helper.write_file("role_icon.json", data)

@tree.command(name="delete_messages",
				description="Delete last x messages from a channel, optionally from a specific user. Admin only.",
				guild=discord.Object(id=GENSOC_SERVER))
async def delete_messages(interaction, channel: discord.TextChannel, message_number: int, target_user: discord.Member = None):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.", ephemeral=True)
		return
	
	if target_user != None:
		def from_user(m):
			return m.author == target_user
		deleted = await channel.purge(limit=message_number, check=from_user)
	else:
		deleted = await channel.purge(limit=message_number)
	
	await channel.send("Deleted " + str(len(deleted)) + " messages.")

@tree.command(name="view_tasks",
				description="View all scheduled tasks.",
				guild=discord.Object(id=GENSOC_SERVER))
async def view_tasks(interaction):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	embed = discord.Embed(title="Scheduled Tasks", color=0x61dff)
	tasks = misc.list_tasks()
	for t in tasks:
		embed.add_field(name=t[0], value=t[1], inline=False)

	await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="send_code",
	description="Send verification code. Admin only.",
	guild=discord.Object(id=GENSOC_SERVER))
async def send_code(interaction, target_user: discord.Member, email: str, is_unsw: bool, send_reminder_dm: bool):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	await interaction.response.defer()
	
	code = misc.generate_code(target_user, email, is_unsw)
	is_sent = await misc.send_verify_email(target_user, email, code, send_reminder_dm)
	if is_sent:
		await interaction.followup.send("Email  has been sent to " + target_user.name)
	else:
		await interaction.followup.send("Failed to send.")

@tree.command(name="verify_user",
	description="Manually verify user. Admin only.",
	guild=discord.Object(id=GENSOC_SERVER))
async def admin_verify(interaction, verification_target: discord.Member):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	await interaction.response.defer()
	
	await misc.add_verified(verification_target)
	await interaction.followup.send("<@" + str(verification_target.id) + "> has been verified.")
	
	channel = client.get_channel(WELCOME_CHANNEL)
	user_welcome = misc.create_welcome(verification_target)
	await channel.send(user_welcome)
	
@tree.command(name="verify_me",
	description="New member self verification.",
	guild=discord.Object(id=GENSOC_SERVER))
async def user_self_verify(interaction, verification_code: str):
	await interaction.response.defer()
	
	res = misc.is_code_correct(interaction.user.id, verification_code)
	if isinstance(res, str):
		await interaction.followup.send(res, ephemeral=True)
		return

	if res is True:
		# Is UNSW student, auto verify
		await misc.add_verified(interaction.user)
		await interaction.followup.send("Congratulations! You have been verified.", ephemeral=True)
		channel = client.get_channel(WELCOME_CHANNEL)
		user_welcome = misc.create_welcome(interaction.user)
		await channel.send(user_welcome)
		
	else:
		# Not UNSW student, need exec to check details and manual verify
		mod_channel = client.get_channel(MODERATION_CHANNEL)
		await interaction.followup.send("Thank you for the correct code. Please wait patiently for the Hoyosoc team to check the details you have provided.", ephemeral=True)
		await mod_channel.send("<@" + str(interaction.user.id) + "> has entered the correct verification code. Please verify their details before using \\verify_user.")
		
	
@tree.command(name="set_count",
				description="Set counting game current number.",
				guild=discord.Object(id=GENSOC_SERVER))
async def set_count(interaction, number: int):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	data = helper.read_file("count.json")
	data["next_valid_number"] = number + 1
	data["last_user"] = 1
	helper.write_file("count.json", data)

	await interaction.response.send_message("Count has been set to " + str(number))

@tree.command(name="card_count",
				description="Count card emotes in current channel.",
				guild=discord.Object(id=GENSOC_SERVER))
async def card_count(interaction, channel: discord.TextChannel):
	if not helper.is_team(interaction):
		await interaction.response.send_message(
			"Insuffient permission. Command only available to admins due to long execution time.",
			ephemeral=True)
		return
	
	await interaction.response.defer()
		
	num = await misc.channel_substring_counter(channel, output.value)
	if channel.id == CARD_SPAM_CHANNEL:
		data = helper.read_file("config.json")
		data["card_spam_counter"] = num
		helper.write_file("config.json", data)
	
	await interaction.followup.send("There are " + str(num) + " card emotes in " + channel.name, ephemeral=True)


@tree.command(name="yatta",
				description="Send yatta emotes.",
				guild=discord.Object(id=GENSOC_SERVER))
async def yatta(interaction):
	res = misc.yatta_random()
	await interaction.response.send_message(res)

@tree.command(name="unyatta",
	description="Send unyatta emotes.",
	guild=discord.Object(id=GENSOC_SERVER))
async def unyatta(interaction):
	await interaction.response.send_message(misc.UNYATTA_EMOTE)


@tree.command(name="user_to_thread",
	description="Add users to thread",
	guild=discord.Object(id=GENSOC_SERVER))
async def users_to_thread(interaction, thread: discord.Thread, role1: discord.Role, role2: discord.Role = None):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	await interaction.response.defer()

	num = 1
	for member in interaction.guild.members:
		if role1 in member.roles and (role2 == None or role2 in member.roles):
			await thread.add_user(member)
			num += 1

		if num % 5 == 0:
			await asyncio.sleep(6)

	await interaction.followup.send("All " + role1.name + " users have been added to " + thread.name)
	print("All " + role1.name + " users have been added to " + thread.name)



@tree.command(name="help",
				description="View all available bot commands.",
				guild=discord.Object(id=GENSOC_SERVER))
async def help_commands(interaction):
	embed_general = discord.Embed(title="General Commands", color=0x61dff)
	embed_general.set_footer(text="Page 1/5")
	embed_primojem = discord.Embed(title="Primojem Commands", color=0x61dff)
	embed_primojem.set_footer(text="Page 2/5")
	embed_minigame = discord.Embed(title="Minigame Commands", color=0x61dff)
	embed_minigame.set_footer(text="Page 3/5")
	embed_poll = discord.Embed(title="Auction Commands", color=0x61dff)
	embed_poll.set_footer(text="Page 4/5")
	embed_admin = discord.Embed(title="Admin Commands", color=0x61dff)
	embed_admin.set_footer(text="Page 5/5")
	
	paginator = DiscordUtils.Pagination.AutoEmbedPaginator(interaction)
	
	embed_primojem.add_field(name="**/checkin**", value="Daily free primojems.", inline=False)
	embed_primojem.add_field(name="**/freeze_checkin**", value="Freeze check-in till a certain date to preserve streak.", inline=False)
	embed_primojem.add_field(name="**/leaderboard**", value="Top 30 of a category and your own rank.", inline=False)
	embed_primojem.add_field(name="**/shop**", value="See which roles and role icons you can buy.", inline=False)
	embed_primojem.add_field(name="**/buy**", value="Buy a role from the shop.", inline=False)
	embed_primojem.add_field(name="**/equip**", value="Equip or unequip a role.", inline=False)
	embed_primojem.add_field(name="**/inventory**", value="Check primojem, jemdust and owned roles.", inline=False)
	embed_primojem.add_field(name="**/gacha**", value="Gacha for role icons.", inline=False)
	embed_primojem.add_field(name="**/salvage**", value="Sell a role icon for jemdust.", inline=False)
	
	embed_minigame.add_field(name="**/blackjack**", value="Play blackjack.", inline=False)
	embed_minigame.add_field(name="**/hangman**", value="Play hangman.", inline=False)
	embed_minigame.add_field(name="**/coinflip**", value="Play heads or tails.", inline=False)
	embed_minigame.add_field(name="**/connect4**", value="Play connect 4.", inline=False)
	
	embed_poll.add_field(name="**/bid**", value="Bid on an auction.", inline=False)
	embed_poll.add_field(name="**/auction_info**", value="Get info about an auction.", inline=False)
	
	embed_general.add_field(name="**/add_uid**", value="Add UID to bot database.", inline=False)
	embed_general.add_field(name="**/remove_uid**", value="Remove UID from bot database.", inline=False)
	embed_general.add_field(name="**/find_uid**", value="List all UIDs of an user.", inline=False)
	embed_general.add_field(name="**/whose_uid**", value="Find the owner of an UID.", inline=False)
	embed_general.add_field(name="**/add_code**", value="Add redemption code to bot database", inline=False)
	embed_general.add_field(name="**/remove_code**", value="Remove redemption code from bot database.", inline=False)
	embed_general.add_field(name="**/list_codes**", value="List codes with filter rules.", inline=False)
	embed_general.add_field(name="**/fortune**", value="Get your daily fortune.", inline=False)
	embed_general.add_field(name="**/yatta**", value="Bot sends some yatta emotes.", inline=False)
	embed_general.add_field(name="**/unyatta**", value="Bot sends unyatta emotes.", inline=False)

	embed_admin.add_field(name="**/set_verification**", value="Set verification security level.", inline=False)
	embed_admin.add_field(name="**/blacklist_user**", value="Blacklist user.", inline=False)
	embed_admin.add_field(name="**/show_blacklist**", value="Show blacklisted users.", inline=False)
	embed_admin.add_field(name="**/edit_shop**", value="Add or remove role icon from shop.", inline=False)
	embed_admin.add_field(name="**/delete_messages**", value="Purge x messages from channel, optionally from a specific user.", inline=False)
	embed_admin.add_field(name="**/view_tasks**", value="View scheduled tasks.", inline=False)
	embed_admin.add_field(name="**/set_count**", value="Set counting game current number.", inline=False)
	embed_admin.add_field(name="**/card_count**", value="Count card emotes in a channel.", inline=False)
	embed_admin.add_field(name="**/scrape_uid**", value="Add all uids from a channel.", inline=False)
	embed_admin.add_field(name="**/create_auction**", value="Start auction.", inline=False)
	embed_admin.add_field(name="**/give_primojems**", value="Give primojem to a list of users.", inline=False)
	embed_admin.add_field(name="**/edit_inventory**", value="Give user an inventory role.", inline=False)
	embed_admin.add_field(name="**/daylight_savings**", value="Switch on/off daylight savings.", inline=False)
	embed_admin.add_field(name="**/user_to_thread**", value="Add users with a specified role to thread.", inline=False)

	embeds = [embed_general, embed_primojem, embed_minigame, embed_poll, embed_admin]
	await paginator.run(embeds)


################################ UID #################################

@tree.command(name="add_uid",
				description="Add your UID to be easily found",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(game=[
	discord.app_commands.Choice(name="Genshin Impact", value="genshin"),
	discord.app_commands.Choice(name="Honkai Star Rail", value="hsr"),
	discord.app_commands.Choice(name="Honkai Impact", value="honkai"),
	discord.app_commands.Choice(name="Tears of Themis", value="tot"),
	discord.app_commands.Choice(name="Zenless Zone Zero", value="zzz"),
	discord.app_commands.Choice(name="Wuthering Waves", value="wuwa"),
])
async def add_uid(interaction, game: app_commands.Choice[str], uid: str, hide_message: bool = False):
	result = uid_finder.save_uid(str(interaction.user.id), uid, game.value)
	if result == False:
		await interaction.response.send_message("Invalid UID",
												ephemeral=True)
	else:
		await interaction.response.send_message(str(uid) + " has been added.", ephemeral=hide_message)

@tree.command(name="remove_uid",
				description="Remove a UID from our database",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(game=[
	discord.app_commands.Choice(name="Genshin Impact", value="genshin"),
	discord.app_commands.Choice(name="Honkai Star Rail", value="hsr"),
	discord.app_commands.Choice(name="Honkai Impact", value="honkai"),
	discord.app_commands.Choice(name="Tears of Themis", value="tot"),
	discord.app_commands.Choice(name="Zenless Zone Zero", value="zzz"),
	discord.app_commands.Choice(name="Wuthering Waves", value="wuwa"),
])
async def remove_uid(interaction, game: app_commands.Choice[str], uid: str):
	result = uid_finder.remove_uid(str(interaction.user.id), uid, game.value)
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
	discord.app_commands.Choice(name="Honkai Impact", value="honkai"),
	discord.app_commands.Choice(name="Tears of Themis", value="tot"),
	discord.app_commands.Choice(name="Zenless Zone Zero", value="zzz"),
	discord.app_commands.Choice(name="Wuthering Waves", value="wuwa"),
])
async def reverse_find_uid(interaction, game:app_commands.Choice[str], uid: str):
	if not uid.isnumeric() or int(uid) >= 999999999 or int(uid) <= 0:
		await interaction.response.send_message("Invalid uid.", ephemeral=True)
		return

	result = uid_finder.whose_uid(uid, game.value)
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


############################### REDEMPTION CODES ###################################
@tree.command(name="add_code",
				description="Add redemption code.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(game=[
	discord.app_commands.Choice(name="Genshin Impact", value="genshin"),
	discord.app_commands.Choice(name="Honkai Star Rail", value="hsr"),
	discord.app_commands.Choice(name="Honkai Impact", value="hi3"),
	discord.app_commands.Choice(name="Tears of Themis", value="tot"),
	discord.app_commands.Choice(name="Zenless Zone Zero", value="zzz"),
	discord.app_commands.Choice(name="Wuthering Waves", value="wuwa"),
])
async def add_redemption_code(interaction, code: str, game: app_commands.Choice[str], reward: str = "", expiry: str = None, show_link: bool = True, hide_message: bool = False):
	result = misc.add_code(code, game.value, expiry, reward)
	if isinstance(result, str):
		await interaction.response.send_message(result, ephemeral=True)
		return

	# Send code list message and delete previous code list
	channel = client.get_channel(CODE_CHANNEL)

	try:
		async for message in channel.history(limit=20):
			if message.author.bot and message.embed.title == "All Redemption Codes":
				await message.delete()
		await channel.send(embed=misc.display_code_list("All", "all", False, 5)[0])
	except Exception as e:
		print(e)
		pass

	# Make embed for interaction response
	embed = discord.Embed(
		title=code.upper(),
		description="Expires <t:" + str(result[1]) + ":R>",
		color=0x61dfff)
	embed.set_thumbnail(url=helper.game_thumbnail(game.value))

	if expiry == None:
		embed.description = "Expiry unknown"

	if reward != "":
		embed.add_field(name="Reward", value=reward)

	view = View(timeout=None)
	
	# DM button 
	dm_button = Button(label="DM Code", style=discord.ButtonStyle.primary)
	async def dm_callback(b_interaction):
		try:
			await b_interaction.user.send(code.upper())
			await b_interaction.response.send_message("DMed successfully", ephemeral=True)
			
		except:
			await b_interaction.response.send_message("Unable to DM you the code due to your settings.", ephemeral=True)

	if result[0] != None and show_link:
		# Redeem button
		url_button = Button(label="Redeem Now", style=discord.ButtonStyle.link, url=result[0])
		view.add_item(url_button)
			
	dm_button.callback = dm_callback
	view.add_item(dm_button)

	await interaction.response.send_message(embed=embed, view=view, ephemeral=hide_message)


@tree.command(name="remove_code",
				description="Remove redemption code.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(game=[
	discord.app_commands.Choice(name="Genshin Impact", value="genshin"),
	discord.app_commands.Choice(name="Honkai Star Rail", value="hsr"),
	discord.app_commands.Choice(name="Honkai Impact", value="hi3"),
	discord.app_commands.Choice(name="Tears of Themis", value="tot"),
	discord.app_commands.Choice(name="Zenless Zone Zero", value="zzz"),
	discord.app_commands.Choice(name="Wuthering Waves", value="wuwa"),
])
async def remove_redemption_code(interaction, code: str, game: app_commands.Choice[str]):
	result = misc.remove_code(code, game.value)
	await interaction.response.send_message(result, ephemeral=True)


@tree.command(name="list_codes",
				description="List and filter redemption codes.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(game=[
	discord.app_commands.Choice(name="Genshin Impact", value="genshin"),
	discord.app_commands.Choice(name="Honkai Star Rail", value="hsr"),
	discord.app_commands.Choice(name="Honkai Impact", value="hi3"),
	discord.app_commands.Choice(name="Tears of Themis", value="tot"),
	discord.app_commands.Choice(name="Zenless Zone Zero", value="zzz"),
	discord.app_commands.Choice(name="Wuthering Waves", value="wuwa"),
	discord.app_commands.Choice(name="All", value="all"),
])
async def list_redemption_codes(interaction, game: app_commands.Choice[str], is_expired: bool = None):
	embeds = misc.display_code_list(game.name, game.value, is_expired, 10)

	paginator = DiscordUtils.Pagination.AutoEmbedPaginator(interaction)

	await paginator.run(embeds)
	

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
	if isinstance(res, str):
		await interaction.response.send_message(
			"Check-in cooldown finishes " + res + ".",
			ephemeral=True)
	else:
		await interaction.response.send_message(
			"You got " + str(res[0]) +
			" primojems from the check-in. Current streak: " +
			str(res[1]) + ".")

@tree.command(name="freeze_checkin",
	description="Freeze check-in till a certain date to preserve streak. Cannot check-in before that date.",
	guild=discord.Object(id=GENSOC_SERVER))
async def checkin_freeze(interaction, date: str):
	res = gambling.freeze_checkin(interaction.user.id, date)
	
	if "cannot" in res or "format" in res:
		await interaction.response.send_message(res, ephemeral=True)
	else:
		await interaction.response.send_message(
			"<@" + str(interaction.user.id) + ">'s checkin has been frozen till " + res)

@tree.command(name="fortune",
				description="Is it your lucky day today?",
				guild=discord.Object(id=GENSOC_SERVER))
async def fortune(interaction):
	res = gambling.daily_fortune(interaction.user.id)
	if isinstance(res, str):
		await interaction.response.send_message(
			"Fortune cooldown finishes " + res + ".", ephemeral=True)
		return
	
	# Loading screen
	loading_message = "Getting your fortune ...\n"
	
	embed = discord.Embed(title=interaction.user.display_name + "\'s Fortune",
							description=loading_message,
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.display_avatar.url)
	await interaction.response.send_message(embed=embed)
	ori_response = await interaction.original_response()
	
	elements = ["<:Pyro:1177831404608966656>",
				"<:Hydro:1177831406349594628>",
				"<:Anemo:1177831416206217236>",
				"<:Electro:1177831411328241704>",
				"<:Dendro:1177831409453387837>",
				"<:Cryo:1177831401308045412>",
				"<:Geo:1177831414595584131>"]
	for x in range(7):
		loading_message += elements[x]
		embed.description = loading_message
		await asyncio.sleep(1)
		await ori_response.edit(embed=embed)
		
	# Actual fortune
	embed.description = res[1]
	embed.colour = res[2]
	embed.add_field(name="Fortune Level", value=res[0], inline=False)
	await asyncio.sleep(1)
	await ori_response.edit(embed=embed)

@tree.command(name="inventory",
				description="Check your primojem, jemdust and owned roles.",
				guild=discord.Object(id=GENSOC_SERVER))
async def inventory(interaction, target_user: discord.Member = None):
	if target_user != None:
		username = target_user.display_name
		res = gambling.get_inventory(target_user.id)
		thumbnail = target_user.display_avatar.url
	else:
		username = interaction.user.display_name
		res = gambling.get_inventory(interaction.user.id)
		thumbnail = interaction.user.display_avatar.url

	embed = discord.Embed(title=username + "\'s Inventory",
							description=str(res[0]) + " " + helper.PRIMOJEM_EMOTE + "  |  " + 
						  		str(res[1]) + " " + helper.JEMDUST_EMOTE,
							color=0x61dfff)
	embed.set_thumbnail(url=thumbnail)

	# Add embed field for each roles
	permanent_roles = []
	for r in res[2]:
		if r[1] == "Permanent":
			permanent_roles.append(r[0])
		else:
			embed.add_field(name=r[0].capitalize(),
						value=r[1],
						inline=False)
	
	if len(permanent_roles) != 0:
		permanent_roles_str = ", ".join(permanent_roles)
		embed.add_field(name="Permanent Roles",
							value=permanent_roles_str.title(),
							inline=False)
	
	if len(res[3]) != 0:
		embed.add_field(name="5 Star Role Icons",
							value=res[3],
							inline=False)

	if len(res[4]) != 0:
		embed.add_field(name="4 Star Role Icons",
							value=res[4],
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
	config_file = helper.read_file("config.json")

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
			"4 star role icon: 34 " + helper.JEMDUST_EMOTE + "\n" + 
			"Use **/gacha** to pull for role icons.\n\n" +
			"Please message an exec if you would like a character to be added to the role icon shop.")

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
		embed.set_image(url=config_file['role_icon_shop'])

	await interaction.response.send_message(embed=embed)

@tree.command(name="edit_inventory",
	description="Add role to user inventory. Admin only.",
	guild=discord.Object(id=GENSOC_SERVER))
async def add_role_to_inventory(interaction, target_user: discord.Member, role_name: str, expiry_date: str): 
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	res = gambling.modify_inventory(target_user.id, role_name, expiry_date)
	if res == None:
		await interaction.response.send_message(target_user.display_name + " has been given the " + role_name.lower() + " role.")
	else:
		await interaction.response.send_message(res, ephemeral=True)
				   
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
				description="Primojem/collection rate/gambling/check-in leaderboard.",
				guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(category=[
	discord.app_commands.Choice(name="Primojem", value="currency"),
	discord.app_commands.Choice(name="Role Icon Collection Rate", value="role_icon"),
	discord.app_commands.Choice(name="Gambling Profit", value="gambling_profit"),
	discord.app_commands.Choice(name="Gambling Loss", value="gambling_loss"),
	discord.app_commands.Choice(name="Check-in Streak", value="checkin_streak"),
])
async def leaderboard(interaction, category: app_commands.Choice[str]):
	res = gambling.get_leaderboard(category.value)
	
	embed_1 = discord.Embed(title=category.name + " Leaderboard", color=0x61dfff)
	embed_2 = discord.Embed(title=category.name + " Leaderboard", color=0x61dfff)
	embed_3 = discord.Embed(title=category.name + " Leaderboard", color=0x61dfff)
	embed_unused = discord.Embed(title=category.name + " Leaderboard", color=0x61dfff)

	paginator = DiscordUtils.Pagination.AutoEmbedPaginator(interaction)
	
	# Add embed field for each person in top 30
	rank = 1
	entry_number = 1
	your_rank = 0

	# Deal with tied 100% role collection
	tied_first = "1. "
	is_prev_tied = True
	
	for r in range(0, len(res)):
		user = interaction.guild.get_member(int(res[r][0]))
		if user == None:
			continue

		if entry_number <= 10:
			target_embed = embed_1
		elif entry_number <= 20:
			target_embed = embed_2
		elif entry_number <= 30:
			target_embed = embed_3
		else:
			target_embed = embed_unused
			
		if category.value == "role_icon":
			role_list = helper.read_file("role_icon.json")
			role_num = len(role_list["5"]) + len(role_list["4"])
			role_collection = round(len(set(res[r][1])) / role_num * 100)

			# Deal with tied 100% collection rate
			if role_collection == 100:
				tied_first += user.display_name + ", "
				rank += 1
				continue
				
			elif role_collection != 100 and is_prev_tied == True:
				# End of ties
				is_prev_tied = False
				target_embed.add_field(name=tied_first[:-2],
					value="100%",
					inline=False)
				
				target_embed.add_field(name=str(rank) + ". " + user.display_name,
					value=str(role_collection) + "%",
					inline=False)

			else:
				target_embed.add_field(name=str(rank) + ". " + user.display_name,
							value=str(role_collection) + "%",
							inline=False)
		
		else:
			# Not role icon leaderboard
			target_embed.add_field(name=str(rank) + ". " + user.display_name,
							value=str(res[r][1]),
							inline=False)

		if user.id == interaction.user.id:
			your_rank = rank
			
		rank += 1
		entry_number += 1
	
	embed_1.set_footer(text="Your rank: " + str(your_rank))
	embed_2.set_footer(text="Your rank: " + str(your_rank))
	embed_3.set_footer(text="Your rank: " + str(your_rank))
	embeds = [embed_1, embed_2, embed_3]
	
	await paginator.run(embeds)

@tree.command(
	name="give_primojems",
	description="Give primojems to list of people. Admin only.",
	guild=discord.Object(id=GENSOC_SERVER))
async def give_primojem(interaction, user_list: str, amount: int):
	if not helper.is_team(interaction):
		await interaction.response.send_message("Insuffient permission.",
												ephemeral=True)
		return

	await interaction.response.defer()
	if user_list == "all":
		gambling.update_all_currency(amount)
		await interaction.followup.send(str(amount) + " apologems given to all users",
												ephemeral=True)
	else:
		res = gambling.update_user_list_currency(user_list, amount, interaction.guild)
	await interaction.followup.send(str(amount) + " given to these users: " + ", ".join(res),
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
		description += "You have lost " + str(bet) + helper.PRIMOJEM_EMOTE + "\n\n"
	else:
		description += "You have won " + str(res[1] - int(bet)) + helper.PRIMOJEM_EMOTE + "\n\n"

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
	"Play hangman at normal (12 lives), hard (8 lives), or extreme (4 lives) difficulty.",
	guild=discord.Object(id=GENSOC_SERVER))
@app_commands.choices(difficulty=[
	discord.app_commands.Choice(name="Normal", value="normal"),
	discord.app_commands.Choice(name="Hard", value="hard"),
	discord.app_commands.Choice(name="Extreme", value="extreme"),
])
@app_commands.choices(fandom=[
	discord.app_commands.Choice(name="Genshin Impact", value="genshin"),
	discord.app_commands.Choice(name="Star Rail", value="hsr")
])
async def hangman(interaction, difficulty: app_commands.Choice[str], fandom: app_commands.Choice[str]):
	res = minigame.new_hangman(interaction.user.id, difficulty.value, fandom.value)
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

@tree.command(
	name="connect4",
	description="Play connect 4 against another person.",
	guild=discord.Object(id=GENSOC_SERVER))
async def connect4(interaction, invited_user: discord.Member, wager: int):
	res = minigame.new_connect(interaction.user, invited_user, wager)

	if isinstance(res, str):
		await interaction.response.send_message(res)
		return
	
	# Buttons
	view = View(timeout=120)

	# Accept button
	accept_button = Button(label="Accept", style=discord.ButtonStyle.blurple)
	async def accept_callback(b_interaction):
		if b_interaction.user.id == invited_user.id:
			await b_interaction.response.defer()
			await followup.start_connect4_followup(interaction, res)
	accept_button.callback = accept_callback
	view.add_item(accept_button)

	# Decline button
	decline_button = Button(label="Decline", style=discord.ButtonStyle.red)
	async def decline_callback(b_interaction):
		if b_interaction.user.id == invited_user.id:
			await b_interaction.response.defer()
			await followup.decline_connect4_followup(interaction)
	decline_button.callback = decline_callback
	view.add_item(decline_button)

	# Ping the invited user and ask for their response
	await interaction.response.send_message(
		"<@" + str(invited_user.id) + ">, " +
		interaction.user.display_name + " has challenged you to a game of connect 4 for " + 
		str(wager) + helper.PRIMOJEM_EMOTE + ". Do you accept?", view=view)


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

	if res == None or res == False:
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
