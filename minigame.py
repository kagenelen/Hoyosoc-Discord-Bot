import helper
import gambling
import minigame_helper

import math
import time
import random
import numpy

'''
Minigames:
Blackjack
Coinflip
Hangman
Counting game
Connect 4
'''

CARDS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "K", "Q"]
HM_NORMAL = 25 # 300 at max
HM_HARD = 50 # 400 at max
HM_EXTREME = 130 # 520 at max
TWO_WORD_PENALTY = 0.9615484 # 500 at max
THREE_WORD_PENALTY = 0.923086 # 480 at max
RANDOM_WORD_CHANCE = 0.5
EARNINGS_CAP = 50000
COUNT_MULTIPLER = 0.05
COUNT_MAX = 100 # Need 2000 to get this
COUNT_BONUS = 2 
ROW_COUNT = 6
COLUMN_COUNT = 7

minigame_earnings = {}

################### Blackjack ############################

# Make new blackjack session.
# Argument: discord id string, bet amount
# Return: [outcome string, [dealer cards], [your cards], allow_double bool] or error string
def new_blackjack(discord_id, bet):
	discord_id = str(discord_id)
	data = helper.read_file("minigame_session.json")
	dealer_hand = random.choices(CARDS, k=1)
	your_hand = random.choices(CARDS, k=2)
	allow_double = False
	
	if bet <= 0:
		return "Bets have to be higher than 0."
	
	data[discord_id] = {
		"minigame": "blackjack",
		"bet": bet,
		"dealer_hand": dealer_hand,
		"your_hand": your_hand
	}
	
	if gambling.check_user_currency(discord_id) - bet < 0:
		return "Insufficient primojems to make this bet."
	
	if gambling.check_user_currency(discord_id) - 2 * bet > 0:
		allow_double = True
		
	gambling.update_user_currency(discord_id, -1 * bet)
	
	outcome_string = ""
	if blackjack_get_value(your_hand) == 21:
		gambling.update_user_currency(discord_id, bet * 2)
		gambling.update_user_gambling(discord_id, bet)
		outcome_string = "You have won " + str(bet) + helper.PRIMOJEM_EMOTE
		data.pop(discord_id)
	elif blackjack_get_value(dealer_hand) == 21:
		gambling.update_user_gambling(discord_id, -1 * bet)
		outcome_string = "You have lost " + str(bet) + helper.PRIMOJEM_EMOTE
		data.pop(discord_id)
	
	helper.write_file("minigame_session.json", data)
	return [outcome_string, dealer_hand, your_hand, allow_double]


# Do an action in blackjack
# Argument: discord id string, action string
# Return: [outcome string, [dealer cards], [your cards]] or error string
def blackjack_action(discord_id, action):
	discord_id = str(discord_id)
	data = helper.read_file("minigame_session.json")
	session = data.get(discord_id, None)

	if session == None or session["minigame"] != "blackjack":
		return "No active session."

	res = 0
	if action == "hit":
		res = blackjack_hit(discord_id)
	elif action == "stand":
		res = blackjack_stand(discord_id)
	elif action == "double":
		res = blackjack_double(discord_id)

	# Re-read the session file after action
	data = helper.read_file("minigame_session.json")
	session = data.get(discord_id)

	outcome_string = ""
	if res == 1:
		gambling.update_user_currency(discord_id, session["bet"] * 2)
		gambling.update_user_gambling(discord_id, session["bet"])
		outcome_string = "You have won " + str(session["bet"]) + helper.PRIMOJEM_EMOTE
		data.pop(discord_id)
	elif res == 2:
		gambling.update_user_currency(discord_id, session["bet"])
		outcome_string = "It\'s a tie, you get back " + str(session["bet"]) + helper.PRIMOJEM_EMOTE
		data.pop(discord_id)
	elif res == -1:
		outcome_string = "You have lost " + str(session["bet"]) + helper.PRIMOJEM_EMOTE
		gambling.update_user_gambling(discord_id, -1 * session["bet"])
		data.pop(discord_id)

	helper.write_file("minigame_session.json", data)
	return [outcome_string, session["dealer_hand"], session["your_hand"]]


