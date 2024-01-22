import helper
import misc

import datetime
import time
import discord
import random
import pytz
from operator import getitem

# ISSUE: Sometimes data doesn't get written because another function that uses write is called. This would overwrite the data.
# FIX: Call update user currency (or something similar) after write data
'''
▢ (maybe) Shop items that doubles primojem earnt from this-or-that 

'''

TIME_OFFSET = 36000 # not daylight saving
HOUR_OFFSET = 13 # daylight saving 13, not daylight saving 14
BET_LIMIT = 5000
AUCTION_INCREMENT = 1.05
ONE_WEEK_ROLE = 800
PERMANENT_ROLE = 30000
CHECKIN = 150
CHECKIN_CAP = 1000
INITIAL_POOL = 5000 # Normally 2000
PRIZE_POOL = 500
PRIZE_POOL_PERCENT = 2 # Normally 1.5
EVENT_ATTENDANCE = 1000
BOOSTER_DISCOUNT = 0.5
STREAK_MULTIPLIER = 5
ONE_PULL = 160
FIVE_STAR_RARITY = 6
FOUR_STAR_RARITY = 50
THREE_STAR_RARITY = 944
FIVE_STAR_DUP = 25
FOUR_STAR_DUP = 5
THREE_STAR_DUP = 1
FIVE_STAR_COST = 180
FOUR_STAR_COST = 34

############################# Functions that deal with bets #############################################


# Create a bet for a this-or-that bracket
# Argument: bracket identifier string, string of bracket candidates, end_time string
def create_bet(bracket_id, candidates, end_time):
    bracket_id = bracket_id.lower()

    # Convert candidate string to list
    candidate_list = [c.strip().lower() for c in candidates.split(",")]

    # Convert end_time string to unix. Expected format e.g. 4/12/23 17:15
    end_time_dt = datetime.datetime.strptime(end_time, "%d/%m/%y %H:%M")
    end_time_unix = time.mktime(end_time_dt.timetuple()) - TIME_OFFSET

    # Create dictionary
    new_entry = {
        "candidates": candidate_list,
        "end_time": int(end_time_unix),
		"prize_pool": INITIAL_POOL,
		"message_id": None,
        "bets": {}
    }

    # Add entry to bets.json
    data = helper.read_file("bets.json")
    data[bracket_id] = new_entry
    helper.write_file("bets.json", data)


# Submit a bet for a this-or-that bracket with nominated candidate
# Argument: discord_id of better, bracket identifer string, 1 chosen candidate, bet amount int
# Return: [message_id, embed] if valid, or error str for invalid bets
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

	user_bet_entry = bracket_entry["bets"].get(discord_id)
	if user_bet_entry != None:
			# Already betted, update bet if bet is higher
		
			if user_bet_entry[0] < bet_amount and user_bet_entry[1] == chosen_candidate.lower():
				# Update bet to higher amount
				deduct_amount = bet_amount - user_bet_entry[0]
				user_bet_entry[0] = bet_amount
				bracket_entry["prize_pool"] += int(deduct_amount * PRIZE_POOL_PERCENT)

				if bet_amount <= 0 or bet_amount > BET_LIMIT or deduct_amount > user_entry["currency"]:
				# Invalid bet amount
					return "Invalid bet. Bet is over the " + str(BET_LIMIT) + " limit or you have insufficient currency."
		
				helper.write_file("bets.json", data)
				update_user_currency(discord_id, -1 * deduct_amount)
				return create_bet_message(bracket_id)
				
			elif user_bet_entry[0] >= bet_amount and user_bet_entry[1] == chosen_candidate.lower():
				# New bet is lower than previous
				return "To update your bet, you must bet higher than your previous bet of " + str(user_bet_entry[0])
				
			else:
				return "You may only update your previous bet on " + user_bet_entry[1]

	if bet_amount <= 0 or bet_amount > BET_LIMIT or bet_amount > user_entry["currency"]:
			# Invalid bet amount
			return "Invalid bet. Bet is over the " + str(BET_LIMIT) + " limit or you have insufficient currency."
	
	# Add bet to bracket entry
	bracket_entry["bets"][discord_id] = [bet_amount, chosen_candidate.lower()]
	bracket_entry["prize_pool"] += int(max(bet_amount + PRIZE_POOL, bet_amount * PRIZE_POOL_PERCENT))
	helper.write_file("bets.json", data)
	update_user_currency(discord_id, -1 * bet_amount)

	return create_bet_message(bracket_id)


