import helper

import time
import discord
import random
import string
import re
from dotenv import load_dotenv
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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


# Parses necessary information from verification form
# Argument: Message (class)
# Return: User (member class) or None if user not found
async def verify_form(message):
	# Deals message type: either embed or not embed
	message_words = []
	if (len(message.embeds) > 0):
		message_words = message.embeds[0].description.split('\n')
	else:
		message_words = message.content.split('\n')

	old_username = False
	username = None
	for word in message_words:
		search_res = re.search(r'(?:!\w+\s+)?([^\n]*#[0-9]*)', word)
		if search_res != None:  # Discord old username format found
			old_username = True
			username = search_res.group()
			username_list = username.split("#")

	email = None
	unsw = False
	for index, word1 in enumerate(message_words):
		if "discord username" in word1.lower(): # Discord new username format
			username = message_words[index + 1].lower()

		if "email:" in word1.lower():
			email = message_words[index + 1].lower()

		if "your zid" in word1.lower() and message_words[index + 1].lower() != "z0000000":
			email = message_words[index + 1].lower() + "@ad.unsw.edu.au"
			unsw = True

	if username == None and email == None:
		# Not a verification form, ignore message
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
	config = helper.read_file("config.json")
	if user.id in config["user_blacklist"]:
		# Blacklisted user
		await message.reply("WARNING: <@" + str(user.id) + "> is on the blacklist.")
		return None

	# Security check: account age
	if time.mktime(user.created_at.timetuple()) > time.time() - 2592000:
		# Account is less than 1 month old
		await message.reply("WARNING: <@" + str(user.id) + "> account is less than 1 month old. Please manually send verification email with //send_code")
		return None

	# Send verification email to zid or supplied email
	if email != None:
		verification_code = generate_code(user, email, unsw)
		is_sent = await send_verify_email(user, email, verification_code, True)
		if is_sent:
			await message.add_reaction("✅")
	
	return user

# Generate verification code
# Argument: user object, email, is_unsw  
def generate_code(user, email, unsw):
	digits = string.ascii_uppercase + "0123456789"
	verification_code = ''.join(random.choice(digits) for i in range(8))
	expiry = time.time() + 1800 # 30 minute expiry

	data = helper.read_file("verification.json")
	data[str(user.id)] = {
		"code": verification_code,
		"expiry": expiry,
		"unsw": unsw
	}

	helper.write_file("verification.json", data)

	return verification_code
	
# Email user the verification code
# Argument: discord user (object), email, verification code, send reminder dm true/false
# Return: True if email sent, False if error occurs
async def send_verify_email(discord_user, email, code, send_remind):
	from_addr = 'UNSW Hoyoverse Society'
	to_addr = email
	text = """
Your verification code is:
%s

This code will expire in 30 minutes, and will only work for the discord user: %s. 

Use the code with the command  \\verify_me  to become verified. The command will immediately verify UNSW students. However non-UNSW verification form details will need to be manually checked by an society executive after using this command.
""" % (code, discord_user.name)
	
	username = 'verify.unswhoyosoc@gmail.com'
	load_dotenv()
	password = os.getenv("EMAIL_PASS")

	msg = MIMEMultipart()

	msg['From'] = from_addr
	msg['To'] = to_addr
	msg['Subject'] = 'Hoyoverse Society Verification Code'
	msg.attach(MIMEText(text))

	try:
		server = smtplib.SMTP('smtp.gmail.com:587')
		server.ehlo()
		server.starttls()
		server.ehlo()
		server.login(username,password)
		server.sendmail(from_addr,to_addr,msg.as_string())
		server.quit()
		
	except Exception as error:
		print("An exception occurred during emailing: ", error)
		return False

	# Send dm to remind user
	if send_remind:
		channel = await discord_user.create_dm()
		await channel.send("You have been sent a verification code at " + email + 
						   ". Please check your spam and bin if you cannot find the email.")

	print(discord_user.name + " has been emailed an verification code at " + email)
	return True

# Check if verification code is correct and not expired
# Argument: discord_id, code
# Return: True/False depending on correct code + is unsw or error message
def is_code_correct(discord_id, code):
	data = helper.read_file("verification.json")
	discord_id = str(discord_id)
	
	entry = data.get(discord_id, None)
	if entry == None:
		return "You do not have an associated verification code, as you may have provided the wrong username."

	if time.time() > entry["expiry"]:
		return "Your verification code has expired. Please ask an executive to resend a verification email."
		
	if entry["code"] == code.upper():
		data.pop(discord_id)
		helper.write_file("verification.json", data)
		if entry["unsw"]:
			return True
		else:
			return False
			
	
	return "The verification code you have provided is incorrect."
	
# Add all verified roles and remove unverified status
# Argument: Member (class)
# Return: User (member class) or None if user not found
async def add_verified(user):
	role1 = discord.utils.get(user.guild.roles, name="Traveller")
	role2 = discord.utils.get(user.guild.roles, name="⠀⠀⠀⠀⠀⠀⠀ Cosmetic Roles ⠀⠀⠀⠀⠀⠀⠀")
	role3 = discord.utils.get(user.guild.roles, name="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ About ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀")
	role4 = discord.utils.get(user.guild.roles, name="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ Misc ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀")
	role5 = discord.utils.get(user.guild.roles, name="Unverified")
	if role1 == None or role2 == None or role3 == None or role4 == None or role5 == None:
		return

	await user.add_roles(role1)
	await user.add_roles(role2)
	await user.add_roles(role3)
	await user.add_roles(role4)
	
	print(user.name + " has been given a role.")

	try:
		await user.remove_roles(role5)
	except:
		pass

	return user

# Generates the user a character welcome message
# Argument: Member (class)
# Return: welcome message string
def create_welcome(user):
	data = helper.read_file("message.json")
	welcome_character = random.choices(list(data.keys()), k=1)[0]
	character_message = "*" + data.get(welcome_character)[
		1] + "    " + data.get(welcome_character)[0] + "*"
	character_message = character_message.replace("author", user.mention)
	return character_message