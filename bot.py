import praw
from discord.ext import commands
import discord
import requests # this is for the mtg search
from fuzzywuzzy import fuzz
import asyncio
import os # I need this to use environment variables on heroku
import csv # this is to browse the core set

# Reddit variables
reddit = praw.Reddit(client_id = 'x4FICJQqO4D14g' , client_secret = 'i9kip94Qs6R4Kfy77XYzDuv0z8Q' , user_agent = 'Card fetcher for Collective.') # gives access to reddit
collective = reddit.subreddit('collectivecg') # gives access to the Collective subreddit

# discord variables
bot = commands.Bot(command_prefix='!')
embed = discord.Embed(title = "CollectiveCardFetcher Help", description = "here is a list of commands for the bot:" , color= 0x00FFFF)
embed.add_field(name = '!alive', value = 'The bot will respond with "im alive and well!"')
embed.add_field(name = '!server', value = "The bot will respond with a link that can be used to add him to a server. note: you need to be an admin in a server to add a bot.")
embed.add_field(name = '!github', value = "The bot will respond with a link to the github page of the bot.")
embed.add_field(name = '!nice' , value = 'The bot will respond with a "nice art!" picture.')
embed.add_field(name = '!good' , value = 'Ups the score of the bot. Will make the bot respond with a thankful message.')
embed.add_field(name = '!bad', value = 'Reduces the score of the bot. Will make the bot respond with an apologetic message.')
embed.add_field(name = '!score' , value = 'The bot will respond with the amount of votes given to him trough !bad and !good')
embed.add_field(name = '!image <link>' , value= 'Will return the art of the card linked.')
embed.add_field(name = '!new', value = 'Needs to be used with one of the following topics after: keys, turns, keywords, collection, links, heroes, restrictions, affinities or basics. will return an explanation about said topic')
embed.add_field(name = '!squidward' , value = 'The bot responds with a juicy nick meme about a squidward that summons 15 fortnite players.')
embed.add_field(name = '!excuseme' , value = 'Responds with the classic meme of "excuse me wtf".')
embed.add_field(name = '!leaderboard', value = 'Responds with an embed holding the value of the current leaderboard.')
bot.remove_command('help')

# functions
def get_card_name(text):
    '''takes a string and extracts card names from it. card names are encapsulated in [[xxxx]] where xxxx is the card name'''
    cards = [] # list of names of cards
    start = text.find('[[')
    while start != -1: # until there are no more brackets
        end = text.find(']]')
        if end == -1:
            return cards # if there is an opener but no closer then someone fucked up
        else:
            query = text[start + 2:end]
            if query.find(':') > 0:
                mod = query[:query.find(':')].lower()
                card = query[query.find(':')+1:]
                if mod not in POSSIBLE_MODS:
                    card = query
                    mod = 'none'
                cards.append((mod,card))
            else:
                cards.append(('none',query)) # gets the name of the card
        text = text[end+2 : ] # cuts out the part with the card
        start = text.find('[[') # and the circle begins anew
    return cards

def save_card(name , link):
    '''saves a link to a card picture with the name specified in the temp_cards.csv document'''
    with open('temp_cards.csv' , 'a') as temp_cards_file:
        temp_cards = csv.writer(temp_cards_file , delimiter = ',')
        temp_cards.writerow([name , link])

def load_core_set():
    '''loads the core set cards from core_set.csv into a dictionary called core_set'''
    core_set = {}
    for card_info in requests.get('https://server.collective.gg/api/public-cards/').json()['cards']:
        if card_info['imgurl'] is not None:
            core_set[card_info['name']] = card_info['imgurl']
    return core_set

def load_temp_cards():
    '''loads the temp saved cards from temp_cards.csv into a dictionary called temp_cards'''
    temp_cards = {}
    with open('temp_cards.csv' , 'r') as temp_cards_file:
        temp_cards_csv = csv.reader(temp_cards_file , delimiter = ',')
        for row in temp_cards_csv:
            if row != []: # there is a bug that adds empty lines .this prevent the program from crashing from it
                name , link = row # unpack the row into a name and a link
                temp_cards[name] = link # adds the card into the core_set dictionary
    return temp_cards

def load_stormbound_cards():
    cards = {}
    with open('card_list' , 'r') as fcard_list:
        card_list = csv.reader(fcard_list , delimiter = '%')
        for row in card_list:
            name , link = row
            cards[name] = link
    return cards

def load_eternal():
    cards = {}
    with open('eternal_list.csv' , 'r') as fcard_list:
        card_list = csv.reader(fcard_list , delimiter = ',')
        for row in card_list:
            name , link = row
            cards[name] = link
    return cards

def load_hs():
    cards = {}
    card_data = requests.get('https://api.hearthstonejson.com/v1/25770/enUS/cards.json').json()
    for card in card_data:
        if 'name' not in card:
            continue
        cards[card['name']] = card['id']
    return cards