# Blackjack hit action
# Argument: discord id string
# Return: 0 no one won, 1 better won, -1 dealer won
def blackjack_hit(discord_id):
	discord_id = str(discord_id)
	data = helper.read_file("minigame_session.json")
	session = data.get(discord_id, None)
	
	# Better draw 1 card
	session["your_hand"].append(random.choice(CARDS))
	helper.write_file("minigame_session.json", data)
	
	# Check if better has won or lost
	if blackjack_get_value(session["your_hand"]) == 21:
		return 1
	elif len(session["your_hand"]) == 5 and blackjack_get_value(session["your_hand"]) < 21:
		# 5 card charlie rule
		return 1
	elif blackjack_get_value(session["your_hand"]) > 21:
		return -1
	
	return 0

# Blackjack double down
# Argument: discord id string
# Return: 0 insufficient bet, 1 better won, -1 dealer won, 2 tie
def blackjack_double(discord_id):
	discord_id = str(discord_id)
	data = helper.read_file("minigame_session.json")
	session = data.get(discord_id, None)
	
	# Double down can only happen on first action
	if len(session["your_hand"]) > 2:
		return 0

	# Double bet
	if gambling.check_user_currency(discord_id) - session['bet'] < 0:
		# Insufficient to double
		return 0
	gambling.update_user_currency(discord_id, -1 * session['bet'])
	session['bet'] += session['bet']

	# Better draw 1 card and stand
	session["your_hand"].append(random.choice(CARDS))
	helper.write_file("minigame_session.json", data)

	# Check if your double is a bust or blackjack
	if blackjack_get_value(session["your_hand"]) > 21:
		return -1
	if blackjack_get_value(session["your_hand"]) == 21:
		return 1

	# Player not bust, dealer must hit under 17 (not including 17)
	while blackjack_get_value(session["dealer_hand"]) < 17:
		session["dealer_hand"].append(random.choice(CARDS))
		helper.write_file("minigame_session.json", data)

    # Check if dealer has won or lost
	if blackjack_get_value(session["dealer_hand"]) == 21:
		return -1
	if blackjack_get_value(session["dealer_hand"]) > 21:
		return 1

	# Check if better has won or lost
	if blackjack_get_value(session["dealer_hand"]) > blackjack_get_value(session["your_hand"]):
		return -1
	elif blackjack_get_value(session["dealer_hand"]) == blackjack_get_value(session["your_hand"]):
		return 2
	else:
		return 1


# Blackjack stand action
# Argument: discord id string
# Return: 1 better won, -1 dealer won, 2 tie
def blackjack_stand(discord_id):
  discord_id = str(discord_id)
  data = helper.read_file("minigame_session.json")
  session = data.get(discord_id, None)

  # Dealer must hit under 17 (not including 17)
  while blackjack_get_value(session["dealer_hand"]) < 17:
    session["dealer_hand"].append(random.choice(CARDS))
    helper.write_file("minigame_session.json", data)

    # Check if dealer has won or lost
    if blackjack_get_value(session["dealer_hand"]) == 21:
      return -1
    if blackjack_get_value(session["dealer_hand"]) > 21:
      return 1

  # Check who has the higher value
  if blackjack_get_value(session["dealer_hand"]) > blackjack_get_value(
      session["your_hand"]):
    return -1
  elif blackjack_get_value(session["dealer_hand"]) == blackjack_get_value(
      session["your_hand"]):
    return 2
  else:
    return 1


# Get numerical value for a hand
# Argument: card list
# Return: hand value
def blackjack_get_value(hand):
  hand = ["10" if c == "J" or c == "Q" or c == "K" else c for c in hand]
  hand1 = ["1" if c == "A" else c for c in hand]
  hand2 = ["11" if c == "A" else c for c in hand]
  hand1 = [int(c) for c in hand1]
  hand2 = [int(c) for c in hand2]

  # Account for A can be 1 or 11
  hand1_value = sum(hand1)
  hand2_value = sum(hand2)
  if hand2_value <= 21:
    return hand2_value
  else:
    return hand1_value