# Give currency to all winning bets of a bracket
# Argument: bracket identifier string, winning candidate string
# Return: [total reward distributed, winner amount] or None if invalid bracket id
def give_bet_rewards(bracket_id, winning_candidate):
	bracket_id = bracket_id.lower()
	data = helper.read_file("bets.json")
	bracket_entry = data.get(bracket_id, None)
	
	if bracket_entry == None:
		# Invalid bracket id
		return None
	
	# all_bets = [x[0] for x in list(bracket_entry["bets"].values())]
	# total_bets = sum(all_bets) + PRIZE_POOL * len(all_bets)
	total_bets = bracket_entry["prize_pool"]
	total_winner_bets = sum(x[0] for x in list(bracket_entry["bets"].values())
							if x[1] == winning_candidate)
	winners = []
	
	if total_winner_bets == 0:
		# Make sure division by 0 error does not occur if no winning bets
		return [total_bets, len(winners)]
	
	# Reward winners by the fraction they contributed to bets out of the winners
	for user in bracket_entry["bets"]:
		if bracket_entry["bets"][user][1] == winning_candidate:
			earning = total_bets * (bracket_entry["bets"][user][0] /
									total_winner_bets)
			update_user_currency(user, earning)
			winners.append([user, earning])
	
	return [total_bets, len(winners)]


# See which brackets you have betted on
# Argument: discord id string
# Return: List of (bracket id, amount, candidate) in order of most recent, max 5
def view_own_bets(discord_id):
	discord_id = str(discord_id)
	data = helper.read_file("bets.json")
	
	recent_bets = []
	for bracket in data:
		betters = list(data[bracket]["bets"].keys())
		if discord_id in betters:
			this_bet = data[bracket]["bets"].get(discord_id)
			recent_bets.append([bracket] + this_bet)
	
	recent_bets.reverse()
	return recent_bets[0:5:]


# See bets that are ongoing (end time not passed)
# Return: List of (bracket id, candidate list as string, end time as date string, current prize pool)
def view_ongoing_bets():
	data = helper.read_file("bets.json")
	
	ongoing_bets = []
	for bracket in data:
		if time.time() < data[bracket]["end_time"]:
			end_datetime = datetime.datetime.utcfromtimestamp(
				data[bracket]["end_time"] + TIME_OFFSET).strftime('%d/%m/%Y')
			candidates = ", ".join(data[bracket]["candidates"])
	
			# all_bets = [x[0] for x in list(data[bracket]["bets"].values())]
			# current_prize = sum(all_bets) + PRIZE_POOL * len(all_bets)
			current_prize = data[bracket]["prize_pool"]
	
			ongoing_bets.append(
				[bracket, candidates.title(), end_datetime, current_prize])
	
	return ongoing_bets

# Set message to keep track of a bet progress live
# Argument: bracket id, message id
def set_bet_message(bracket_id, message_id):
	data = helper.read_file("bets.json")
	
	data[bracket_id]["message_id"] = message_id
	helper.write_file("bets.json", data)