def get_card():
    '''fetches the newest card from reddit'''
    for card in collective.new(limit = 1):
        return 'https://www.reddit.com' + card.permalink

async def repost_card(post_channel):
    last_card = get_card()
    while True:
        card = get_card()
        if card != last_card:
            last_card = card
            await bot.send_message(post_channel , card)
        await asyncio.sleep(10)

def get_core(card):
    max_ratio = (' ', 0)  # maximum score in ratio exam
    max_partial = (' ', 0)  # maximum sort in partial ratio exam
    list_ratio = []
    list_partial = []
    #lets put the core_set and temp_cards together
    search_list = temp_cards.copy()
    search_list.update(core_set)
    for entry in search_list:
        # lets check if an entry is "good enough" to be our card
        ratio = fuzz.ratio(card, entry)
        partial = fuzz.partial_ratio(card, entry)
        if ratio > max_ratio[1]:
            max_ratio = (entry, ratio)
            list_ratio = [max_ratio]
        elif ratio == max_ratio[1]:
            list_ratio.append((entry, ratio))
        if partial > max_partial[1]:
            max_partial = (entry, partial)
            list_partial = [max_partial]
        elif partial == max_partial[1]:
            list_partial.append((entry, partial))
    if max_partial[1] > max_ratio[1]:
        return search_list[max_partial[0]]
    return search_list[max_ratio[0]]

def get_mtg(card):
    '''sends a link to an image file of the mtg card'''
    # check scryfall api at scryfall website
    available = requests.get('https://api.scryfall.com/cards/named/', {'fuzzy': card}).json()
    if available['object'] == 'card':
        return 'https://api.scryfall.com/cards/named?fuzzy={};format=image;version=png'.format(card.replace(' ', '%20'))
    return "sorry, couldn't find {}. please try again.".format(card)

def get_from_set(card,set):
    max_ratio = (' ', 0)  # maximum score in ratio exam
    max_partial = (' ', 0)  # maximum sort in partial ratio exam
    for entry in set:
        # lets check if an entry is "good enough" to be our card
        ratio = fuzz.ratio(card, entry)
        partial = fuzz.partial_ratio(card, entry)
        if ratio > max_ratio[1]:
            max_ratio = (entry, ratio)
            list_ratio = [max_ratio]
        elif ratio == max_ratio[1]:
            list_ratio.append((entry, ratio))
        if partial > max_partial[1]:
            max_partial = (entry, partial)
            list_partial = [max_partial]
        elif partial == max_partial[1]:
            list_partial.append((entry, partial))
    if max_partial[1] > max_ratio[1]:
        return set[max_partial[0]]
    return set[max_ratio[0]]

def get_ygo(card):
    id = requests.get('https://db.ygoprodeck.com/similarcards2.php?name=' + card).text[2:-2]
    if id:
        return 'https://ygoprodeck.com/pics/'+id.split(',')[0].split(':')[1][1:-1]+'.jpg'
    else:
        return '{} was not found. please be more specific'.format(card)

def get_top(num , week):
    ret = []
    count = 0
    for post in collective.search('flair:(week ' + week + ')',limit = 1000, sort = 'top'):
        if (post.title.lower().startswith('[card') or post.title.lower().startswith('[update')) and count<num:
            ret.append(post.url+' | '+str(post.score)+' | '+str(int(post.upvote_ratio*100))+'%')
            count+=1
    return ret

# commands
@bot.command()
async def alive():
    await bot.say('im alive and well!')

@bot.command()
async def server():
     bot.say('https://discordapp.com/api/oauth2/authorize?client_id=465866501715525633&permissions=522304&scope=bot')

@bot.command()
async def github():
    await bot.say('https://github.com/fireasembler/CollectiveCardFetcher')

@bot.command(pass_context=True)
async def nice(ctx):
    await bot.send_file(ctx.message.channel, 'nice art.jpg')

@bot.command()
async def good():
    os.environ['GOOD'] = str(int(os.environ['GOOD']) + 1)
    await bot.say('thank you! :)')

@bot.command()
async def bad():
    os.environ['BAD'] = str(int(os.environ['BAD']) + 1)
    await bot.say('ill try better next time :(')

@bot.command()
async def score():
    await bot.say('good: ' + os.environ.get('GOOD'))
    await bot.say('bad: ' + os.environ.get('BAD'))

