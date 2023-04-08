import helper

import datetime
import time
import discord
from operator import getitem

# ISSUE: Sometimes data doesn't get written because another function that uses write is called. This would overwrite the data.
# FIX: Call update user currency (or something similar) after write data
'''
TODO = Has a function stub written. Control + F to find it.
✓ = Finished coding in gambling.py
▢ = Not started at all

Functions we need:
▢ Daily check login streak bonus
✓ Daily check in to obtain currency
✓ Buy colour/roles (subscription based, you have to renew depending on duration)
✓ In bot.py, create an embed to see role shop items
✓ Create a bet for a this-or-that bracket, with specified option, specified end date for bet
✓ Submit a bet for a bracket, taking in bet amount and option as argument
▢ Minigames to earn currency
✓ Currency leaderboard
✓ Give x currency to list of discord tags (used for online event attendees)
✓ Give earnings to bet winners
✓ Role expiry checking, looping on daily basis
✓ View ongoing bets (end time has not passed)
✓ View your own bets
✓ Check inventory (price + role + role duration)
✓ In bot.py, equip and unequip roles that they own

For future if people still have interest in gambling:
▢ Gacha with currency. 3 star weapons and 4, 5 star characters. Occurence depends on rarity.
▢ Collect 3 of the same 5 star character to unlock their role icon.
▢ Trading stuff from gacha. (Or trading currency)
'''

TIME_OFFSET = 36000  # Don't use, it causes issues
ME = 318337790708547588
BET_LIMIT = 2000
ONE_WEEK_ROLE = 1500
ONE_MONTH_ROLE = 4500
PERMANENT_ROLE = 30000
CHECKIN = 150
PRIZE_POOL = 500
EVENT_ATTENDANCE = 1000
BOOSTER_DISCOUNT = 0.5
STREAK_MULTIPLIER = 5

############################# Functions that deal with bets #############################################


# Create a bet for a this-or-that bracket
# Argument: bracket identifier string, string of bracket candidates, end_time string
def create_bet(bracket_id, candidates, end_time):
	bracket_id = bracket_id.lower()

	# Convert candidate string to list
	candidate_list = [c.strip().lower() for c in candidates.split(",")]

	# Convert end_time string to unix. Expected format e.g. 4/12/2023 17:15
	end_time_dt = datetime.datetime.strptime(end_time, "%d/%m/%Y %H:%M")
	end_time_unix = time.mktime(end_time_dt.timetuple())

	# Create dictionary
	new_entry = {
	 "candidates": candidate_list,
	 "end_time": int(end_time_unix),
	 "bets": {}
	}

	# Add entry to bets.json
	data = helper.read_file("bets.json")
	data[bracket_id] = new_entry
	helper.write_file("bets.json", data)


# Submit a bet for a this-or-that bracket with nominated candidate
# Argument: discord_id of better, bracket identifer string, 1 chosen candidate, bet amount int
# Return: None if bet is valid, or error str for invalid bets
def submit_bet(discord_id, bracket_id, chosen_candidate, bet_amount):
	bracket_id = bracket_id.lower()
	discord_id = str(discord_id)
	data = helper.read_file("bets.json")
	bracket_entry = data.get(bracket_id, None)
	user_entry = helper.get_user_entry(discord_id)
	chosen_candidate = chosen_candidate.replace("‘", "'")

	if bracket_entry == None:
		# Invalid bracket id
		return "Invalid bracket id."

	if time.time() > bracket_entry["end_time"]:
		# Bet is no longer active
		return "Betting has already ended."

	if chosen_candidate.lower() not in bracket_entry["candidates"]:
		# Invalid candidate
		return "Invalid candidate."

	if bracket_entry["bets"].get(discord_id) != None:
		# Already betted
		return "You have already betted in this bracket."

	if bet_amount < 0 or bet_amount > BET_LIMIT or bet_amount > user_entry[
	  "currency"]:
		# Invalid bet amount
		return "Invalid bet. Bet is over the " + str(
		 BET_LIMIT) + " limit or you have insufficient currency."

	# Add bet to bracket entry
	bracket_entry["bets"][discord_id] = [bet_amount, chosen_candidate.lower()]
	helper.write_file("bets.json", data)
	update_user_currency(discord_id, -1 * bet_amount)