# Create an embed for bet progress (to be called everytime bracket is updated)
# Argument: bracket id
# Return: [message id, bet embed]
def create_bet_message(bracket_id):
	data = helper.read_file("bets.json")
	bracket_entry = data.get(bracket_id, None)

	embed = discord.Embed(title="Bracket ID: " + bracket_id, 
						description=str(bracket_entry["prize_pool"]) + helper.PRIMOJEM_EMOTE + " prize pool",
						color=0x61dfff)
	
	# Count number of bets and bet amount for each candidate
	for candidate in bracket_entry["candidates"]:
		bet_count = 0
		bet_amount = 0
		
		for bet in bracket_entry["bets"]:
			if bracket_entry["bets"][bet][1] == candidate:
				bet_count += 1
				bet_amount += bracket_entry["bets"][bet][0]

		# Count and amount finalised, create embed field
		embed.add_field(name=candidate.title(),
						value= helper.BETTER_EMOTE + " " + str(bet_count) + 
						" | " + helper.PRIMOJEM_EMOTE + " " + str(bet_amount),
						inline=False)
				
	return [bracket_entry["message_id"], embed]

# Automatically give payout after bracket vote time ends
# Argument: message id, bracket id, vote end time string
# Return: error string or None if successful
def add_auto_payout_bet(message_id, bracket_id, end_time):
	data = helper.read_file("bets.json")
	bracket_entry = data.get(bracket_id, None)

	if bracket_entry == None:
		return "Invalid bracket id."
	
	# Convert end_time string to unix. Expected format e.g. 4/12/23 17:15
	end_time_dt = datetime.datetime.strptime(end_time, "%d/%m/%y %H:%M")
	end_time_unix = time.mktime(end_time_dt.timetuple()) - TIME_OFFSET

	task_dict = {
		"bracket_id": bracket_id,
		"message_id": message_id
	}

	misc.create_task("vote", end_time_unix, task_dict)

# Function called when vote task is scheduled, auto payout bet from reacts
# Argument: bracket id, list of reactions
# Return: [give_bet_reward response, bracket id, winning candidate] or error string
def auto_payout_bet(bracket_id, reactions):
	data = helper.read_file("bets.json")
	bracket_entry = data.get(bracket_id, None)

	count_list = [x.count for x in reactions]

	# Check for vote ties
	if count_list.count(max(count_list)) > 1:
		print("Unable to payout " + bracket_id + " due to a tie.")
		return

	# Find which option has highest vote (assumes reaction list is in order)
	candidate_num = count_list.index(max(count_list))
	winning_candidate = bracket_entry["candidates"][candidate_num]

	print("Auto payout done for " + bracket_id + " " + winning_candidate)

	return give_bet_rewards(bracket_id, winning_candidate) + [bracket_id, winning_candidate]
	

################## Functions that deal with user currency #############################################


# Change user's currency amount
# Arguments: discord_id, change by x amount
# Return: Currency amount or none if insufficient currency
def update_user_currency(discord_id, change):
    discord_id = str(discord_id)
    helper.get_user_entry(discord_id)
    data = helper.read_file("users.json")
    user_entry = data.get(discord_id, None)

    if user_entry["currency"] >= 0 and user_entry["currency"] + change < 0:
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
# Argument: leaderboard category
# Return: List of (discord id, currency) in order or error string
def get_leaderboard(category):
	category = category.lower()
	if category not in ["currency", "gambling_profit", "gambling_loss","role_icon", "checkin_streak"]:
		return "Invalid category"
	
	data = helper.read_file("users.json")
	if category == "role_icon":
		sorted_data = sorted(data.items(),
							 key=lambda x: len(set(getitem(x[1], category))),
							 reverse=True)
	else:
		sorted_data = sorted(data.items(),
							 key=lambda x: getitem(x[1], category),
							 reverse=True)
	
	leaderboard = []
	for user in sorted_data:
		leaderboard.append([user[0], user[1][category]])
	
	return leaderboard


# Change multiple user's currency by amount
# Argument: Discord tag (Bob#1234) list as string, change by x amount, server object
# Return: Successful usernames
def update_user_list_currency(discord_list, change, server):
		if "\n" in discord_list:
			usernames = [d.strip() for d in discord_list.split("\n")]
		else:
			usernames = [d.strip() for d in discord_list.split(",")]
	
		successful = []
		for u in usernames:
				username_parts = u.split("#")
				if len(username_parts) == 1: # New username format
					user = discord.utils.get(server.members,
																	 name=username_parts[0].lower())
				else: # Old username format
					user = discord.utils.get(server.members,
																	 name=username_parts[0],
																	 discriminator=username_parts[1])
				if user != None:
						update_user_currency(user.id, change)
						successful.append(u)
	
		return successful


