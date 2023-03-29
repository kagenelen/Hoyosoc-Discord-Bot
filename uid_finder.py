import re

import helper


# Save given uid to user's entry in database
# Argument: discord id, uid
# Return: False if invalid uid
def save_uid(discord_id, uid):
  user = helper.get_user_entry(discord_id)
  data = helper.read_file("users.json")

  # Check valid uid
  if (int(uid) < 100000000 or int(uid) > 999999999):
    return False

  if uid not in user["uids"]:
    user["uids"].append(uid)

  data[discord_id] = user
  helper.write_file("users.json", data)
  return True


# Remove given uid from user's entry in database
# Argument: discord id, uid
# Return: False if uid not found
def remove_uid(discord_id, uid):
  user = helper.get_user_entry(discord_id)
  data = helper.read_file("users.json")

  if user["uids"].remove(uid) == False:
    return False

  data[discord_id] = user
  helper.write_file("users.json", data)
  return True


# Find all uids for a given user
# Argument: discord id
# Return: False if not uid found, uid list as string
def find_uid(discord_id):
  user = helper.get_user_entry(discord_id)

  if len(user["uids"]) == 0:
    return False

  return ", ".join(user["uids"])


# Read through message history in channel and add uid to database
# Argument:
# Return:
async def scrape_uid(target_channel):
  async for message in target_channel.history(limit=500):
    search_res1 = re.findall(r"\s\d{9}", message.content)

    if search_res1 != None:
      for uid in search_res1:
        save_uid(str(message.author.id), uid.strip())
        print(uid + " added for user " + message.author.name + " " +
              str(message.author.id))