################### Coinflip ############################

# Flip a certain amount of coins and guess amount of heads
# Argument: discord id string, coin amount, head amount, bet
# Return: [coin flip result as list, payout] or error string
def coinflip(discord_id, coin_amount, head_amount, bet):
	discord_id = str(discord_id)
	
	if bet <= 0:
		return "Bets have to be higher than 0."
	
	if coin_amount > 10:
		return "Coin amount has to be below or equal to 10."
	
	if coin_amount <= 0 or head_amount > coin_amount or head_amount < 0:
		return "Invalid coin or head amount."
	
	if gambling.check_user_currency(discord_id) - bet < 0:
		return "Insufficient primojems to make this bet."

	gambling.update_user_currency(discord_id, -1 * bet)
	
	flip_result = random.choices(["H", "T"], k=coin_amount)
	
	# Payout correct guess
	if flip_result.count("H") == head_amount:
		payout = int(math.ceil(
		  bet * (1 / (math.comb(coin_amount, head_amount) / pow(2, coin_amount)))))
		gambling.update_user_currency(discord_id, payout)
		gambling.update_user_gambling(discord_id, payout - bet)
		return [flip_result, payout]
	else:
		gambling.update_user_gambling(discord_id, -1 * bet)
		return [flip_result, 0]


################### Hangman ############################
''' 
Returns: [
    status,
    [args]
]
'''


# Create a new hangman session in minigame_session.json for that player
def new_hangman(discord_id, difficulty, fandom):
	discord_id = str(discord_id)
	hangman_word = random.choice(helper.read_encrypted_file("wordlist.json")[fandom])
	
	if difficulty == "normal":
		lives = 12
	elif difficulty == "hard":
		lives = 8
	elif difficulty == "extreme":
		lives = 4
		hangman_word = hangman_word.replace(" ", "")
	else:
		return [-1, ["Invalid difficulty..."]]
	
	minigame_session = helper.read_file("minigame_session.json")
	minigame_session[discord_id] = {
		"minigame": "hangman",
		"difficulty": difficulty,
		"lives": lives,
		"guessed_letters": "",
		"hangman_word": hangman_word,
		"message_id": None
	}
	helper.write_file("minigame_session.json", minigame_session)
	
	hidden_word = ""
	for letter in minigame_session[discord_id]["hangman_word"]:
		if letter == " ":
			hidden_word += "᲼᲼᲼"
		else:
			hidden_word += "\_ "
	
	return [
		0,
		[
			hidden_word,
			minigame_session[discord_id]["difficulty"],
			minigame_session[discord_id]["lives"],
		]
	]
	
	
	'''
	Returns: [
		status,
		[args]
	]
	'''


# Ends the hangman session
def hangman_gameOver(discord_id, user_session, minigame_session):
  minigame_session.pop(discord_id)
  helper.write_file("minigame_session.json", minigame_session)
  return [0, ["Oh no! You ran out of lives.", user_session["hangman_word"]]]


