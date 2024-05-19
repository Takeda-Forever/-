import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta
from random import shuffle

API_TOKEN = "7108357216:AAF9fM_pQekSdMqzx554unxiyIy88D336l0"

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

chat_list = {}
time_now = datetime.now()

def player_in_game(player_id):
    for chat in chat_list.values():
        if player_id in chat['players']:
            return True
    return False

async def change_role(player_id, player_dict, new_role, text):
    player_dict[player_id]['role'] = new_role
    await bot.send_message(player_id, text)

async def list_buttons(player_dict, game_id, player_role, text):
    players_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=val['name'], callback_data=f'{key}{player_role[0]}{game_id}') for key, val in player_dict.items() if val['role'] != player_role]
    ])
    message = await bot.send_message(game_id, text, reply_markup=players_btn)
    return message.message_id

async def choice_checker(chat_id, chat, player_role):
    if not chat[player_role]:
        await bot.edit_message_text(chat_id=chat_id, message_id=chat[f'{player_role[0]}List_id'], text='Время выбора истекло...', reply_markup=None)
        chat[player_role] = True

def players_alive(player_dict):
    mes = "*Живые игроки:*"
    for i, player in enumerate(player_dict.values(), 1):
        mes += f'\n{i}. {player["name"]}'
    return mes

def players_role(player_dict):
    mes = "*Кто-то из них:*\n"
    player_keys = list(player_dict.keys())
    shuffle(player_keys)
    for i, key in enumerate(player_keys):
        mes += f'{player_dict[key]["role"]}'
        if i < len(player_keys) - 1:
            mes += ', '
    return mes

async def voice_handler(game_id):
    players = chat_list[game_id]['players']
    voice_dict = []
    for key, val in players.items():
        if 'voice' in val:
            voice_dict.append(val['voice'])
            players[key].pop('voice')
    if voice_dict:
        dead_key = max(set(voice_dict), key=voice_dict.count)
        dead = players.pop(dead_key)
        return dead

@dp.message(Command(commands=["start"]))
async def start_message(message: types.Message):
    otvet = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Начать игру', callback_data='start_game')]
    ])
    await message.answer('Привет!\nЯ ведущий бот по игре мафия🤵🏻', reply_markup=otvet)


@dp.callback_query()
async def callback_handler(call: types.CallbackQuery):
    global chat_list
    if call.data == 'start_game':
        await call.message.answer("Начинаем игру!")
    elif call.data == 'join':
        chat_id = call.message.chat.id
        chat = chat_list.get(chat_id, {'game_running': False, 'players': {}})
        players = chat['players']
        if player_in_game(call.from_user.id):
            await call.message.answer('Вы не можете присоединиться, пока находитесь в другой игре')
        else:
            players[call.from_user.id] = {'name': call.from_user.first_name}
            await call.message.answer('Вы присоединились к игре')
            chat_list[chat_id] = chat
            await update_players_list(chat_id)

    elif 'м' in call.data:
        data = call.data.split('м')
        dead = chat_list[int(data[1])]["players"][int(data[0])]
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text=f'Вы выбрали {dead["name"]}', reply_markup=None)
        chat_list[int(data[1])]['dead'] = (int(data[0]), dead)
        await bot.send_message(int(data[1]), '🤵🏻 Мафия выбрала жертву...')

    elif 'ш' in call.data:
        data = call.data.split('ш')
        checked = chat_list[int(data[1])]["players"][int(data[0])]
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text=f'{checked["name"]} оказался {checked["role"]}', reply_markup=None)
        await bot.send_message(int(data[1]), '🕵🏼️‍♂ Шериф ушёл искать злодеев...')
        chat_list[int(data[1])]['шериф'] = True

    elif call.data.isdigit():
        if call.from_user.id in chat_list[call.message.chat.id]['players']:
            chat_list[call.message.chat.id]['players'][call.from_user.id]['voice'] = int(call.data)


#Сломанная часть который работает некорреткно 
'''
@dp.message(ContentType(types.ContentType.NEW_CHAT_MEMBERS))
async def welcome_new_member(message: types.Message):
    if message.new_chat_members.id == 7108357216 :
        await message.answer('Welcome new member')
'''

@dp.message()
async def welcome_new_member(message: types.Message):
    if message.new_chat_members is not None and len(message.new_chat_members) > 0:
        if message.new_chat_members[0].id == 7108357216:
            await message.answer('Добро пожаловать новый игрок!')


            
##Обработка командый -----------create_game-----------
@dp.message(Command(commands=["create_game"]))
async def get_command(message: types.Message):
    global chat_list, time_now
    chat_id = message.chat.id
    if chat_id not in chat_list:
        chat_list[chat_id] = {'game_running': False, 'players': {}}
        await message.answer('Создан новый игровой чат.')
    chat = chat_list[chat_id]
    players = chat['players']

    if not players:
        join_btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Присоединиться к игре', callback_data='join')]
        ])
        msg = await message.answer("""Нажмите на кнопку чтобы вступить в игру.
Напишите команду /start_game для начала игры""", reply_markup=join_btn)
        chat['join_message_id'] = msg.message_id
        await message.answer('Игра создана. Ожидание игроков...')

    else:
        await message.answer('Игра уже создана или идет.')