# Give currency to all winning bets of a bracket
# Argument: bracket identifier string, winning candidate string
# Return: List of winner's discord id or None if invalid bracket id
def give_bet_rewards(bracket_id, winning_candidate):
	bracket_id = bracket_id.lower()
	data = helper.read_file("bets.json")
	bracket_entry = data.get(bracket_id, None)

	if bracket_entry == None:
		# Invalid bracket id
		return None

	all_bets = [x[0] for x in list(bracket_entry["bets"].values())]
	total_bets = sum(all_bets) + PRIZE_POOL * len(all_bets)
	total_winner_bets = sum(x[0] for x in list(bracket_entry["bets"].values())
	                        if x[1] == winning_candidate)
	winners = []

	if total_winner_bets == 0:
		# Make sure division by 0 error does not occur if no winning bets
		return []

	# Reward winners by the fraction they contributed to bets out of the winners
	for user in bracket_entry["bets"]:
		if bracket_entry["bets"][user][1] == winning_candidate:
			earning = total_bets * (bracket_entry["bets"][user][0] / total_winner_bets)
			update_user_currency(user, earning)
			winners.append(user)

	return winners


# See which brackets you have betted on
# Argument: discord id string
# Return: List of (bracket id, amount, candidate) in order of most recent, max 5
def view_own_bets(discord_id):
	discord_id = str(discord_id)
	data = helper.read_file("bets.json")

	recent_bets = []
	counter = 0
	for bracket in data:
		betters = list(data[bracket]["bets"].keys())
		if discord_id in betters:
			this_bet = data[bracket]["bets"].get(discord_id)
			recent_bets.append([bracket] + this_bet)
			counter += 1
		if counter == 5:
			break

	recent_bets.reverse()
	return recent_bets


# See bets that are ongoing (end time not passed)
# Return: List of (bracket id, candidate list as string, end time as date string)
def view_ongoing_bets():
	data = helper.read_file("bets.json")

	ongoing_bets = []
	for bracket in data:
		if time.time() < data[bracket]["end_time"]:
			end_datetime = datetime.datetime.utcfromtimestamp(
			 data[bracket]["end_time"] + TIME_OFFSET).strftime('%d/%m/%Y')
			candidates = ", ".join(data[bracket]["candidates"])
			ongoing_bets.append([bracket, candidates.title(), end_datetime])

	return ongoing_bets


################## Functions that deal with user currency #############################################


# Change user's currency amount
# Arguments: discord_id, change by x amount
# Return: Currency amount or none if insufficient currency
def update_user_currency(discord_id, change):
	discord_id = str(discord_id)
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id, None)

	if user_entry["currency"] + change < 0:
		# Insufficient currency
		return None

	user_entry["currency"] = int(user_entry["currency"] + change)
	helper.write_file("users.json", data)
	return user_entry["currency"]


# Check user's currency amount
# Arguments: discord_id
# Return: Currency amount
def check_user_currency(discord_id):
	user_entry = helper.get_user_entry(discord_id)
	return user_entry["currency"]


# Get leaderboard for currency
# Return: List of (discord id, currency) in order
def get_leaderboard():
	data = helper.read_file("users.json")
	sorted_data = sorted(data.items(),
	                     key=lambda x: getitem(x[1], "currency"),
	                     reverse=True)

	leaderboard = []
	for user in sorted_data:
		# Prevent myself from appearing on the leaderboard
		if int(user[0]) != ME:
			leaderboard.append([user[0], user[1]["currency"]])

	return leaderboard


