import random
#TODO
#Set difficulty, easy, medium, hard
#incorporate gambling somehow maybe?
#decide payout
#Wordbank as a txt

# Idea
# No gambling (completely free)
# The less attempts you use, the more primojems you bet.
# I.e each attempt subtracts your winning
print("Genshin Hangman")
wordbank = ["venti", 'diluc'] 
word = random.choice(wordbank) 
attempts = 6 #difficulty
current = "" 
while attempts > 0:
    guess = input("\nEnter a letter: ").lower()
    if guess in word:
        print("Correct Guess!")
    else:
        attempts = attempts - 1
        print(f"Your guess {guess} is incorrect, {attempts} tries remaining!")
    current = current + guess
    wrong = 0
    for letter in word:
        if letter in current:
            print(f"{letter}",end="")
        else:
            print("_",end="")
            wrong = wrong + 1
    if wrong == 0:
        print("\nCongrats!")
        break
  
  
  
