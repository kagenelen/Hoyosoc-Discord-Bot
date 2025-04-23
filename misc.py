import helper

import time
import discord
import random
import string
import re
from dotenv import load_dotenv
import os
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

NEWCOMER_EXPIRY = 604800 # 1 week
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

EMAIL_SENDER =  'verification@unswhoyosoc.org' # 'verify.unswhoyosoc@gmail.com
EMAIL_DOMAIN = 'mail.unswhoyosoc.org' # 'smtp.gmail.com'
EMAIL_PORT = 587

#################### Scheduled Tasks #####################################

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

#################### Card Counter #####################################

# Count number of times a substring appears in channel
# Argument: channel object
# Return: number of appearance of a substring
async def channel_substring_counter(channel, word):
	regex_str = ""
	for letter in word:
		regex_str += "[" + letter.upper() + letter.lower() + "]"

	counter = 0
	async for message in channel.history(limit=None):
		all_matches = re.findall("<:\w*" + regex_str + "\w*:[0-9]+>", message.content) # Change regex to suit needs
		counter += len(all_matches)

	print("There are " + str(counter) + " " + word + " emote in " + channel.name)

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

#################### Yatta #####################################

# Generate a string of random number of yatta emotes
# Return: Yatta string
def yatta_random():
	emote_amount = random.randint(1, 10)
	yatta_str = ""
	for x in range(emote_amount):
		yatta_str += random.choice(YATTA_EMOTE) + " "

	return yatta_str

#################### Daylight Savings Settings #####################################

# Turn daylight savings on or off in config.json
# mode (on/off)
# Return: None for success
def switch_daylight(mode):
	config = helper.read_file("config.json")
	mode = mode.lower()
	
	if mode == "off":
		# No daylight savings (UTC +10)
		config["hour_offset"] = 14
		config["time_offset"] = 36000
		helper.write_file("config.json", config)
		
	elif mode == "on":
		# Daylight savings time (UTC +11)
		config["hour_offset"] = 13
		config["time_offset"] = 39600
		helper.write_file("config.json", config)
		

#################### Redemption Code #####################################

# Add redemption code to code.json
# redemption_code, game, expiry (string)
# Return: error string or [redemption url, expiry_unix]
def add_code(code, game, expiry, reward):
	code = code.upper()
	data = helper.read_file("codes.json")

	# Check duplicate
	if code in data[game]:
		return code + " has already been added."
	
	# Fix expiry string timezone to match format
	expiry_unix = None
	if expiry == None:
		expiry_unix = 2147400001
	else:
		expiry_unix = helper.text_to_date(expiry)

	# Make redemption url
	if game == "genshin":
		url = "https://genshin.hoyoverse.com/en/gift?code=" + code
	elif game == "hsr":
		url = "https://hsr.hoyoverse.com/gift?code=" + code
	elif game == "zzz":
		url = "https://zenless.hoyoverse.com/redemption?code=" + code
	else:
		url = None

	data[game][code] = {
		"link": url,
		"expiry": expiry_unix,
		"reward": reward
	}

	helper.write_file("codes.json", data)
	return [url, expiry_unix]
	

# Remove redemption code from code.json
# redemption_code, game
# Return: outcome string
def remove_code(code, game):
	code = code.upper()
	data = helper.read_file("codes.json")

	# Check duplicate
	if code in data[game]:
		del data[game][code]
		helper.write_file("codes.json", data)
		return code + " has been removed successfully."
	else:
		return code + " does not exist."


# List redemption codes with filters
# game, filter for expiry (bool/None)
# Return: List of dictionary{game, code, expiry, reward}
def list_codes(game, is_expired):
	data = helper.read_file("codes.json")
	
	# Filter 1: by game
	filtered1 = []
	for g in data:
		for code in data[g]:
			entry = {
				"game": game_to_long(g),
				"code": code,
				"expiry": data[g][code]["expiry"],
				"reward": data[g][code]["reward"]
			}
			if game == "all" or game == g:
				filtered1.append(entry)
	
	# Filter 2: expired / unexpired / all
	filtered2 = []
	if is_expired == True:
		filtered2 = [x for x in filtered1 if x["expiry"] < time.time()]
			
	elif is_expired == False:
		filtered2 = [x for x in filtered1 if x["expiry"] > time.time()]

	else:
		filtered2 = filtered1
	
	# Remove expiry time from codes with no expiry or convert to discord timestamp
	# Change reward to printable format
	for entry in filtered2:
		if entry["reward"] != "":
			entry["reward"] = entry["reward"]
		
		if entry["expiry"] > 2147400000:
			entry["expiry"] = ""
		else:
			entry["expiry"] = "Expires <t:" + str(entry["expiry"]) + ":f> | "
	
	return filtered2