# Make a guess in a hangman session
def hangman_guess(discord_id, guess):
  guess = guess.lower()
  discord_id = str(discord_id)
  minigame_session = helper.read_file("minigame_session.json")
  user_session = minigame_session.get(discord_id, None)

  # Case 1: No active session
  if user_session == None or user_session["minigame"] != "hangman":
    return [-1, ["No active session."]]

  # Case 2: The guess is a final guess (length of guess is length of word)
  elif len(guess.replace(" ", "")) == len(user_session["hangman_word"].replace(
      " ", "")):
    # final guess is incorrect = gameover
    if guess.replace(
        " ", "") != user_session["hangman_word"].casefold().replace(" ", ""):
      return hangman_gameOver(discord_id, user_session, minigame_session)
    # final guess is correct
    else:
      for letter in guess:
        user_session["guessed_letters"] += letter

  # Case 3: The guess is invalid
  elif len(guess) != 1:
    return [
      -2, ["Guess ONE character...", "https://www.wikihow.com/Play-Hangman"]
    ]

  # Case 4: The guess is correct
  elif guess in user_session["hangman_word"].lower():
    guess_result = "Correct guess."

  # Case 5: The guess is incorrect
  else:
    if guess not in user_session["guessed_letters"]:
      user_session["lives"] -= 1
    if user_session["lives"] == 0:
      return hangman_gameOver(discord_id, user_session, minigame_session)
    guess_result = "Incorrect guess. You lose a life."
  user_session["guessed_letters"] += guess

  hidden_word = ""
  incorrect_letters = ""
  for letter in user_session["guessed_letters"]:
    if letter not in user_session["hangman_word"].lower(
    ) and letter not in incorrect_letters:
      incorrect_letters += letter

  for letter in user_session["hangman_word"]:
    if letter in user_session["guessed_letters"] or letter.lower(
    ) in user_session["guessed_letters"]:
      hidden_word += letter + " "
    elif letter == " ":
      hidden_word += "᲼᲼᲼"
    else:
      hidden_word += "\_ "

  if "_" in hidden_word:
    minigame_session[discord_id] = user_session
    helper.write_file("minigame_session.json", minigame_session)
    return [
      1, [
        guess_result,
        hidden_word,
        incorrect_letters,
        user_session["lives"],
      ]
    ]
  else:
    minigame_session.pop(discord_id)

    if user_session["difficulty"] == "normal":
      primojem = HM_NORMAL
    elif user_session["difficulty"] == "hard":
      primojem = HM_HARD
    else:
      word_length = len(user_session["hangman_word"])
      penalty = 1
      if word_length > 11:
        penalty = TWO_WORD_PENALTY
      if word_length > 16:
        penalty = THREE_WORD_PENALTY
      primojem = int(HM_EXTREME * penalty)

    primojem = primojem * user_session["lives"]
    curr_earnings = minigame_earnings.get(discord_id, 0)
    minigame_earnings[discord_id] = curr_earnings + primojem
    if minigame_earnings[discord_id] < EARNINGS_CAP:
      gambling.update_user_currency(discord_id, primojem)
      earnings_message = "You got " + str(primojem) + " primojems."
    else:
      earnings_message = "Daily earnings cap reached."
	

    helper.write_file("minigame_session.json", minigame_session)
    return [
      2,
      [
        "You have guessed the word.", user_session["hangman_word"], incorrect_letters,
        user_session["lives"], earnings_message
      ]
    ]

################### Counting game ############################
# Check whether number is valid
# Argument: message object
# Return: true/false or error message
def number_validity(message):
	data = helper.read_file("count.json")
	num = message.content.lower().strip()
	num = num.replace("\*", "x")
	num = num.replace("*", "x")
	num = num.replace("×", "x")

	# Solve math equation
	math_eq_res = None
	fun_bonus = 1
	if not num.isdigit():
		try:
			nsp = minigame_helper.NumericStringParser()
			math_eq_res = nsp.eval(num)
		except:
			pass

	# Ignore any non-equation, non word-number and non number
	if math_eq_res == None and not num.isdigit():
		return False
	elif math_eq_res != None and isinstance(math_eq_res, int):
		if str(math_eq_res) not in num and str(math_eq_res + 1) not in num and str(math_eq_res - 1) not in num:
			fun_bonus = COUNT_BONUS
		num = math_eq_res
			
	# Invalid number
	if data["next_valid_number"] != int(num):
		data["next_valid_number"] = 1
		data["last_user"] = 1
		helper.write_file("count.json", data)
		return "<@" + str(message.author.id) + "> incorrect! Resetting counting game..."

	# Double counting user
	if data["last_user"] == message.author.id:
		data["next_valid_number"] = 1
		data["last_user"] = 1
		helper.write_file("count.json", data)
		return "<@" + str(message.author.id) + "> You cannot make consecutive counts. Resetting counting game..."

	# Correct submission (except 1), increment count and reward primojem
	if int(num) != 1:
		primojem_reward = min(int(math.ceil(data["next_valid_number"] * COUNT_MULTIPLER)), COUNT_MAX) * fun_bonus
		curr_earnings = minigame_earnings.get(str(message.author.id), 0)
		minigame_earnings[str(message.author.id)] = curr_earnings + primojem_reward
		if minigame_earnings[str(message.author.id)] < EARNINGS_CAP:
			gambling.update_user_currency(message.author.id, primojem_reward)
	
	data["next_valid_number"] += 1
	data["last_user"] = message.author.id
	
	helper.write_file("count.json", data)
	return True

