import re

import helper


# Save given uid to user's entry in database
# Argument: discord id, uid, game
# Return: False if invalid uid
def save_uid(discord_id, uid, game):
	user = helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")

	# Check valid uid
	if game == "honkai":
		if int(uid) < 10000000 or int(uid) > 999999999:
			return False
	elif int(uid) < 100000000 or int(uid) > 1999999999:
		return False
	
	if uid not in user["uids"][game]:
		user["uids"][game].append(uid)
	
	data[discord_id] = user
	helper.write_file("users.json", data)
	return True


# Remove given uid from user's entry in database
# Argument: discord id, uid, game
# Return: False if uid not found
def remove_uid(discord_id, uid, game):
	user = helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	
	if uid in user["uids"][game]:
		user["uids"][game].remove(uid)
	else:
		return False
	
	data[discord_id] = user
	helper.write_file("users.json", data)
	return True


# Find all uids for a given user
# Argument: discord id
# Return: False if not uid found, uid list as string
def find_uid(discord_id):
	user = helper.get_user_entry(discord_id)

	merged_uids = user["uids"]["genshin"] + user["uids"]["hsr"] + \
		user["uids"]["honkai"] + user["uids"]["tot"] + user["uids"]["zzz"]
	
	if len(merged_uids) == 0:
		return False
	
	uid_list = ""
		
	if len(user["uids"]["genshin"]) != 0:
		uid_list += "Genshin Impact: " + ", ".join(user["uids"]["genshin"]) + "\n"
		
	if len(user["uids"]["hsr"]) != 0:
		uid_list += "Star Rail: " + ", ".join(user["uids"]["hsr"]) + "\n"

	if len(user["uids"]["honkai"]) != 0:
		uid_list += "Honkai Impact: " + ", ".join(user["uids"]["honkai"]) + "\n"

	if len(user["uids"]["tot"]) != 0:
		uid_list += "Tears of Themis: " + ", ".join(user["uids"]["tot"]) + "\n"

	if len(user["uids"]["zzz"]) != 0:
		uid_list += "Zenless Zone Zero: " + ", ".join(user["uids"]["zzz"]) + "\n"

	return uid_list

# Find which person an uid belongs to
# Argument: uid, game
# Return: discord id of owner or False if uid not registered, 
def whose_uid(uid, game):
	data = helper.read_file("users.json")
	for user in data:
		for user_uid in data[user]["uids"][game]:
			if user_uid == uid:
				return user
			
	return False


# Read through message history in channel and add uid to database
# Argument:
# Return:
async def scrape_uid(target_channel, game):
	async for message in target_channel.history(limit=500):
		search_res1 = re.findall(r"\b\d{9}\b", message.content)
	
		if game != "hsr" or game != "genshin":
			return False
	
		if search_res1 != None and message.author.id != 986446621468405852:
			for uid in search_res1:
				save_uid(str(message.author.id), uid.strip(), game)
				print(uid + " added for user " + message.author.name + " " +
							str(message.author.id))
