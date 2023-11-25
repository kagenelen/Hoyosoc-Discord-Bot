import json
import discord
import re
import os
import time
import datetime
import shutil
import pytz

EXEC_ROLE = "2024 Hoyosoc Team"
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
			"gambling_loss": 0,
			"next_fortune": 0
		}
		data[discord_id] = user_entry
	
	write_file("users.json", data)
	return user_entry


# One time function for modifying database structure
# Modify this function to suit your need
def rewrite_structure():
	data = read_file("users.json")
	for user in data:
		if data[user].get("next_fortune", None) == None:
			data[user]["next_fortune"] = 0
		
	write_file("users.json", data)

	print("Database modification complete")


# Determines whether user is subcom or exec
# Argument: Interaction (class)
# Return: True if user is part of team, False otherwise
def is_team(interaction):
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