# Change all user's currency by amount
def update_all_currency(change):
    data = helper.read_file("users.json")

    for u in data:
        if data[u]["currency"] > 0:
            update_user_currency(u, change)

    print("Compensation given.")

# Update user gambling profit/loss value
# Arguments: discord_id, primojem change by x amount
def update_user_gambling(discord_id, change):
	discord_id = str(discord_id)
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id, None)

	if change < 0:
		user_entry["gambling_loss"] = int(user_entry["gambling_loss"] - change)
	elif change > 0:
		user_entry["gambling_profit"] = int(user_entry["gambling_profit"] + change)
	
	helper.write_file("users.json", data)


########### Shop, checkin, roles, inventory ##############################################


# Give currency for user weekly checkin
# Argument: discord id string
# Return: [amount gained, streak, next checkin string], or next checkin countdown str if error
def currency_checkin(discord_id):
	discord_id = str(discord_id)
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id)
	
	# Check whether user checkin cooldown is over
	if time.time() < user_entry["next_checkin"]:
		return "<t:" + str(user_entry["next_checkin"]) + ":R>"
	
	# Check login streak still remains, and increment streak
	if user_entry["next_checkin"] + 86400 < time.time():
		user_entry["checkin_streak"] = 0
	else:
		user_entry["checkin_streak"] += 1
	amount_earned = min(CHECKIN + user_entry["checkin_streak"] * STREAK_MULTIPLIER, CHECKIN_CAP)
	
	# Set next checkin to tomorrow 12am AEST
	tomorrow_date = datetime.datetime.now() \
				.replace(hour=HOUR_OFFSET, minute=0, second=0, microsecond=0)
	user_entry["next_checkin"] = int(time.mktime(tomorrow_date.timetuple()))
	
	if user_entry["next_checkin"] < time.time():
		user_entry["next_checkin"] = user_entry["next_checkin"] + 86400
	
	helper.write_file("users.json", data)
	update_user_currency(discord_id, amount_earned)
	return [amount_earned, user_entry["checkin_streak"]]

# Freeze checkin until a certain date
# Argument: discord id string, resume date string (format 4/12/23)
# Return: next checkin timestamp, or error string
def freeze_checkin(discord_id, resume_time):
	discord_id = str(discord_id)
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id)

	# Check whether user checkin is broken to prevent people from restoring forgotten checkin
	if user_entry["next_checkin"] + 86400 < time.time():
		return "Check-in cannot be frozen until you have checked in today."
		
	# Convert resume_time string to unix. Expected format e.g. 4/12/23 17:15
	try:
		resume_time_dt = datetime.datetime.strptime(resume_time, "%d/%m/%y")
	except:
		return "Invalid format. Please use the format d/m/y. Example: 4/6/23 for June 4 2023."

	# Set next checkin to resume time at 12am
	resume_time_dt = resume_time_dt \
				.replace(hour=HOUR_OFFSET, minute=0, second=0, microsecond=0)
	next_checkin_unix = int(time.mktime(resume_time_dt.timetuple())) - 86400

	if next_checkin_unix < user_entry["next_checkin"]:
		checkin_str = "<t:" + str(user_entry["next_checkin"]) + ":f>"
		return "Resuming date cannot be before " + checkin_str + "."
	
	user_entry["next_checkin"] = next_checkin_unix

	helper.write_file("users.json", data)
	return "<t:" + str(user_entry["next_checkin"]) + ":f>"