# Checks whether a message deleted is a counting game number
# Message object
# Return true if message deleted is a valid number, false otherwise
def counting_deletion_check(message):
	is_valid_count = False
	for react in message.reactions:
		# Valid numbers have react from this bot
		if react.me:
			is_valid_count = True

	return is_valid_count
	

################### Connect 4  ############################

# Start a new game of connect 4
# Arguments: inviter player user object, invited player user object, wager
# Return: error string or [current turn player's id, board]
def new_connect(inviter_player, invited_player, wager):
	inviter_player_id = str(inviter_player.id)
	invited_player_id = str(invited_player.id)
	helper.get_user_entry(inviter_player_id)
	helper.get_user_entry(invited_player_id)
	data = helper.read_file("minigame_session.json")
	users = helper.read_file("users.json")
	
	if wager < 0:
		return "Wager have to be higher or equal to 0."

	if (users.get(inviter_player_id, None)["currency"] - wager < 0 or 
		users.get(invited_player_id, None)["currency"] - wager < 0):
		return "One or both players does not have sufficient primojem."

	# Assign who is player 1 (going first) and player 2 (going second)
	player_order = random.sample([inviter_player, invited_player], 2)
	player1 = player_order[0]
	player2 = player_order[1]

	# Create board, 0 = no token, 1 = player 1 token, 2 = player 2 token
	board = numpy.zeros((6,7))
	
	data[inviter_player_id] = {
		"minigame": "connect",
		"wager": wager,
		"game_title": player1.display_name + " and " + player2.display_name + "\'s Connect 4 Game",
		"player1": player1.id,
		"player2": player2.id,
		"player1_name": player1.display_name,
		"player2_name": player2.display_name,
		"turn": 0,
		"timeout": int(time.time()) + 60,
		"board": board.tolist()
	}
	
	helper.write_file("minigame_session.json", data)
	return [player1.id, board]

# Drop token down a certain column
# Arguments: token dropper's user object, column number
# Return: [next turn player's id, numpy board, game status message, next turn player's name, session object]
def drop_token(token_dropper, col):
	game_id = find_connect4_game(token_dropper.id)
	if game_id == None:
		return
		
	data = helper.read_file("minigame_session.json")
	session = data.get(game_id, None)

	board = numpy.array(session["board"])
	status_message = ""

	piece = None
	if session["turn"] % 2 == 0 and token_dropper.id == session["player1"]:
		# Player 1's turn
		piece = 1
	elif session["turn"] % 2 == 1 and token_dropper.id == session["player2"]:
		# Player 2's turn
		piece = 2

	# Early return if player turn has timed out
	if time.time() > session["timeout"]:
		reward = session["wager"]
		
		if session["turn"] % 2 == 0:
			# Player 1 timeout, player 2 wins			
			status_message = (session["player1_name"] + " has timed out. " + session["player2_name"] + " wins! " + 
				str(reward) + helper.PRIMOJEM_EMOTE + " has been added to your inventory.")
			gambling.update_user_currency(session["player2"], 2 * reward)
		else:
			# Player 2 timeout, player 1 wins
			status_message = (session["player2_name"] + " has timed out. " + session["player1_name"] + " wins! " + 
				str(reward) + helper.PRIMOJEM_EMOTE + " has been added to your inventory.")
			gambling.update_user_currency(session["player1"], 2 * reward)
			
		gambling.update_user_currency(session["player1"], -reward)
		gambling.update_user_currency(session["player2"], -reward)
		data.pop(game_id)
		helper.write_file("minigame_session.json", data)
		return [None, board, status_message, None, session]

	# Drop the token
	if is_valid_location(board, col) and piece != None:
		row = get_next_open_row(board,col)
		if row == -1:
			status_message = "This column is full. Please choose another column."
		else:
			board[row][col]= piece
			session["board"] = board.tolist()
			session["turn"] += 1
			session["timeout"] = int(time.time()) + 60
			helper.write_file("minigame_session.json", data)
		
		if winning_move(board, piece):
			# There is 4 in a row
			reward = session["wager"]
			status_message = (token_dropper.display_name + " wins! " + 
				str(reward) + helper.PRIMOJEM_EMOTE + " has been added to your inventory.")
			gambling.update_user_currency(token_dropper.id, 2 * reward)
			gambling.update_user_currency(session["player1"], -reward)
			gambling.update_user_currency(session["player2"], -reward)
			data.pop(game_id)
			
		elif (session["turn"] == 42):
			# Board is full
			status_message = "The board is full. It's a tie."
			data.pop(game_id)
			
	elif piece == None:
		# Not their turn
		status_message = token_dropper.display_name + ", it is not your turn."
		
	else:
		# Invalid location
		status_message = "Invalid column."
			
	if session["turn"] % 2 == 0:
		# Player 1's turn
		next_turn = session["player1"]
		next_turn_name = session["player1_name"]
	else:
		# Player 2's turn
		next_turn = session["player2"]
		next_turn_name = session["player2_name"]

	
	
	helper.write_file("minigame_session.json", data)
	return [next_turn, board, status_message, next_turn_name, session]
 