# Change multiple user's currency by amount
# Argument: Discord tag (Bob#1234) list as string, change by x amount, server object
# Return: Successful usernames
def update_user_list_currency(discord_list, change, server):
	usernames = [d.strip() for d in discord_list.split(",")]

	successful = []
	for u in usernames:
		username_parts = u.split("#")
		user = discord.utils.get(server.members,
		                         name=username_parts[0],
		                         discriminator=username_parts[1])
		if user != None:
			update_user_currency(user.id, change)
			successful.append(u)

	return successful


############################### Shop, checkin, roles, inventory ##############################################


# Give currency for user weekly checkin
# Argument: discord id string
# Return: [amount gained, streak], or None if checkin is still in cooldown
def currency_checkin(discord_id):
	discord_id = str(discord_id)
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id)

	# Check whether user checkin cooldown is over
	if time.time() < user_entry["next_checkin"]:
		return None

	# Check login streak still remains, and increment streak
	if user_entry["next_checkin"] + 86400 < time.time():
		user_entry["checkin_streak"] = 0
	else:
		user_entry["checkin_streak"] += 1
	amount_earned = CHECKIN + user_entry["checkin_streak"] * STREAK_MULTIPLIER

	# Set next checkin to tomorrow 12am
	today_date = datetime.datetime.now()
	tomorrow_date = today_date + datetime.timedelta(
	 hours=-today_date.hour, minutes=-today_date.minute, days=1)
	user_entry["next_checkin"] = int(time.mktime(tomorrow_date.timetuple()))

	helper.write_file("users.json", data)
	update_user_currency(discord_id, amount_earned)
	return [amount_earned, user_entry["checkin_streak"]]


# Check whether a user owns a role
# Argument: discord id string, role string
# Return: True/false
def is_role_owned(discord_id, role):
	user_entry = helper.get_user_entry(str(discord_id))

	return role.lower() in user_entry["role"]


# Get user's currency, roles, role duration
# Argument: discord id string
# Return: list[currency, (role1, duration1), ...]
def get_inventory(discord_id):
	discord_id = str(discord_id)
	user_entry = helper.get_user_entry(discord_id)

	# Convert unix to datetime string for each role
	role_items = list(user_entry["role"].items())
	roles = []
	for r in role_items:
		r_datetime = datetime.datetime.utcfromtimestamp(int(
		 r[1])).strftime('%d/%m/%Y')
		roles.append([r[0], r_datetime])

	inventory = [user_entry["currency"]] + roles
	return inventory


# Adds role to inventory or renew duration
# Argument: discord id string, role string, duration (7 or 30)
# Return: None if successful or error string
def buy_role(discord_id, role, duration, is_booster):
	discord_id = str(discord_id)
	duration = int(duration)
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id)

	# Determine cost
	price = 0
	if duration == 30:
		price = ONE_MONTH_ROLE
	elif duration == 7:
		price = ONE_WEEK_ROLE
	elif duration == 999:
		price = PERMANENT_ROLE
	else:
		# Invalid duration
		return "Invalid duration."

	# Server booster discount
	if is_booster:
		price = int(BOOSTER_DISCOUNT * price)

	if user_entry["currency"] < price:
		# Insufficient currency
		return "Insufficent primojem."

	if role.lower() not in [
	  "geo", "anemo", "electro", "pyro", "hydro", "cryo", "abyss", "dendro"
	]:
		return "Invalid role."

	# Update role duration
	current_end_time = user_entry["role"].get(role, int(time.time()))
	if duration == 7:
		user_entry["role"][role] = current_end_time + 604800
	elif duration == 30:
		user_entry["role"][role] = current_end_time + 2592000
	elif duration == 999:
		user_entry["role"][role] = 2145919483

	helper.write_file("users.json", data)
	update_user_currency(discord_id, -1 * price)


# Function called daily to check expiry of all roles, and remove role if expired
# Return: List of (discord id, role)
def check_role_expiry():
	data = helper.read_file("users.json")

	expired_roles = []
	for user in data:
		iter_list = list(data[user]["role"].items())
		for r in iter_list:
			if time.time() > r[1]:
				data[user]["role"].pop(r[0])
				expired_roles.append([user, r])

	helper.write_file("users.json", data)
	return expired_roles