# Gets daily fortune
# Argument: discord id
# Return: [fortune_level, fortune_message, fortune_colour]
def daily_fortune(discord_id):
	discord_id = str(discord_id)
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id)

	# Check whether user checkin cooldown is over
	if time.time() < user_entry["next_fortune"]:
		return "<t:" + str(user_entry["next_fortune"]) + ":R>"

	# Set next fortune to tomorrow 12am AEST
	tomorrow_date = datetime.datetime.now() \
				.replace(hour=HOUR_OFFSET, minute=0, second=0, microsecond=0)
	user_entry["next_fortune"] = int(time.mktime(tomorrow_date.timetuple()))

	if user_entry["next_fortune"] < time.time():
		user_entry["next_fortune"] = user_entry["next_fortune"] + 86400

	fortune_value = random.randint(0, 220)

	if fortune_value <= 50:
		# Very unlucky
		messages = ["Seems you're very unlucky today. If you gamble, you might go bankrupt.",
					"Seems you're very unlucky today. Watch out, a piano might fall on you.",
					"Seems you're very unlucky today. Did you break a mirror by accident?",
				   	"Seems you're very unlucky today. Perhaps someone stole your luck."]
		fortune_colour = 0x3b3b3b
		fortune_level = "Very unlucky. (" + str(fortune_value - 100) + ")"
	elif fortune_value <= 100:
		# Unlucky
		messages = ["A bit unlucky. You might pull a Qiqi.",
					"A bit unlucky. You might pull a Dehya.",
					"A bit unlucky. You might pull a Jean.",
					"A bit unlucky. You might pull a Diluc.",
					"A bit unlucky. You might pull a Mona.",
					"A bit unlucky. You might pull a Tighnari.",
					"A bit unlucky. You might pull a Keqing."]
		fortune_colour = 0xfd4869
		fortune_level = "Unlucky. (" + str(fortune_value - 100) + ")"
	elif fortune_value <= 120:
		# Neutral
		messages = ["Neither good or bad luck. Your fate is in your hands today.",
					"Neither good or bad luck. But I'm just a bot, so how would I know?",
					"Error 404: Your fortune is not found."]
		fortune_colour = 0x4cb6ff
		fortune_level = "Neutral. (0)"
	elif fortune_value <= 170:
		# Lucky
		fortune_primo = int(fortune_value * 1.84) + random.randint(-5, 5)
		messages = ["Lucky you! Perhaps you'll get more blue drops today.",
					"Lucky you! You might win your 50/50!",
					"Lucky you! You found " + str(fortune_primo) + helper.PRIMOJEM_EMOTE + " on the ground."]
		fortune_colour = 0x2ee518
		fortune_level = "Lucky. (" + str(fortune_value - 120) + ")"
	elif fortune_value == 220:
		# Ultimate luck
		fortune_primo = 5000
		messages = ["You found 5000" + helper.PRIMOJEM_EMOTE + " on the ground. How did you get so much luck?"]
		fortune_level = "Extremely lucky. (" + str(fortune_value - 120) + ")"
		fortune_colour = 0x2ee518
	else:
		# Very lucky
		fortune_primo = int(fortune_value * 2.84) + random.randint(0, 10)
		messages = ["Wow, you are so lucky! Maybe you'll pull a double 5 star!",
					"Wow, you are so lucky! Did you steal someone else's luck?",
			"Wow, you are so lucky you found " + str(fortune_primo) + helper.PRIMOJEM_EMOTE + " on the ground."]
		fortune_colour = 0xffda67
		fortune_level = "Very lucky. (" + str(fortune_value - 120) + ")"
		
		

	helper.write_file("users.json", data)

	fortune_message = random.choice(messages)
	if "ground" in fortune_message:
		update_user_currency(discord_id, fortune_primo)

	return [fortune_level, fortune_message, fortune_colour]

# Check whether a user owns a role
# Argument: discord id string, role string
# Return: True/false
def is_role_owned(discord_id, role):
    user_entry = helper.get_user_entry(str(discord_id))

    return role.title() in user_entry["role"] or role.title() in user_entry["role_icon"]


