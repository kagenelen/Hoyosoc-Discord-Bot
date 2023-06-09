import re

import helper


# Save given uid to user's entry in database
# Argument: discord id, uid, game
# Return: False if invalid uid
def save_uid(discord_id, uid, game):
	user = helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	
	# Check valid uid
	if (int(uid) < 100000000 or int(uid) > 999999999):
		return False
	
	if uid not in user["genshin_uids"] and game == "genshin":
		user["genshin_uids"].append(uid)
	
	if uid not in user["hsr_uids"] and game == "hsr":
		user["hsr_uids"].append(uid)
	
	data[discord_id] = user
	helper.write_file("users.json", data)
	return True


# Remove given uid from user's entry in database
# Argument: discord id, uid
# Return: False if uid not found
def remove_uid(discord_id, uid):
  user = helper.get_user_entry(discord_id)
  data = helper.read_file("users.json")

  if user["genshin_uids"].remove(uid) == False and user["hsr_uids"].remove(uid) == False:
    return False

  data[discord_id] = user
  helper.write_file("users.json", data)
  return True


# Find all uids for a given user
# Argument: discord id
# Return: False if not uid found, uid list as string
def find_uid(discord_id):
	user = helper.get_user_entry(discord_id)
	
	if len(user["genshin_uids"]) == 0 and len(user["hsr_uids"]) == 0:
		return False
	
	uid_list = ""
		
	if len(user["genshin_uids"]) != 0:
		uid_list += "Genshin Impact: " + ", ".join(user["genshin_uids"]) + "\n"
		
	if len(user["hsr_uids"]) != 0:
		uid_list += "Star Rail: " + ", ".join(user["hsr_uids"]) + "\n"

	return uid_list

# Find which person an uid belongs to
# Argument: uid, game
# Return: discord id of owner or False if uid not registered, 
def whose_uid(uid, game):
	data = helper.read_file("users.json")
	for user in data:
		if game == "genshin" and uid in data[user]["genshin_uids"]:
			return user
		if game == "hsr" and uid in data[user]["hsr_uids"]:
			return user
			
	return False


# Read through message history in channel and add uid to database
# Argument:
# Return:
async def scrape_uid(target_channel):
  async for message in target_channel.history(limit=500):
    search_res1 = re.findall(r"\b\d{9}\b", message.content)

    if search_res1 != None and message.author.id != 986446621468405852:
      for uid in search_res1:
        save_uid(str(message.author.id), uid.strip(), "hsr")
        print(uid + " added for user " + message.author.name + " " +
              str(message.author.id))
