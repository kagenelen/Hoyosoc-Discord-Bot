import bot
import os
import discord
import helper

# This file serves to restart the bot whenever it is rate limited
while __name__ == '__main__':
  try:
    bot.runbot()
  except discord.errors.HTTPException as e:
    print(" \n\n\nBLOCKED BY RATE LIMITS\n\n\n")
    os.system('kill 1')
