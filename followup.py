import discord
from discord.ui import Button, View
import time

import minigame
import helper

async def hit_followup(interaction):
	res = minigame.blackjack_action(interaction.user.id, "hit")

	if isinstance(res, str):
		await interaction.edit_original_response(content=res)
		return

	embed = discord.Embed(title=interaction.user.display_name +
							"\'s Blackjack Game",
							description=res[0],
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.avatar.url)

	dealer_value = str(minigame.blackjack_get_value(res[1]))
	better_value = str(minigame.blackjack_get_value(res[2]))
	embed.add_field(name="Dealer's Hand: " + dealer_value,
					value=", ".join(res[1]),
					inline=False)
	embed.add_field(name="Your Hand: " + better_value,
					value=", ".join(res[2]),
					inline=False)

	await interaction.edit_original_response(embed=embed)

async def stand_followup(interaction):
	res = minigame.blackjack_action(interaction.user.id, "stand")

	if isinstance(res, str):
		await interaction.edit_original_response(content=res)
		return

	embed = discord.Embed(title=interaction.user.display_name +
							"\'s Blackjack Game",
							description=res[0],
							color=0x61dfff)
	embed.set_thumbnail(url=interaction.user.avatar.url)

	dealer_value = str(minigame.blackjack_get_value(res[1]))
	better_value = str(minigame.blackjack_get_value(res[2]))
	embed.add_field(name="Dealer's Hand: " + dealer_value,
					value=", ".join(res[1]),
					inline=False)
	embed.add_field(name="Your Hand: " + better_value,
					value=", ".join(res[2]),
					inline=False)

	await interaction.edit_original_response(embed=embed)

async def drop_followup(interaction, column):
	res = minigame.drop_token(interaction.user, column)

	embed = discord.Embed(title=res[4]["game_title"],
							description=res[2] + "\n\n" + minigame.render_board(res[1]),
							color=0x61dfff)

	token = "🔵"
	if res[4]["turn"] % 2 == 0:
		# Player 1
		token = "🔴"
	
	embed.add_field(name="Current Turn",
					value=res[3] + " " + token,
					inline=True)
	embed.add_field(name="Timeout",
					value="<t:" + str(int(time.time()) + 60) + ":R>",
					inline=True)

	# Buttons
	view = View(timeout=60)

	# Column 1
	col1_button = Button(label="1", row=0, style=discord.ButtonStyle.blurple)
	async def col1_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 0)
	col1_button.callback = col1_callback
	view.add_item(col1_button)

	# Column 2
	col2_button = Button(label="2", row=0, style=discord.ButtonStyle.blurple)
	async def col2_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 1)
	col2_button.callback = col2_callback
	view.add_item(col2_button)

	# Column 3
	col3_button = Button(label="3", row=0, style=discord.ButtonStyle.blurple)
	async def col3_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 2)
	col3_button.callback = col3_callback
	view.add_item(col3_button)

	# Column 4
	col4_button = Button(label="4", row=0, style=discord.ButtonStyle.blurple)
	async def col4_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 3)
	col4_button.callback = col4_callback
	view.add_item(col4_button)

	# Column 5
	col5_button = Button(label="5", row=1, style=discord.ButtonStyle.green)
	async def col5_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 4)
	col5_button.callback = col5_callback
	view.add_item(col5_button)

	# Column 6
	col6_button = Button(label="6", row=1, style=discord.ButtonStyle.green)
	async def col6_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 5)
	col6_button.callback = col6_callback
	view.add_item(col6_button)

	# Column 7
	col7_button = Button(label="7", row=1, style=discord.ButtonStyle.green)
	async def col7_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 6)
	col7_button.callback = col7_callback
	view.add_item(col7_button)

	if "win" in res[2] or "tie" in res[2]:
		await interaction.edit_original_response(embed=embed, view=None)
	else:
		await interaction.edit_original_response(embed=embed, view=view)

# Connect 4 game declined.
async def decline_connect4_followup(interaction):
	data = helper.read_file("minigame_session.json")
	data.pop(str(interaction.user.id))
	helper.write_file("minigame_session.json", data)
	await interaction.edit_original_response(content="Challenge declined.", view=None)
	
# Connect 4 game accepted. Print board.
async def start_connect4_followup(interaction, res):
	data = helper.read_file("minigame_session.json")
	session = data.get(str(interaction.user.id), None)
	
	embed = discord.Embed(title=session["game_title"],
							description=minigame.render_board(res[1]),
							color=0x61dfff)

	token = "🔵"
	if session["turn"] % 2 == 0:
		# Player 1
		token = "🔴"
	
	embed.add_field(name="Current Turn",
					value=session["player1_name"] + " " + token,
					inline=True)
	embed.add_field(name="Timeout",
					value="<t:" + str(int(time.time()) + 60) + ":R>",
					inline=True)

	# Buttons
	view = View(timeout=60)

	# Column 1
	col1_button = Button(label="1", row=0, style=discord.ButtonStyle.blurple)
	async def col1_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 0)
	col1_button.callback = col1_callback
	view.add_item(col1_button)

	# Column 2
	col2_button = Button(label="2", row=0, style=discord.ButtonStyle.blurple)
	async def col2_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 1)
	col2_button.callback = col2_callback
	view.add_item(col2_button)

	# Column 3
	col3_button = Button(label="3", row=0, style=discord.ButtonStyle.blurple)
	async def col3_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 2)
	col3_button.callback = col3_callback
	view.add_item(col3_button)

	# Column 4
	col4_button = Button(label="4", row=0, style=discord.ButtonStyle.blurple)
	async def col4_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 3)
	col4_button.callback = col4_callback
	view.add_item(col4_button)

	# Column 5
	col5_button = Button(label="5", row=1, style=discord.ButtonStyle.green)
	async def col5_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 4)
	col5_button.callback = col5_callback
	view.add_item(col5_button)

	# Column 6
	col6_button = Button(label="6", row=1, style=discord.ButtonStyle.green)
	async def col6_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 5)
	col6_button.callback = col6_callback
	view.add_item(col6_button)

	# Column 7
	col7_button = Button(label="7", row=1, style=discord.ButtonStyle.green)
	async def col7_callback(b_interaction):
		if b_interaction.user.id == res[0]:
			await b_interaction.response.defer()
			await drop_followup(b_interaction, 6)
	col7_button.callback = col7_callback
	view.add_item(col7_button)
	
	await interaction.edit_original_response(content="", embed=embed, view=view)