#Обработка командый -----------start_game-----------, а также само процесс игры
@dp.message(Command(commands=["start_game"]))
async def start_game(message: types.Message):
    global chat_list, time_now
    chat_id = message.chat.id
    chat = chat_list.get(chat_id, {'game_running': False, 'players': {}})
    players = chat['players']

    if len(players) >= 4 and not chat['game_running']:
        chat['game_running'] = True
        await bot.edit_message_text(chat_id=chat_id, message_id=chat['join_message_id'], text="Игра начинается!", reply_markup=None)
        del chat['join_message_id']
        player_items = list(players.items())
        shuffle(player_items)

        await change_role(player_items[0][0], players, 'мафия', 'Ты - 🤵🏻мафия! Тебе решать, кто не проснётся этой ночью...')
        await change_role(player_items[1][0], players, 'шериф', 'Ты - 🕵🏼️‍♂шериф! Главный городской защитник и гроза мафии...')
        for i in range(2, len(player_items)):
            await change_role(player_items[i][0], players, 'мирный житель', 'Ты - 👨🏼 Мирный житель. Твоя задача вычислить мафию и на городском собрании казнить засранца!')

        await notify_players_about_roles(players)
        while True:
            if player_items[1][0] in players:
                chat['dead'] = False
                chat['шериф'] = False
            else:
                chat['dead'] = False
                chat['шериф'] = True

            await bot.send_video(chat_id, open("video/sunset.mp4", "rb"), caption='''🌃 Наступает ночь. На улицы города выходят лишь самые отважные и бесстрашные. Утром попробуем сосчитать их головы...''')
            await message.answer(players_alive(players) + '\n\nСпать осталось *1 мин.*', parse_mode="Markdown")

            chat['dList_id'] = await list_buttons(players, chat_id, 'мафия', 'Кого будем убивать?')
            if player_items[1][0] in players:
                chat['шList_id'] = await list_buttons(players, chat_id, 'шериф', 'Кого будем проверять?')

            chat['time_event'] = datetime.now() + timedelta(seconds=60)

            while chat_list[chat_id]['time_event'] > time_now:
                await asyncio.sleep(1)
                time_now = datetime.now()

            await choice_checker(chat_id, chat, 'шериф')

            if not chat['dead']:
                await bot.edit_message_text(chat_id=chat_id, message_id=chat['dList_id'], text='Время выбора истекло...', reply_markup=None)
                chat['dead'] = True

            dead = await voice_handler(chat_id)
            await message.answer(f'☠ *{dead["name"]}*.', parse_mode="Markdown")
            if dead['role'] == 'шериф' and not any(player['role'] == 'шериф' for player in players.values()):
                await message.answer('Мафия выиграла! 🎉')
                chat['game_running'] = False
                break

            if not any(player['role'] == 'мафия' for player in players.values()):
                await message.answer('Все мафии мертвы. Мирные жители выиграли! 🎉')
                chat['game_running'] = False
                break

            await message.answer(players_alive(players), parse_mode="Markdown")

            players_btn = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=players[player_id]['name'], callback_data=str(player_id)) for player_id in players.keys()]
            ])
            await message.answer(players_role(players) + '\n*Пришло время выбрать одного из них...*', parse_mode="Markdown", reply_markup=players_btn)

            chat['time_event'] = datetime.now() + timedelta(seconds=60)

            while chat_list[message.chat.id]['time_event'] > time_now:
                await asyncio.sleep(1)
                time_now = datetime.now()

            dead = await voice_handler(message.chat.id)
            await message.answer(f'☠ *{dead["name"]}* казнён горожанами...', parse_mode="Markdown")
            if dead['role'] == 'мафия':
                await message.answer('Мирные победили! 🎉')
                await message.answer('Игра окончена!')
                chat['game_running'] = False
                break
    else:
        await message.answer('Нужно минимум 4 игрока, чтобы начать игру.')

async def cancel_registration(message: types.Message):
    global chat_list
    chat_id = message.chat.id
    user_id = message.from_user.id
    if chat_id in chat_list and user_id in chat_list[chat_id]['players']:
        chat_list[chat_id]['players'].pop(user_id)
        await message.answer('Вы отменили регистрацию на игру.')
        await update_players_list(chat_id)
    else:
        await message.answer('Вы не зарегистрированы в игре.')

async def cancel_game(message: types.Message):
    global chat_list
    chat_id = message.chat.id
    if chat_id in chat_list and chat_list[chat_id]['game_running']:
        chat_list[chat_id]['game_running'] = False
        for player_id in chat_list[chat_id]['players']:
            await bot.send_message(player_id, 'Игра была отменена.')
        await message.answer('Игра была отменена.')
    else:
        await message.answer('Игра не запущена или уже была завершена.')

async def update_players_list(chat_id):
    global chat_list
    chat = chat_list[chat_id]
    players = chat['players']
    players_list = "*Игроки, присоединившиеся к игре:*\n"
    for player in players.values():
        players_list += f"{player['name']}\n"
    if 'join_message_id' in chat:
        await bot.edit_message_text(chat_id=chat_id, message_id=chat['join_message_id'], text=players_list, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Присоединиться к игре', callback_data='join')]
        ]))

async def notify_players_about_roles(players):
    for player_id, player_info in players.items():
        await bot.send_message(player_id, f'Ваша роль: {player_info["role"]}')

async def main():
    dp.message.register(start_message, Command(commands=["start"]))
    dp.message.register(get_command, Command(commands=["create_game"]))
    dp.message.register(start_game, Command(commands=["start_game"]))
    dp.message.register(cancel_registration, Command(commands=["cancel_registration"]))
    dp.message.register(cancel_game, Command(commands=["cancel_game"]))
    dp.callback_query.register(callback_handler)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