# Display redemption code list in embeds
# game full name, game abbreviation, filter for expiry (bool/None), embed field number
# Return: List of embeds
def display_code_list(game_long, game_short, is_expired, page_size):
	result = list_codes(game_short, is_expired)
	result.reverse()
	
	embed_1 = discord.Embed(title=game_long + " Redemption Codes", color=0x61dfff)
	embed_2 = discord.Embed(title=game_long + " Redemption Codes", color=0x61dfff)
	embed_3 = discord.Embed(title=game_long + " Redemption Codes", color=0x61dfff)
	embed_unused = discord.Embed(title=game_long + " Redemption Codes", color=0x61dfff)

	embed_1.set_thumbnail(url=helper.game_thumbnail(game_short))
	embed_2.set_thumbnail(url=helper.game_thumbnail(game_short))
	embed_3.set_thumbnail(url=helper.game_thumbnail(game_short))

	embeds = [embed_1]
	for no, entry in enumerate(result):
		if no < page_size:
			embed_1.add_field(name=entry["code"], value=entry["expiry"] + entry["reward"], inline=False)
		elif no < page_size * 2:
			embeds.append(embed_2) if embed_2 not in embeds else None
			embed_2.add_field(name=entry["code"], value=entry["expiry"] + entry["reward"], inline=False)
		elif no < page_size * 3:
			embeds.append(embed_3) if embed_3 not in embeds else None
			embed_3.add_field(name=entry["code"], value=entry["expiry"] + entry["reward"], inline=False)
		else:
			embed_unused.add_field(name=entry["code"], value=entry["expiry"] + entry["reward"], inline=False)

	return embeds

	
# Turns game abbreviated name to full form
# Shorthand game
# Return: Full name game
def game_to_long(game):
	if game == "genshin":
		return "Genshin Impact",
	elif game == "hsr":
		return "Honkai Star Rail",
	elif game == "zzz":
		return "Zenless Zone Zero",
	elif game == "tot":
		return "Tears of Themis",
	elif game == "hi3":
		return "Honkai Impact 3",
	elif game == "wuwa":
		return "Wuthering Waves"


#################### Verification Code #####################################

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
	zid = None
	unsw = False
	for index, word1 in enumerate(message_words):
		if "discord username" in word1.lower(): # Discord new username format
			username = message_words[index + 1].lower()

		if "email:" in word1.lower():
			email = message_words[index + 1].lower()

		if "your zid" in word1.lower() and message_words[index + 1].lower() != "z0000000":
			zid = message_words[index + 1].lower()
			student_email = zid + "@ad.unsw.edu.au"
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
	if user.id in config["user_blacklist"] or (zid != None and zid in config["user_blacklist"]):
		# Blacklisted user
		await message.reply("WARNING: <@" + str(user.id) + "> is on the blacklist.")
		return None

	'''
	# Security check: account age
	if time.mktime(user.created_at.timetuple()) > time.time() - 2592000:
		# Account is less than 1 month old
		await message.reply("WARNING: <@" + str(user.id) + "> account is less than 1 month old. Please manually send verification email with //send_code")
		return None
	'''
	
	config = helper.read_file("config.json")
	verification_level = config['verification_level']
	
	if verification_level == "low":
		# Verify immediately if verification level is set to low
		await add_verified(user)
		await message.add_reaction("✅")
	
	# Send verification supplied email
	elif email != None and verification_level == "medium":
		# Send verification to supplied email, auto verifies once code is entered
		verification_code = generate_code(user, email, True)
		is_sent = await send_verify_email(user, email, verification_code, True)
		if is_sent:
			await message.add_reaction("✅")

	elif email != None and verification_level == "high":
		# Send verification to email or student email, auto verifies for student email
		if unsw:
			email = student_email
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
	expiry = time.time() + 86400 # 24 hour expiry

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
	to_addr = email
	recipient = discord_user.name
	text = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="en">