@bot.command()
async def new(link):
    if link == 'keys':
        await bot.say("Invite keys aren’t being given out currently, as the devs work on new player features. They will be available freely again in around 2 months’ time.\nIn the meantime, we have occasional Team Design Competitions. By participating (not winning) via teaming up with another player, you can get into the game. If you’d like, you can be put on a reminder list for if/when the next one happens.")
    elif link == 'collection':
        await bot.say("https://www.collective.gg/collection")
    elif link == 'turns':
        await bot.say("Each turn has two main phases. They are first the card/abilities phase, then the attack/block phase. At start of turn, each player first draws 1 card and gains 1 EXP.\n\nDuring the first phase, a player is assigned initiative, which alternates between players each turn. Players simultaneously play their cards and activate unit abilities (actives). Their decisions don't happen immediately, but go on a stack where they wait to be resolved, until both players finished making their choices. Then, starting with the player with initiative, all cards/abilities are resolved in the order they were selected in. After all of the effects of the cards/abilities of the initiative player resolves, then all of the non-initiative player's actions resolve. That ends the first phase.\n\nDuring the second phase, players again make simultaneous decisions that don't take effect until both have confirmed their choices. Attackers are selected first. After those choices are locked in, then defenders are selected. After defenders are locked in, combat happens. The initiative player's attackers deal their atk to their respective blockers' hp, or to the opponent's hp if unblocked. The attack value of a unit is dealt cumulatively to each defender, not the same amount to each. If an 1/2 attacker is blocked with two 1/1s, only one of the 1/1s will die. The order in which you select blocks is the order in which units block. This can lead to situations where a 1/2 is blocked with a vanilla 0/3 and a 1/1 deadly, and the deadly unit will kill the 1/2 without taking damage, because it was selected it to block second.")
    elif link == 'heroes':
        await bot.say('Collective is unique in utilizing Heroes and the EXP system as an integral part of gameplay. When you build a new deck, you do so under a hero of your choice, with that deck being bound to the hero and unable to be played with any other.  Heroes aren\'t actual units or cards, but act as a reward system through which you can receive a free unit on board, a spell in hand, or a passive ability that lasts for the duration of the game. Each hero (of which the game currently has four, with more planned) has 4 different rewards specific to them, provided sequentially when they "level up". Leveling up happens as certain EXP thresholds are reached within each match, which are reset once the match concludes, with the exact thresholds differing for each hero. EXP is attainable through three ways: One, at the beginning of each turn, each player gains 1 EXP. Two, each hero has a unique passive ability that triggers once per turn, and providing you with a set amount of EXP if you meet that condition. Three, certain cards in game possess the ability Exemplar, which provides EXP equal to the amount of damage that they deal whenever they do.\n\nTake the hero Heldim as an example. He has a passive ability that provides 2 EXP whenever you attack with only one unit. When he reaches 4 total EXP, his level 1 reward is unlocked, which is a 2/2 flier named Cassiel that is played on the board for you for free, at the end of the turn you reach the reward threshold. His level 2, which requires 7 additional EXP to reach, resurrects Cassiel if she is dead and gives her +2/+2 permanently. His further rewards again resurrect Cassiel and provides her additional buffs.')
        await bot.say('\n\nThe nature of heroes, their passives, and the rewards shapes the playstyle of the decks built under them, while allowing enough flexibility that multiple archetypes can be built under one hero. The aforementioned Heldim, for example, lends himself to aggro and aggressive midrange decks currently. Vriktik, on the other hand, has a passive that triggers on enemy unit death and gives rewards that are good at removing/stalling enemy units, so its decks tend to lean towards control. Building your deck to best take advantage of a given hero’s traits is a pillar of Collective’s gameplay, and enables a further layer of variety beyond the affinity system.')
    elif link == 'basics':
        await bot.say('Life total: 25\nMana System: +1 max per turn, no max limit\nHandsize: 13 (overdraw burn)\nDecksize: 45 min, 300 max, 3 max per card\nMulligan: 4 card choose-to-replace\nFatigue: Instant death on empty draw\nTurn system: Simultaneous\nCard resolution: Resolving queue, alternating priority\nCard types: Units and actions only (creatures/sorceries)')
    elif link == 'player':
        await bot.say('**Helpful Links**\nList of cards: <https://www.collective.gg/collection>\nList of keywords: <https://collective.gamepedia.com/Keywords>\nWrite-up of affinity identity trends: <https://collective.gamepedia.com/Affinity_Identities>\nList of current coding restraints: <https://collective.gamepedia.com/Temporary_rules>\nArticle on player design strategies: <https://medium.com/@nick_13012/design-strategies-for-ccgs-that-our-players-taught-us-6f8585613f52>\n\n**Helpful Commands**\n!new basics (some foundational traits of the game)\n!new turns (explanation of the simultaneous turns system)\n!new heroes (explanation of the heroes and XP system)')
    else:
        await bot.say("{} isnt a link I can give. the current links are: keys,collection,turns,heroes,basics,player".format(link))

