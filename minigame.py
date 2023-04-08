import helper
import gambling

import math
import time
import random
'''
Minigames:
Guess the number
Blackjack
Coinflip
Hangman

Hangman TODO:
talent name
character dish
more terminology: darshan, inazuma commissions etc.
furniture name (evil)


'''

CARDS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "K", "Q"]
HM_NORMAL = 10
HM_HARD = 30
HM_EXTREME = 150


# Make new guess session. Where the number range is 0 - bet.
# Argument: discord id string, bet amount, self given attempts
# Return: outcome string
def new_guess(discord_id, bet, given_attempts):
  discord_id = str(discord_id)
  data = helper.read_file("minigame_session.json")

  if bet <= 10:
    return "Bets have to be higher than 10."

  max_attempts = int(math.ceil(math.log(bet, 2)))
  if given_attempts > max_attempts:
    return "The maximum allowed guesses for this bet is " + str(
      max_attempts) + "."

  winnings = int(bet * (1.3 + 0.5 * (max_attempts - given_attempts)))
  data[discord_id] = {
    "minigame": "number guess",
    "used_attempts": 0,
    "bet": bet,
    "target": random.randint(0, bet),
    "allowed_attempts": given_attempts,
    "winnings": winnings,
    "time": int(time.time())
  }

  if gambling.update_user_currency(discord_id, -1 * bet) == None:
    return "Insufficient primojems to make this bet."

  helper.write_file("minigame_session.json", data)
  return "You have 10 minutes to guess the correct number between 0 and " + str(
    bet) + " and earn " + str(winnings) + " primojems."


# Make a guess
# Argument: discord id string, guessed number
# Return: outcome string
def make_guess(discord_id, guess):
  discord_id = str(discord_id)
  data = helper.read_file("minigame_session.json")
  session = data.get(discord_id, None)

  if session == None or session["minigame"] != "number guess":
    return "No active session."

  if time.time() - session["time"] > 600:
    data.pop(discord_id)
    helper.write_file("minigame_session.json", data)
    return "Out of time."

  res = ""
  target = session["target"]
  if guess == target:
    # Correct
    gambling.update_user_currency(discord_id, session["winnings"])
    res = "Correct! You have earnt " + str(session["winnings"]) + " primojems!"
    data.pop(discord_id)
  elif guess < target:
    # Go higher
    session["used_attempts"] += 1
    remaining_attempts = session["allowed_attempts"] - session["used_attempts"]
    res = "Higher. You have " + str(remaining_attempts) + " attempts left."
  else:
    # Go lower
    session["used_attempts"] += 1
    remaining_attempts = session["allowed_attempts"] - session["used_attempts"]
    res = "Lower. You have " + str(remaining_attempts) + " attempts left."

  if session["used_attempts"] == session["allowed_attempts"]:
    res = "Out of attempts. The correct number is " + str(
      session["target"]) + "."
    data.pop(discord_id)

  helper.write_file("minigame_session.json", data)
  return res


# Make new blackjack session.
# Argument: discord id string, bet amount
# Return: [outcome string, [dealer cards], [your cards]] or error string
def new_blackjack(discord_id, bet):
  discord_id = str(discord_id)
  data = helper.read_file("minigame_session.json")
  dealer_hand = random.choices(CARDS, k=2)
  your_hand = random.choices(CARDS, k=2)

  if bet <= 0:
    return "Bets have to be higher than 0."

  data[discord_id] = {
    "minigame": "blackjack",
    "bet": bet,
    "dealer_hand": dealer_hand,
    "your_hand": your_hand
  }

  if gambling.update_user_currency(discord_id, -1 * bet) == None:
    return "Insufficient primojems to make this bet."

  outcome_string = ""
  if blackjack_get_value(your_hand) == 21:
    gambling.update_user_currency(discord_id, bet * 2)
    outcome_string = "You have won."
    data.pop(discord_id)
  elif blackjack_get_value(dealer_hand) == 21:
    outcome_string = "You have lost."
    data.pop(discord_id)

  helper.write_file("minigame_session.json", data)
  return [outcome_string, dealer_hand, your_hand]


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

  # Re-read the session file after hit and stand action
  data = helper.read_file("minigame_session.json")
  session = data.get(discord_id)

  outcome_string = ""
  if res == 1:
    gambling.update_user_currency(discord_id, session["bet"] * 2)
    outcome_string = "You have won " + str(session["bet"] * 2) + "."
    data.pop(discord_id)
  elif res == 2:
    gambling.update_user_currency(discord_id, session["bet"])
    outcome_string = "It\'s a tie, you get back " + str(session["bet"]) + "."
    data.pop(discord_id)
  elif res == -1:
    outcome_string = "You have lost."
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
  elif blackjack_get_value(session["your_hand"]) > 21:
    return -1

  return 0


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

  if gambling.update_user_currency(discord_id, -1 * bet) == None:
    return "Insufficient primojems to make this bet."

  flip_result = random.choices(["H", "T"], k=coin_amount)

  # Payout correct guess
  if flip_result.count("H") == head_amount:
    payout = int(
      bet * (1 / (math.comb(coin_amount, head_amount) / pow(2, coin_amount))))
    gambling.update_user_currency(discord_id, payout)
    return [flip_result, payout]
  else:
    return [flip_result, 0]


#Hangman #################################################################
''' 
Returns: [
    status,
    [args]
]
'''


# Create a new hangman session in minigame_session.json for that player
def new_hangman(discord_id, difficulty):

  discord_id = str(discord_id)
  difficulty = difficulty.lower()

  if difficulty == "normal":
    lives = 9
  elif difficulty == "hard":
    lives = 6
  elif difficulty == "extreme":
    lives = 3
  else:
    return [-1, ["Invalid difficulty..."]]

  minigame_session = helper.read_file("minigame_session.json")
  minigame_session[discord_id] = {
    "minigame": "hangman",
    "difficulty": difficulty,
    "lives": lives,
    "guessed_letters": "",
    "hangman_word": random.choice(helper.read_file("wordbank.json"))
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
      primojem = HM_EXTREME

    primojem = primojem * user_session["lives"]
    gambling.update_user_currency(discord_id, primojem)

    helper.write_file("minigame_session.json", minigame_session)
    return [
      2,
      [
        "You have guessed the word.", hidden_word, incorrect_letters,
        user_session["lives"], "You got " + str(primojem) + " primojems."
      ]
    ]