def is_valid_location(board,col):
    #if this condition is true we will let the use drop piece here.
    #if not true that means the col is not vacant
	if col >= COLUMN_COUNT or col < 0:
		return False
	else:
		return True

# Check next empty row in a column
# Argument: numpy board, column number
# Return: empty row's number, -1 if column is full
def get_next_open_row(board,col):
	for r in range(ROW_COUNT):
		if board[r][col]==0:
			return r
	return -1

# Check connect 4 win condition
# Argument: numpy board, player number
# Return: True for win, False for no win
def winning_move(board, piece):
	# Check horizontal locations for win
	for c in range(COLUMN_COUNT-3):
		for r in range(ROW_COUNT):
			if board[r][c] == piece and board[r][c+1] == piece and board[r][c+2] == piece and board[r][c+3] == piece:
				return True
	
	# Check vertical locations for win
	for c in range(COLUMN_COUNT):
		for r in range(ROW_COUNT-3):
			if board[r][c] == piece and board[r+1][c] == piece and board[r+2][c] == piece and board[r+3][c] == piece:
				return True
	
	# Check positively sloped diaganols
	for c in range(COLUMN_COUNT-3):
		for r in range(ROW_COUNT-3):
			if board[r][c] == piece and board[r+1][c+1] == piece and board[r+2][c+2] == piece and board[r+3][c+3] == piece:
				return True
	
	# Check negatively sloped diaganols
	for c in range(COLUMN_COUNT-3):
		for r in range(3, ROW_COUNT):
			if board[r][c] == piece and board[r-1][c+1] == piece and board[r-2][c+2] == piece and board[r-3][c+3] == piece:
				return True

	return False

# Render the numpy 2d array to string and emotes
# Argument: numpy board
# Return: rendered board string
def render_board(board):
	flipped_board = numpy.flip(board,0) #Flip the board so that tokens are at the bottom
	rendered_board = ""
	
	for row in flipped_board:
		for col_num, col in enumerate(row):
			if col == 0:
				rendered_board += "⚫"
			if col == 1:
				rendered_board += "🔴"
			if col == 2:
				rendered_board += "🔵"
			if col_num == COLUMN_COUNT - 1:
				# End column, add newline
				rendered_board += "\n"

	rendered_board += "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣\n"

	return rendered_board

# Find id of the connect 4 game a player is in
# Argument: Player discord id
# Return: game id or None if not in any game
def find_connect4_game(discord_id):
	data = helper.read_file("minigame_session.json")

	# Loop seperately incase there is an abandoned game
	for session in data:
		if data[session]["minigame"] == "connect" and (data[session]["player2"] == discord_id or data[session]["player1"] == discord_id):
			return session

	return None

	
