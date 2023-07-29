import discord

import minigame

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