<head>
<title></title>
<meta charset="UTF-8" />
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<!--[if !mso]>-->
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<!--<![endif]-->
<meta name="x-apple-disable-message-reformatting" content="" />
<meta content="target-densitydpi=device-dpi" name="viewport" />
<meta content="true" name="HandheldFriendly" />
<meta content="width=device-width" name="viewport" />
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no, url=no" />
<style type="text/css">
table {{
border-collapse: separate;
table-layout: fixed;
mso-table-lspace: 0pt;
mso-table-rspace: 0pt
}}
table td {{
border-collapse: collapse
}}
.ExternalClass {{
width: 100%
}}
.ExternalClass,
.ExternalClass p,
.ExternalClass span,
.ExternalClass font,
.ExternalClass td,
.ExternalClass div {{
line-height: 100%
}}
body, a, li, p, h1, h2, h3 {{
-ms-text-size-adjust: 100%;
-webkit-text-size-adjust: 100%;
}}
html {{
-webkit-text-size-adjust: none !important
}}
body, #innerTable {{
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale
}}
#innerTable img+div {{
display: none;
display: none !important
}}
img {{
Margin: 0;
padding: 0;
-ms-interpolation-mode: bicubic
}}
h1, h2, h3, p, a {{
line-height: inherit;
overflow-wrap: normal;
white-space: normal;
word-break: break-word
}}
a {{
text-decoration: none
}}
h1, h2, h3, p {{
min-width: 100%!important;
width: 100%!important;
max-width: 100%!important;
display: inline-block!important;
border: 0;
padding: 0;
margin: 0
}}
a[x-apple-data-detectors] {{
color: inherit !important;
text-decoration: none !important;
font-size: inherit !important;
font-family: inherit !important;
font-weight: inherit !important;
line-height: inherit !important
}}
u + #body a {{
color: inherit;
text-decoration: none;
font-size: inherit;
font-family: inherit;
font-weight: inherit;
line-height: inherit;
}}
a[href^="mailto"],
a[href^="tel"],
a[href^="sms"] {{
color: inherit;
text-decoration: none
}}
</style>
<style type="text/css">
@media (min-width: 481px) {{
.hd {{ display: none!important }}
}}
</style>
<style type="text/css">
@media (max-width: 480px) {{
.hm {{ display: none!important }}
}}
</style>
<style type="text/css">
@media (max-width: 480px) {{
.t36,.t41{{mso-line-height-alt:0px!important;line-height:0!important;display:none!important}}.t37{{padding-top:43px!important}}.t39{{border:0!important;border-radius:0!important}}.t25,.t31{{mso-line-height-alt:40px!important;line-height:40px!important}}
}}
</style>
<!--[if !mso]>-->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800&amp;display=swap" rel="stylesheet" type="text/css" />
<!--<![endif]-->
<!--[if mso]>
<xml>
<o:OfficeDocumentSettings>
<o:AllowPNG/>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
<![endif]-->
</head>
<body id="body" class="t44" style="min-width:100%;Margin:0px;padding:0px;background-color:#F9F9F9;"><div class="t43" style="background-color:#F9F9F9;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td class="t42" style="font-size:0;line-height:0;mso-line-height-rule:exactly;background-color:#F9F9F9;background-image:none;background-repeat:repeat;background-size:auto;background-position:center top;" valign="top" align="center">
<!--[if mso]>
<v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="true" stroke="false">
<v:fill color="#F9F9F9"/>
</v:background>
<![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" align="center" id="innerTable"><tr><td><div class="t36" style="mso-line-height-rule:exactly;mso-line-height-alt:70px;line-height:70px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t40" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="700" class="t39" style="background-color:#FFFFFF;border:1px solid #CECECE;overflow:hidden;width:700px;border-radius:20px 20px 20px 20px;">
<table class="t38" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t37" style="padding:50px 40px 40px 40px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100% !important;"><tr><td align="center">
<table class="t4" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="138" class="t3" style="width:138px;">
<table class="t2" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t1"><a href="#" style="font-size:0px;" target="_blank"><img class="t0" style="display:block;border:0;height:auto;width:100%;Margin:0;max-width:100%;" width="138" height="47.985611510791365" alt="" src="https://unswhoyosoc.org/wp-content/uploads/2024/02/hoyosoc-logo.png"/></a></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t5" style="mso-line-height-rule:exactly;mso-line-height-alt:40px;line-height:40px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t10" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="339" class="t9" style="width:339px;">
<table class="t8" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t7"><h1 class="t6" style="margin:0;Margin:0;font-family:Inter,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:28px;font-weight:600;font-style:normal;font-size:24px;text-decoration:none;text-transform:none;letter-spacing:-1.2px;direction:ltr;color:#111111;text-align:center;mso-line-height-rule:exactly;mso-text-raise:1px;">Hello {recipient}!</h1></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t12" style="mso-line-height-rule:exactly;mso-line-height-alt:17px;line-height:17px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t16" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="308" class="t15" style="width:308px;">
<table class="t14" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t13"><p class="t11" style="margin:0;Margin:0;font-family:Inter,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:500;font-style:normal;font-size:15px;text-decoration:none;text-transform:none;letter-spacing:-0.6px;direction:ltr;color:#424040;text-align:center;mso-line-height-rule:exactly;mso-text-raise:2px;">Your verification code (valid for 24 hours) is:</p></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t18" style="mso-line-height-rule:exactly;mso-line-height-alt:17px;line-height:17px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t22" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="308" class="t21" style="width:308px;">
<table class="t20" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t19"><p class="t17" style="margin:0;Margin:0;font-family:Inter,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:800;font-style:normal;font-size:20px;text-decoration:none;text-transform:none;letter-spacing:-0.6px;direction:ltr;color:#6774EB;text-align:center;mso-line-height-rule:exactly;mso-text-raise:1px;">{code}</p></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t25" style="mso-line-height-rule:exactly;mso-line-height-alt:17px;line-height:17px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t29" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="318" class="t28" style="width:318px;">
<table class="t27" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t26"><p class="t24" style="margin:0;Margin:0;font-family:Inter,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:500;font-style:normal;font-size:15px;text-decoration:none;text-transform:none;letter-spacing:-0.6px;direction:ltr;color:#424040;text-align:center;mso-line-height-rule:exactly;mso-text-raise:2px;">Use the code with the command <span class="t23" style="margin:0;Margin:0;font-weight:700;mso-line-height-rule:exactly;">/verify_me</span>.&nbsp;</p></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t31" style="mso-line-height-rule:exactly;mso-line-height-alt:17px;line-height:17px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr><tr><td align="center">
<table class="t35" role="presentation" cellpadding="0" cellspacing="0" style="Margin-left:auto;Margin-right:auto;"><tr><td width="318" class="t34" style="width:318px;">
<table class="t33" role="presentation" cellpadding="0" cellspacing="0" width="100%" style="width:100%;"><tr><td class="t32"><p class="t30" style="margin:0;Margin:0;font-family:Inter,BlinkMacSystemFont,Segoe UI,Helvetica Neue,Arial,sans-serif;line-height:22px;font-weight:500;font-style:normal;font-size:15px;text-decoration:none;text-transform:none;letter-spacing:-0.6px;direction:ltr;color:#424040;text-align:center;mso-line-height-rule:exactly;mso-text-raise:2px;">&nbsp;&#x9;&#x9;If your code has expired or you need further help with verification, please check the pinned FAQ in the &#x27;self-verify&#x27; channel before sending a message.</p></td></tr></table>
</td></tr></table>
</td></tr></table></td></tr></table>
</td></tr></table>
</td></tr><tr><td><div class="t41" style="mso-line-height-rule:exactly;mso-line-height-alt:70px;line-height:70px;font-size:1px;display:block;">&nbsp;&nbsp;</div></td></tr></table></td></tr></table></div><div class="gmail-fix" style="display: none; white-space: nowrap; font: 15px courier; line-height: 0;">&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;</div></body>
</html>
""".format(recipient=recipient, code=code)
	
	load_dotenv()
	password = os.getenv("EMAIL_PASS")

	msg = MIMEMultipart()

	msg['From'] = EMAIL_SENDER
	msg['To'] = to_addr
	bcc = ['verify.unswhoyosoc@gmail.com']
	msg['Subject'] = 'HoyoSoc Discord Verification'
	msg.attach(MIMEText(text, 'html'))

	try:
		# server = smtplib.SMTP("smtp.gmail.com", 587, None, 30)
		server = smtplib.SMTP(EMAIL_DOMAIN, EMAIL_PORT)
		server.ehlo()
		server.starttls()
		server.ehlo()
		server.login(EMAIL_SENDER, password)
		server.sendmail(EMAIL_SENDER, [to_addr] + bcc, msg.as_string())
		server.quit()
		
	except Exception as error:
		print("An exception occurred during emailing: ", error)
		return False

	# Send dm to remind user
	try:
		if send_remind:
			channel = await discord_user.create_dm()
			await channel.send("You have been sent a verification code at " + email + 
							   ". Please check your spam and bin if you cannot find the email.")
	except:
		print(discord_user.name + " cannot be sent a dm.")

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
	role2 = discord.utils.get(user.guild.roles, name="★☆★☆★☆ COSMETIC ☆★☆★☆★")
	role3 = discord.utils.get(user.guild.roles, name="★☆★☆★☆ ABOUT ☆★☆★☆★")
	role4 = discord.utils.get(user.guild.roles, name="★☆★☆★☆ MISC ☆★☆★☆★")
	role5 = discord.utils.get(user.guild.roles, name="Unverified")
	role6 = discord.utils.get(user.guild.roles, name="New Member")
	if role1 == None or role2 == None or role3 == None or role4 == None or role5 == None or role6 == None:
		return

	await user.add_roles(role1)
	await user.add_roles(role2)
	await user.add_roles(role3)
	await user.add_roles(role4)
	await user.add_roles(role6)

	# New Member role expiry
	helper.get_user_entry(str(user.id))
	data = helper.read_file("users.json")
	user_entry = data.get(str(user.id))
	user_entry["role"]["New Member"] = time.time() + NEWCOMER_EXPIRY
	helper.write_file("users.json", data)
	
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