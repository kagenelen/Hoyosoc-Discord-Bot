import helper

import time
import discord
import random
import re

YATTA_EMOTE = ["<:YattaNoText:1168444235620569160>",
	  "<:Yatta:1168443429869592606>",
	  "<:YattaBoom:1168443375645622282>",
	  "<:YattaRed:1168443412912025601>",
	  "<a:YattaDance:1168443447036887060>",
	  "<:yatta:1025653835596824687>",
	  "<:ShenheYatta:1169519511582552115>",
	  "<:NahidaYatta:1169519517425217626>"]
UNYATTA_EMOTE = \
"<:Unyatta_01:1169516502576279552><:Unyatta_02:1169516506317590528><:Unyatta_03:1169516508523806741>\n" + \
"<:Unyatta_04:1169516512214777896><:Unyatta_05:1169516516237127690><:Unyatta_06:1169516519001169952>\n" + \
"<:Unyatta_07:1169516523082235934><:Unyatta_08:1169516527016476732><:Unyatta_09:1169516528757133352>"

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
	data = helper.read_file("tasks.json")
	data.append(new_entry)
	helper.write_file("tasks.json", data)

# List scheduled tasks
# Return list of [task_type, task_time]
def list_tasks():
	data = helper.read_file("tasks.json")

	task_list = []
	for task in data:
		task_list.append([task["type"].title(), helper.unix_to_syd(task["time"])])

	return task_list

# Count number of times a substring appears in channel
# Argument: channel object, output to file (0 or 1)
# Return: number of appearance of a substring
async def channel_substring_counter(channel, output):
	counter = 0
	async for message in channel.history(limit=None):
		all_matches = re.findall("<:\w*[Cc][Aa][Rr][Dd]\w*:[0-9]+>", message.content) # Change regex to suit needs
		counter += len(all_matches)

		if output == 1:
			f = open("card.txt", "a")
			f.write(message.content + "\n")
			f.close()

	print("There are " + str(counter) + " cards in " + channel.name)

	return counter

# Count number of times a card emote appears in a message and update card spam description
# Argument: channel object
# Return: number of appearance of a substring
async def card_update(channel):
	topic_card = re.search("[0-9]+", channel.topic).group()
	data = helper.read_file("config.json")

	if data["card_spam_counter"] != int(topic_card):
		await channel.edit(reason="Card count update", 
								 topic="If only I had " + str(data["card_spam_counter"]) + " nickels for all these card emotes.")
		print("Card spam description updated from " + topic_card + " to " + str(data["card_spam_counter"]))

	return data["card_spam_counter"]

# Generate a string of random number of yatta emotes
# Return: Yatta string
def yatta_random():
	emote_amount = random.randint(1, 10)
	yatta_str = ""
	for x in range(emote_amount):
		yatta_str += random.choice(YATTA_EMOTE) + " "

	return yatta_str


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
	config = helper.read_file("config.json")
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

	role1 = discord.utils.get(message.guild.roles, name="Traveller")
	role2 = discord.utils.get(message.guild.roles, name="⠀⠀⠀⠀⠀⠀⠀ Cosmetic Roles ⠀⠀⠀⠀⠀⠀⠀")
	role3 = discord.utils.get(message.guild.roles, name="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ About ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀")
	role4 = discord.utils.get(message.guild.roles, name="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ Misc ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀")
	role5 = discord.utils.get(message.guild.roles, name="Unverified")
	if role1 == None or role2 == None or role3 == None or role4 == None or role5 == None:
		return

	await user.add_roles(role1)
	await user.add_roles(role2)
	await user.add_roles(role3)
	await user.add_roles(role4)
	await message.add_reaction("✅")
	print(username + " has been given a role")

	try:
		await user.remove_roles(role5)
	except:
		pass

	return user