# Get user's currency, roles, role duration
# Argument: discord id string
# Return: list[currency, jemdust, [(role1, duration1), ...], 5_star_role_icons, 4_star_role_icons]
def get_inventory(discord_id):
	discord_id = str(discord_id)
	user_entry = helper.get_user_entry(discord_id)
	role_icon_file = helper.read_file("role_icon.json")
	
	# Convert unix to datetime string for each role
	role_items = list(user_entry["role"].items())
	roles = []
	for r in role_items:
		if r[1] == 2145919483:
			r_datetime = "Permanent"
		else:
			r_datetime = datetime.datetime.utcfromtimestamp(int(
				r[1])).strftime('%d/%m/%Y')
		roles.append([r[0], r_datetime])

	five_star_roles = []
	four_star_roles = []
	for role_icon in user_entry["role_icon"]:
		if role_icon in role_icon_file["5"]:
			five_star_roles.append(role_icon)

		if role_icon in role_icon_file["4"]:
			four_star_roles.append(role_icon)
		
	inventory = [user_entry["currency"], user_entry["jemdust"], 
				 roles, ", ".join(five_star_roles), ", ".join(four_star_roles)]
	return inventory

# Admin add role to inventory["role"]
# Argument: target user discord id string, role string, expiry date string (format 4/12/23)
# Return: None if successful or error string
def modify_inventory(discord_id, role, expiry_date):
	discord_id = str(discord_id)
	role = role.title()
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id)

	# Get expiry date unix time
	if expiry_date.lower() == "permanent":
		expiry_unix = 2145919483
	else:
		try:
			expiry_dt = datetime.datetime.strptime(expiry_date, "%d/%m/%y")
			expiry_unix = int(time.mktime(expiry_dt.timetuple()))
		except:
			return "Invalid format. Please use the format d/m/y or 'permanent'. Example: 4/6/23 for June 4 2023."

	user_entry["role"][role] = expiry_unix
	helper.write_file("users.json", data)
	

# Adds role to inventory or renew duration
# Argument: discord id string, role string, duration (7 or permanent), server booster boolean
# Return: None if successful or error string
def buy_role(discord_id, role, duration, is_booster, recipient):
	discord_id = str(discord_id)
	role = role.title()
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	gacha_pool = helper.read_file("role_icon.json")
	user_entry = data.get(discord_id)

	if duration != None:
		duration = int(duration)

	# Determine whether it is role or role icon and the price
	primojem_price = 0
	jemdust_price = 0
	if role in gacha_pool["colour"]:
		if duration == 7:
			primojem_price = ONE_WEEK_ROLE
		elif duration == 5000:
			primojem_price = PERMANENT_ROLE
		elif duration == None:
			return "Please specify a duration for colour roles."
		else:
			return "Invalid duration."

		if is_booster and recipient == None:
			primojem_price = int(BOOSTER_DISCOUNT * primojem_price)
			
	elif role in gacha_pool["5"]:
		jemdust_price = FIVE_STAR_COST
	
	elif role in gacha_pool["4"]:
		jemdust_price = FOUR_STAR_COST
		
	else: 
		return "Invalid role."
	
	if user_entry["currency"] < primojem_price or user_entry["jemdust"] < jemdust_price:
		# Insufficient currency
		return "Insufficent primojem or jemdust."
	
	# Update role duration
	if recipient == None:
		current_end_time = user_entry["role"].get(role, int(time.time()))
		if user_entry["role"].get(role, 0) == 2145919483 or role in user_entry["role_icon"]:
			return "You already have this permanent role."

		if jemdust_price != 0:
			user_entry["role_icon"].append(role)
		elif duration == 7:
			user_entry["role"][role] = current_end_time + 604800
		elif duration == 5000:
			user_entry["role"][role] = 2145919483
		
	else:
		# Gifting the role
		helper.get_user_entry(str(recipient.id))
		recipient_entry = data.get(str(recipient.id))
		current_end_time = recipient_entry["role"].get(role, int(time.time()))
		if recipient_entry["role"].get(role, 0) == 2145919483:
			return "The recipient already have this permanent role."

		if jemdust_price != 0:
			recipient_entry["role_icon"].append(role)
		elif duration == 7:
			recipient_entry["role"][role] = current_end_time + 604800
		elif duration == 5000:
			recipient_entry["role"][role] = 2145919483

	user_entry["jemdust"] += -1 * jemdust_price
	helper.write_file("users.json", data)
	update_user_currency(discord_id, -1 * primojem_price)


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