@bot.command(pass_context=True)
async def say(ctx):
    if ctx.message.author.id == '223876086994436097':
        await bot.delete_message(ctx.message)
        await bot.say(' '.join(ctx.message.content.split(' ')[1:]))

@bot.command(pass_context=True)
async def update(ctx):
    global core_set
    if ctx.message.author.id == '223876086994436097':
        core_set = {}
        for card_info in requests.get('https://server.collective.gg/api/public-cards/').json()['cards']:
            if card_info['imgurl'] is not None:
                core_set[card_info['name']] = card_info['imgurl']
        await bot.say('done updating the cards!')

@bot.command(pass_context=True)
async def image(ctx,link):
    if link.startswith('https://files.collective.gg/p/cards/'):
        card_id = '-'.join(link.split('/')[-1].split('-')[ :-1])
        card_data = requests.get('https://server.collective.gg/api/card/'+card_id).json()
        if len(card_data) > 1:
            for prop in card_data['card']['Text']['Properties']:
                if prop['Symbol']['Name'] == 'PortraitUrl':
                    os.remove('card.png')
                    with open('card.png' , 'wb+') as img:
                        img_link =  requests.get(prop['Expression']['Value'])
                        img.write(img_link.content)
                        await bot.send_file(ctx.message.channel, 'card.png')
        else:
            await bot.say('sorry, card was not found')
    else:
        await bot.say('sorry, but this isnt a link!')

@bot.command(pass_context=True)
async def squidward(ctx):
    await bot.send_file(ctx.message.channel,'squidward.jpg')

@bot.command(pass_context=True)
async def excuseme(ctx):
    await bot.send_file(ctx.message.channel,'excuseme.jpg')

@bot.command()
async def leaderboard():
    leaderboard = discord.Embed(title="leaderboard", color=0x00FFFF)
    for spot in requests.get('https://server.collective.gg/api/public/leaderboards').json()['multi']:
        leaderboard.add_field(name='{}) {} {} {}'.format(spot['deck_rank'],spot['username'],spot['elo'],spot['hero_name']),value=(spot['deck_rank'])+1,inline=False)
    await bot.say(embed=leaderboard)
@bot.command()
async def help():
    await bot.say(embed=embed)

# events
@bot.event
async def on_message(message):
    cards = get_card_name(message.content) # this gets all card names in the message
    links = [] # here are the card links stored
    for card in cards:
        mod , card = card
        if card.lower().startswith('top '):
            card = card.lower()
            if len(card.split(' ')) == 2: # the name looks like this :"top X"
                num = card.split(' ')[1]
                if num.isdigit():
                    links += get_top(int(num),os.environ.get('WEEK'))
            elif len(card.split(' ')) == 4:
                num = card.split(' ')[1]
                week = card.split(' ')[3]
                if card.split(' ')[2] == 'week': # the name looks like this: "top X week Y"
                    if num.isdigit() and week.isdigit():
                        links += get_top(int(num), week)
                elif card.split(' ')[2] == 'dc':
                    links += list([x.url for x in filter(lambda post: not post.selftext ,collective.search('[DC{}'.format(week),sort='top',limit=int(num)))])
        else:
            if mod == 'none':
                links.append(get_core(card))
            elif mod == 'sub':
                found = False
                for post in collective.search(card, limit=1):  # this searches the subreddit for the card name with the [card] tag and takes the top suggestion
                    if post.title.startswith('['):
                        links.append(post.url)
                        found = True
                if not found:
                    links.append('{} was not found in the subreddit.'.format(card))
            elif mod == 'mtg':
                links.append(get_mtg(card))
            elif mod == 'sb':
                links.append(get_from_set(card,stormbound_cards))
            elif mod == 'ygo':
                links.append(get_ygo(card))
            elif mod == 'et':
                links.append(get_from_set(card,eternal_cards))
            elif mod == 'hs':
                links.append('https://art.hearthstonejson.com/v1/render/latest/enUS/512x/'+get_from_set(card,hs_cards)+'.png')
            else:
                links.append("the mode you chose is not present at this moment. current mods are: {}".format(','.join(POSSIBLE_MODS)))
    if links: # if there are any links
        for x in range((len(links)//5)+1): # this loops runs one time plus once for every five links since discord can only display five pictures per message
            await bot.send_message(message.channel , '\n'.join(links[5*x:5*(x+1)]))
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction,user):
    if reaction.emoji == '🤦' and reaction.message.author == bot.user:
        await bot.delete_message(reaction.message)

#main
core_set = load_core_set()
temp_cards = load_temp_cards()
stormbound_cards = load_stormbound_cards()
eternal_cards = load_eternal()
hs_cards = load_hs()
POSSIBLE_MODS = ['mtg','sub','sb','ygo','et','hs']
bot.run(os.environ.get('BOT_TOKEN')) #DO NOT FORGET TO REMOVE
