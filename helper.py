import json
import discord
import re
import os
import time
import datetime
import shutil
import pytz

SUBCOM_ROLE = "Subcommittee"
EXEC_ROLE = "2023 Gensoc Team"
PRIMOJEM_EMOTE = "<:Primojem:1108620629902626816>"
JEMDUST_EMOTE = "<:Jemdust:1108591111649362043>"
BETTER_EMOTE = "<:Betters:1122383400418934846>"
HEADS_EMOTE = "<:Heads:1137589987962015815>"
TAILS_EMOTE = "<:Tails:1137589996916850760>"

def write_file(file, data):
  absolute_path = os.path.dirname(os.path.abspath(__file__)) + "/json_files/"
  with open(absolute_path + file, "w") as f:
    json.dump(data, f, indent=4, separators=(',', ': '))

def read_file(file):
  absolute_path = os.path.dirname(os.path.abspath(__file__)) + "/json_files/"
  with open(absolute_path + file, 'rb') as f:
    data = json.load(f)
  return data

# Make file backup in backup folder
# Argument: file name (must be in json_file folder)
# Return: None
def backup_file(file):
	original = os.path.dirname(os.path.abspath(__file__)) + "/json_files/" + file
	
	tz_Sydney = pytz.timezone('Australia/Sydney')
	datetime_Sydney = datetime.datetime.now(tz_Sydney)
	date_format = datetime_Sydney.strftime("%d%b_%H.%M")

	target = os.path.dirname(os.path.abspath(__file__)) + "/backup/" + date_format + ".json"
	shutil.copyfile(original, target)
	print("Backup of " + file + " done at " + unix_to_syd(time.time()))

# Convert unix to sydney time
def unix_to_syd(unix_time):
	tz_Sydney = pytz.timezone('Australia/Sydney')
	datetime_Sydney = datetime.datetime.now(tz_Sydney)
	return datetime_Sydney.strftime("%d/%m %H:%M")

# Get user entry
# Function mainly used to create entry for new users
# Argument: discord id string
# Return: user entry
def get_user_entry(discord_id):
	discord_id = str(discord_id)
	data = read_file("users.json")
	user_entry = data.get(discord_id, None)
	
	if user_entry == None:
		# Create entry for new user
		user_entry = {
			"currency": 0,
			"next_checkin": int(time.time()),
			"role": {},
			"checkin_streak": 0,
			"genshin_uids": [],
			"role_icon": [],
			"jemdust": 0,
			"hsr_uids": [],
			"chat_cooldown": 0,
			"gambling_profit": 0,
			"gambling_loss": 0
		}
		data[discord_id] = user_entry
	
	write_file("users.json", data)
	return user_entry


# One time function for modifying database structure
# Modify this function to suit your need
def rewrite_structure():
	data = read_file("users.json")
	for user in data:
		if data[user].get("chat_cooldown", None) == None:
			data[user]["chat_cooldown"] = 0
			data[user]["gambling_profit"] = 0
			data[user]["gambling_loss"] = 0
		
	write_file("users.json", data)

	print("Database modification complete")


# Determines whether user is subcom or exec
# Argument: Interaction (class)
# Return: True if user is part of team, False otherwise
def is_team(interaction):
  subcom = discord.utils.find(lambda r: r.name == SUBCOM_ROLE,
                              interaction.guild.roles)
  admin = discord.utils.find(lambda r: r.name == EXEC_ROLE,
                             interaction.guild.roles)

	# This no longer checks for subcom
  if admin not in interaction.user.roles:
    return False
  return True


# Determines whether user is a server booster
# Argument: Member (class)
# Return: True if user is booster, False otherwise
def is_booster(user):
  role_names = [role.name for role in user.roles]
  if "Server Booster" in role_names:
    return True
  return False

# Create scheduled task
# Argument: task type, scheduled time to run task, dictionary containing other info
def create_task(task_type, task_time, task_info):
	# Create dictionary
	new_entry = {
		"type": task_type,
		"time": int(task_time)
	}
	
	new_entry.update(task_info)
	
	# Add entry to tasks.json
	data = read_file("tasks.json")
	data.append(new_entry)
	write_file("tasks.json", data)

# List scheduled tasks
# Return list of [task_type, task_time]
def list_tasks():
	data = read_file("tasks.json")

	task_list = []
	for task in data:
		task_list.append([task["type"].title(), unix_to_syd(task["time"])])

	return task_list

# Count number of times a substring appears in channel
# Argument: channel object
# Return: number of appearance of a substring
async def channel_substring_counter(channel):
	counter = 0
	async for message in channel.history(limit=None):
		all_matches = re.findall(":[A-Za-z0-9~]*[Cc][Aa][Rr][Dd][A-Za-z0-9~]*:", message.content) # Change regex to suit needs
		counter += len(all_matches)

	return counter

# Count number of times a card emote appears in a message and update card spam description
# Argument: message object
# Return: number of appearance of a substring
async def card_update(message):
	all_matches = re.findall(":[A-Za-z0-9~]*[Cc][Aa][Rr][Dd][A-Za-z0-9~]*:", message.content)
	message_card = len(all_matches)
	if message_card > 0:
		topic_card = re.search(" [0-9]+ ", message.channel.topic)
		total_card = int(topic_card.group()) + message_card
		await message.channel.edit(reason="Card count update", 
							 topic="If only I had " + str(total_card) + " nickels for all these card emotes.")
	
	return message_card


# Verifies user from moderator message
# Argument: Message (class)
# Return: User (member class) or None if user not found
async def verify_user(message):
	manual = False
	# Deals message type: either embed or not embed
	message_words = []
	if (len(message.embeds) > 0):
		message_words = message.embeds[0].description.split('\n')
	else:
		manual = True
		message_words = message.content.split('\n')

	old_username = False
	username = None
	for word in message_words:
		search_res = re.search(r'(?:!\w+\s+)?([^\n]*#[0-9]*)', word)
		if search_res != None and "JohnSmith#1234" not in word:  # Discord old username format found
			old_username = True
			username = search_res.group()
			username_list = username.split("#")

	for index, word1 in enumerate(message_words):
		if "discord id" in word1.lower(): # Discord new username format
			username = message_words[index + 1].lower()

	role = discord.utils.get(message.guild.roles, name="Traveller")
	if role == None:
		return

	if old_username:
		user = discord.utils.get(message.guild.members,
														 name=username_list[0],
														 discriminator=username_list[1])
	else:
		user = discord.utils.get(message.guild.members,
														 name=username)
		
	if user == None:
		await message.add_reaction("❌")
		print(username + " does not exist in the server")
		return None

	# Security check: blacklisted users
	config = read_file("config.json")
	if user.id in config["user_blacklist"]:
		# Blacklisted user
		await message.reply("WARNING: <@" + str(user.id) + "> is on the blacklist.")
		return None
	
	# Security check: account age
	if time.mktime(user.created_at.timetuple()) > time.time() - 2592000:
		# Account is less than 1 month old
		if not manual:
			# Do not verify these automatically
			await message.reply("WARNING: <@" + str(user.id) + "> account is less than 1 month old. Please manually verify this user.")
			return None
	
	await user.add_roles(role)
	await message.add_reaction("✅")
	print(username + " has been given a role")
	
	return user