############## Gacha ################################

# Do some amount of pulls
# Argument: discord id string, number of pulls, server booster boolean
# Return: Obtained character/weapons in a list or error string
def gacha(discord_id, pull_amount, is_booster):
	discord_id = str(discord_id)
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(discord_id)
	
	if pull_amount < 1 or pull_amount > 10:
		return "Invalid pull amount. Valid range is 1 - 10."
		
	# Determine cost and apply server booster discount if applicable
	price = pull_amount * ONE_PULL
	if is_booster:
		price = int(BOOSTER_DISCOUNT * price)
	
	if user_entry["currency"] < price:
		# Insufficient currency
		return "Insufficent primojem."
	
	gacha_pool = helper.read_file("role_icon.json")
	
	# Determine rarity sequence
	rarity_sequence = random.choices(("5", "4", "3"), 
		weights=(FIVE_STAR_RARITY, FOUR_STAR_RARITY, THREE_STAR_RARITY), k=pull_amount)

	# Determine jemdust sequence for rarity sequence
	jemdust_sequence = [25 if x == "5" else 5 if x == "4" else 1 for x in rarity_sequence]
	
	# Determine the character/weapon for each rarity in sequence
	gacha_items = []
	for rarity in rarity_sequence:
		gacha_items.append(random.choice(gacha_pool[rarity]))

	# Add obtained character/weapon to inventory
	gacha_res = []
	for index, item in enumerate(gacha_items):
		if item not in user_entry["role_icon"] and item not in gacha_pool["3"]:
			user_entry["role_icon"].append(item)
			gacha_res.append([item, "🎊 NEW 🎊"])
		else:
			# Give jemdust for duplicate/3 star 
			user_entry["jemdust"] += jemdust_sequence[index]
			gacha_res.append([item, str(jemdust_sequence[index]) + " <:Jemdust:1108591111649362043>"])

	helper.write_file("users.json", data)
	update_user_currency(discord_id, -1 * price)
	return gacha_res

# Destroy a role icon for jemdust
# Arguments: discord id string, role icon str
# Return: Obtained jemdust amount or None if invalid role icon
def scrap_role_icon(discord_id, role):
	helper.get_user_entry(discord_id)
	data = helper.read_file("users.json")
	user_entry = data.get(str(discord_id))
	
	role = role.title()
	if not is_role_owned(discord_id, role):
		return None

	jemdust_amount = 0
	gacha_pool = helper.read_file("role_icon.json")
	if role in gacha_pool["5"]:
		jemdust_amount = FIVE_STAR_DUP
		user_entry["role_icon"].remove(role)
	elif role in gacha_pool["4"]:
		jemdust_amount = FOUR_STAR_DUP
		user_entry["role_icon"].remove(role)
	else:
		return False

	user_entry["jemdust"] += jemdust_amount
	helper.write_file("users.json", data)
	return jemdust_amount

############## Auction ################################

# Create auction
# Argument: auction_id, end_time as date string, auction description string
def create_auction(auction_id, end_time, auction_description):
    auction_id = auction_id.lower()

    # Convert end_time string to unix. Expected format e.g. 4/12/23 17:15
    end_time_dt = datetime.datetime.strptime(end_time, "%d/%m/%y %H:%M")
    end_time_unix = time.mktime(end_time_dt.timetuple()) - TIME_OFFSET

    # Create dictionary
    new_entry = {
		"auction_description": auction_description,
        "highest_bid": 0,
		"highest_bidder": "986446621468405852",
		"bidder_name": "None",
        "end_time": int(end_time_unix),
		"message_id": None
    }

    # Add entry to auction.json
    data = helper.read_file("auction.json")
    data[auction_id] = new_entry
    helper.write_file("auction.json", data)

# Submit a bid for an auction
# Argument: bidder user object, auction_id, bid_amount int
# Return: [message_id, embed, highest_bidder, previous_bidder/None] if valid, or error str for invalid bids
def submit_bid(bidder, auction_id, bid_amount):
	auction_id = auction_id.lower()
	discord_id = str(bidder.id)
	data = helper.read_file("auction.json")
	auction_entry = data.get(auction_id, None)
	user_entry = helper.get_user_entry(discord_id)
	
	previous_bidder = auction_entry.copy()["highest_bidder"]
	minimum_next_bid = int(auction_entry["highest_bid"] * AUCTION_INCREMENT)
	
	if auction_entry == None:
		# Invalid auction id
		return "Invalid auction id."
	
	if time.time() > auction_entry["end_time"]:
		# Auction is no longer active
		return "This auction has already ended."
	
	if time.time() + 600 > auction_entry["end_time"]:
		# Extend time by 1 hour if there is sniping in the last 10 minutes
		auction_entry["end_time"] += 3600

	if auction_entry["highest_bid"] < bid_amount:
		if discord_id == auction_entry["highest_bidder"]:
			# Already the highest bidder, only deduct the difference
			deduct_amount = bid_amount - auction_entry["highest_bid"]
			auction_entry["highest_bid"] = bid_amount

			if deduct_amount > user_entry["currency"]:
			# Insufficient currency
				return "You have insufficient currency to make this bid."
	
			update_user_currency(discord_id, -1 * deduct_amount)
			
		else:
			# New highest bidder
			if bid_amount > user_entry["currency"]:
				# Insufficient currency
				return "You have insufficient currency to make this bid."

			# Anti-snipe measures. Different bidder must bid AUCTION_INCREMENT times more than highest
			if minimum_next_bid > bid_amount:
				return "Valid bids must be higher than " + str(minimum_next_bid) + " to prevent sniping."
			
			# Refund previous bidder
			update_user_currency(auction_entry["highest_bidder"], 1 * auction_entry["highest_bid"])

			# Update highest bid and bidder
			auction_entry["highest_bidder"] = discord_id
			auction_entry["highest_bid"] = bid_amount
			auction_entry["bidder_name"] = bidder.display_name
			update_user_currency(discord_id, -1 * bid_amount)
		
	else:
		return "Valid bids must be higher than current highest bid of " + str(auction_entry["highest_bid"])
	
	# Update auction json and auction message
	helper.write_file("auction.json", data)
	return create_auction_message(auction_id) + [previous_bidder]

# Set message to keep track of an auction
# Argument: auction id, message id
def set_auction_message(auction_id, message_id):
	data = helper.read_file("auction.json")
	
	data[auction_id]["message_id"] = message_id
	helper.write_file("auction.json", data)

# Create an embed for auction progress (to be called everytime auction is updated)
# Argument: auction id
# Return: [message id, bet embed, highest bidder id]
def create_auction_message(auction_id):
	data = helper.read_file("auction.json")
	auction_entry = data.get(auction_id, None)

	highest_bidder = auction_entry["highest_bidder"]
	
	embed = discord.Embed(title=auction_id.title(), 
						description=auction_entry["auction_description"] + "\n\n" + "Ending <t:" + str(auction_entry["end_time"]) + ":R>",
						color=0xccccff)

	# Embed field for highest bid and bid amount
	embed.add_field(name="Highest bidder: " + auction_entry["bidder_name"],
						value= str(auction_entry["highest_bid"]) + " " + helper.PRIMOJEM_EMOTE,
						inline=False)
				
	return [auction_entry["message_id"], embed, highest_bidder]
