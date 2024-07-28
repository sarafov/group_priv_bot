from flask import Flask, request
from telebot import types,util
from telebot.async_telebot import AsyncTeleBot
import asyncio
import os
from telebot import formatting
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import json
import urllib
from telebot.types import LinkPreviewOptions
import cv2
from PIL import Image
import piexif
from io import BytesIO
import logging
from detoxify import Detoxify
import aiohttp
from ultralytics import YOLO
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.utils import get_file

# Initialize the bot with your API token
with open('configuration/token.conf', 'r') as token_file:
	token = token_file.read().strip()
bot_username ='@group_priv_bot'
with open('configuration/key.conf', 'r') as key_file:
	key_f = key_file.read().strip()
key = key_f.encode()

group_path = 'configuration/group_setting.json'
personalized_path = 'configuration/personalized_setting.json'

bot = AsyncTeleBot(token)

#-------------------ENCRYPTION AND DECRYPTION FUNCTIONS-------------------#
def encrypt(data, key):
    # Ensure data is in bytes
    if isinstance(data, str):
        data = data.encode()
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(data, AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    # Encode the combined IV and encrypted data to make it safe for storage/transmission
    return base64.b64encode(iv + encrypted_data).decode()

def decrypt(encrypted_data, key):
    # Ensure data is in bytes
    if isinstance(encrypted_data, str):
        encrypted_data = base64.b64decode(encrypted_data)
    iv = encrypted_data[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = cipher.decrypt(encrypted_data[AES.block_size:])
    return unpad(padded_data, AES.block_size).decode()
#-------------------END OF ENCRYPTION AND DECRYPTION FUNCTIONS-------------------#

#-------------------BOT JOIN GROUP HANDLER-------------------#
@bot.my_chat_member_handler()
async def my_chat_m(message: types.ChatMemberUpdated):
    old = message.old_chat_member
    new = message.new_chat_member
    if new.status == "member":
        await bot.send_message(message.chat.id, "Thanks for adding me to the group chat, I am a privacy management bot!")  # Welcome message, if bot was added to group
        await bot.send_message(message.chat.id, "Please activate me first via command /activation and change my role to administrator")
        group_chat_id = str(message.chat.id)
        found = False

        # Read the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Process only if there are entries
        if groups:
            for group in groups:
                group_chat_id_decrypted = decrypt(group['group_id'], key)
                if group_chat_id == group_chat_id_decrypted:
                    found = True
                    break

        if not found:
            # Encrypt and update the JSON file if not found
            encrypted_group_chat_id = encrypt(group_chat_id, key)
            new_group = {
                "group_id": encrypted_group_chat_id,
                "activation": 0,
                "global": 0,
                "sentiment": {
                    "value": 1,
                    "details": {
                        "obscene": 1,
                        "threat": 1,
                        "insult": 1,
                        "identity_attack": 1,
                        "sexual_explicit": 1
                    }
                },
                "face": 2,
                "location": {
                    "value": 1,
                    "details": {
                        "location_only": 1,
                        "document": 1,
                        "image": 1
                    }
                },
                "link": 1,
                "contact": 1
            }
            groups.append(new_group)
            with open(group_path, 'w') as file:
                json.dump(groups, file, indent=4)
#-------------------END OF BOT JOIN GROUP HANDLER-------------------#


#-------------------BOT NEW USER JOIN GROUP HANDLER--------------------------#
@bot.chat_member_handler()
async def new_chat_member_handler(message: types.ChatMemberUpdated):
    new = message.new_chat_member
    if new.status == "member":
        new_user_id = new.user.id
        new_user_name = new.user.username
        group_chat_id = str(message.chat.id)

        welcome_message = f"Welcome to user study group chat,  @{new_user_name}.\nPlease click this {bot_username} and then click START to allow your interaction with the privacy bot."
        await bot.send_message(
                    group_chat_id,
                    formatting.format_text(
                        formatting.munderline("-- NOTIFICATION --"),
                        formatting.mbold(welcome_message),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2'
        )
#-------------------END OF BOT NEW USER JOIN GROUP HANDLER-------------------#

#-------------------BOT USER LEFT GROUP HANDLER--------------------------#
@bot.message_handler(content_types='left_chat_member')
async def member_left_handler(message: types.ChatMemberUpdated):
    if message.left_chat_member:
        group_chat_id = str(message.chat.id)
        user_id = str(message.left_chat_member.id)
        remove_user_data(group_chat_id, user_id)
        await bot.send_message(message.left_chat_member.id, f"Thank you for participating in user study.\nYour contribution hopefully will make Telegram a safer place for everyone.\n\nBest Regards,\nPrivacy Bot Team")

def remove_user_data(group_id, user_id):
    try:
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        personalized_user = next((g for g in personalized if decrypt(g['group_id'], key) == group_id and decrypt(g['user_id'], key) == user_id), None)
        if personalized_user:
            personalized.remove(personalized_user)
            with open(personalized_path, 'w') as file:
                json.dump(personalized, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
#-------------------END OF BOT USER LEFT GROUP HANDLER-------------------#

#-------------------BOT COMMAND START HANDLER-------------------#
@bot.message_handler(commands=['start'])
async def start_command(message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "Welcome to privacy bot!\nPlease use /privacy_setting command from the group chat to activate your personalized privacy setting")
#-------------------END OF BOT COMMAND START HANDLER-------------------#

#-------------------BOT COMMAND ACTIVATION HANDLER-------------------#
@bot.message_handler(commands=['activation'])
async def activate_command(message):
    group_chat_id = str(message.chat.id)
    # Your code for the 'activate' command here
    if message.chat.type == 'private':
        # Your code for the 'activate' command in private chat here
        await bot.send_message(message.chat.id, "Please use the activate command in the group chat directly, thank you", reply_to_message_id=message.message_id)
    elif message.chat.type == 'group' or message.chat.type == 'supergroup':
        # Check if the user is an administrator or owner
        if message.from_user.id in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:

            activation_status =""
            # Load the group settings from JSON file
            try:
                with open(group_path, 'r') as file:
                    groups = json.load(file)

                # Find the group chat
                group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id), None)
                if group:
                    if group['activation'] == 1:
                        activation_status = "ON"
                    else:
                        activation_status = "OFF"
            except IOError as e:
                print(f"An error occurred while accessing the file: {e}")

            # Send the initial setting message
            setting_message = await bot.send_message(
                message.from_user.id,
                formatting.format_text(
                    formatting.munderline("-- BOT ACTIVATION SETTING --"),
                    formatting.mbold("Current Setting: " + activation_status),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2'
            )

            # Create the buttons
            keyboard = types.InlineKeyboardMarkup()
            on_button = types.InlineKeyboardButton("TURN ON", callback_data=f"activate_on_{message.chat.id}_{setting_message.message_id}")
            off_button = types.InlineKeyboardButton("TURN OFF", callback_data=f"activate_off_{message.chat.id}_{setting_message.message_id}")
            keyboard.add(on_button, off_button)
            await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)
        else:
            await bot.send_message(message.chat.id, "The command can only be executed by the owner or administrator", reply_to_message_id=message.message_id)

def update_activation_value(group_id_to_find, new_activation_value):
    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for group in groups:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(group['group_id'], key)
            if group_chat_id_decrypted == group_id_to_find:
                # Update the activation and other settings
                group['activation'] = new_activation_value
                group['sentiment']['value'] = new_activation_value  # Assuming all sub-values should also be updated
                for attribute in group['sentiment']['details']:
                    group['sentiment']['details'][attribute] = new_activation_value

                group['face'] = new_activation_value

                group['location']['value'] = new_activation_value
                for attribute in group['location']['details']:
                    group['location']['details'][attribute] = new_activation_value

                group['link'] = new_activation_value
                group['contact'] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(group_path, 'w') as file:
                json.dump(groups, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('activate_on_'))
async def activate_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    # Update the setting message
    await bot.edit_message_text(
        formatting.format_text(
            formatting.munderline("-- BOT ACTIVATION SETTING --"),
            formatting.mbold("Current Setting: ON"),
            separator="\n"
        ),
        chat_id=call.from_user.id,
        message_id=message_id,
        parse_mode='MarkdownV2'
    )

    await bot.answer_callback_query(call.id, "Privacy Bot Has Been Activated, Please Change Bot Role to Administrator To Handle All Shared Contents!")
    await bot.send_message(
                group_chat_id,
                formatting.format_text(
                    formatting.munderline("-- NOTIFICATION --"),
                    formatting.mbold("Privacy Bot has been activated in this group chat"),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2'
    )
    update_activation_value(group_chat_id, 1)

@bot.callback_query_handler(func=lambda call: call.data.startswith('activate_off_'))
async def activate_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    # Update the setting message
    await bot.edit_message_text(
        formatting.format_text(
            formatting.munderline("-- BOT ACTIVATION SETTING --"),
            formatting.mbold("Current Setting: OFF"),
            separator="\n"
        ),
        chat_id=call.from_user.id,
        message_id=message_id,
        parse_mode='MarkdownV2'
    )
    await bot.answer_callback_query(call.id, "Privacy Bot Has Been Deactivated")
    await bot.send_message(
                group_chat_id,
                formatting.format_text(
                    formatting.munderline("-- NOTIFICATION --"),
                    formatting.mbold("Privacy Bot has been deactivated in this group chat"),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2'
    )
    update_activation_value(group_chat_id, 0)
#-------------------END OF BOT COMMAND ACTIVATION HANDLER-------------------#

#-------------------BOT COMMAND GLOBAL HANDLER-------------------#
@bot.message_handler(commands=['global'])
async def global_command(message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "Please use the global command in the group chat directly, thank you", reply_to_message_id=message.message_id)
    elif message.chat.type == 'group' or message.chat.type == 'supergroup':
        group_chat_id = str(message.chat.id)

        # Load the group settings from JSON file
        try:
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Find the group and check if it's activated
            group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)
            if group is None:
                await bot.send_message(
                    message.chat.id,
                    formatting.format_text(
                        formatting.munderline("-- NOTIFICATION --"),
                        formatting.mbold("Please activate privacy bot via /activation command first"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                    reply_to_message_id=message.message_id
                )
                return

            # Check if the user is an administrator or owner
            if message.from_user.id in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:
                activation_status =""
                # Load the group settings from JSON file
                try:
                    with open(group_path, 'r') as file:
                        groups = json.load(file)

                    # Find the group chat
                    group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id), None)
                    if group:
                        if group['global'] == 1:
                            activation_status = "GLOBAL"
                        else:
                            activation_status = "PERSONALIZED"
                except IOError as e:
                    print(f"An error occurred while accessing the file: {e}")

                # Send the initial setting message
                setting_message = await bot.send_message(
                    message.from_user.id,
                    formatting.format_text(
                        formatting.munderline("-- BOT GLOBAL SETTING --"),
                        formatting.mbold("Current Setting: " + activation_status),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2'
                )

                # Create the buttons
                keyboard = types.InlineKeyboardMarkup()
                on_button = types.InlineKeyboardButton("GLOBAL", callback_data=f"global_on_{message.chat.id}_{setting_message.message_id}")
                off_button = types.InlineKeyboardButton("PERSONALIZED", callback_data=f"global_off_{message.chat.id}_{setting_message.message_id}")
                keyboard.add(on_button, off_button)
                await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)
            else:
                await bot.send_message(message.chat.id, "The command can only be executed by the owner or administrator", reply_to_message_id=message.message_id)

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)

def update_global_value(group_id_to_find, new_activation_value):
    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for group in groups:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(group['group_id'], key)
            if group_chat_id_decrypted == group_id_to_find:
                # Update the activation and all other settings
                group['global'] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(group_path, 'w') as file:
                json.dump(groups, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('global_on_'))
async def global_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    # Update the setting message
    await bot.edit_message_text(
        formatting.format_text(
            formatting.munderline("-- BOT GLOBAL SETTING --"),
            formatting.mbold("Current Setting: GLOBAL"),
            separator="\n"
        ),
        chat_id=call.from_user.id,
        message_id=message_id,
        parse_mode='MarkdownV2'
    )

    await bot.answer_callback_query(call.id, "Global Privacy Mode Has Been Activated")
    await bot.send_message(
                group_chat_id,
                formatting.format_text(
                    formatting.munderline("-- NOTIFICATION --"),
                    formatting.mbold("Global privacy mode has been activated, privacy configuration will be applied to all members in the group chat"),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2'
    )
    update_global_value(group_chat_id, 1)

@bot.callback_query_handler(func=lambda call: call.data.startswith('global_off_'))
async def global_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    # Update the setting message
    await bot.edit_message_text(
        formatting.format_text(
            formatting.munderline("-- BOT GLOBAL SETTING --"),
            formatting.mbold("Current Setting: PERSONALIZED"),
            separator="\n"
        ),
        chat_id=call.from_user.id,
        message_id=message_id,
        parse_mode='MarkdownV2'
    )

    await bot.answer_callback_query(call.id, "Personalized Privacy Mode Has Been Activated")
    await bot.send_message(
                group_chat_id,
                formatting.format_text(
                    formatting.munderline("-- NOTIFICATION --"),
                    formatting.mbold("Personalized privacy mode has been activated, everyone can configure their own privacy preference via /privacy_setting command"),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2'
    )
    update_global_value(group_chat_id, 0)
#-------------------END OF BOT COMMAND GLOBAL HANDLER-------------------#

#-------------------BOT COMMAND PRIVACY SETTING HANDLER-------------------#
def escape_markdown_v2(text):
    special_characters = '_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in special_characters else char for char in text])

@bot.message_handler(commands=['privacy_setting'])
async def personalized_command(message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "Please initiate the privacy setting command in the group chat, thank you", reply_to_message_id=message.message_id)
    elif message.chat.type == 'group' or message.chat.type == 'supergroup':
        group_chat_id = str(message.chat.id)

        # Load the group settings from JSON file
        try:
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Find the group and check if it's activated
            group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)
            if group is None:
                await bot.send_message(message.chat.id, "Please activate privacy bot via /activate command first", reply_to_message_id=message.message_id)
                return

            #check if personalized setting is activated (global is disabled)
            global_setting = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['global'] == 1), None)
            if global_setting is None:
                try:
                    # Load the existing data from the JSON file
                    with open(personalized_path, 'r') as file:
                        personalized = json.load(file)

                    # Check if we have existing user data
                    if personalized:
                        user_setting = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == str(message.from_user.id)) and (g['activation'] == 1)), None)

                        if user_setting:
                            activation_status = "ON"

                            sentiment = user_setting['sentiment']['value']
                            sentiment_setting = f"1. Negative sentiment prevention in chat : {'ON' if sentiment == 1 else 'OFF'}"
                            if sentiment == 1:
                                sentiment_details = ", ".join(attribute for attribute in user_setting['sentiment']['details'] if user_setting['sentiment']['details'][attribute] == 1)
                                sentiment_setting += f" ({sentiment_details})"

                            face = user_setting['face']
                            face_setting = ["OFF", "ON (Remove Image)", "ON (Blur Face)", "ON (Emoji Face)"][face]

                            location = user_setting['location']['value']
                            location_setting = f"3. Location breach prevention : {'ON' if location == 1 else 'OFF'}"
                            if location == 1:
                                location_details = ", ".join([
                                    "Private Location in Image Content" if attribute == "image" and user_setting['location']['details'][attribute] == 1 else
                                    "Public Location in Image Content" if attribute == "image" and user_setting['location']['details'][attribute] == 1 else
                                    "Location Sharing" if attribute == "location_only" and user_setting['location']['details'][attribute] == 1 else
                                    "Location Metadata in Document (Raw Image)" for attribute in user_setting['location']['details']
                                ])
                                location_setting += f" ({location_details})"

                            link = user_setting['link']
                            link_setting = f"4. Link preview prevention in chat : {'ON' if link == 1 else 'OFF'}"

                            contact = user_setting['contact']
                            contact_setting = f"5. Contact sharing prevention : {'ON' if contact == 1 else 'OFF'}"

                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- PRIVACY SETTING --"),
                                    formatting.mbold(f"Activation Status: {activation_status}"),
                                    escape_markdown_v2(sentiment_setting),
                                    escape_markdown_v2(face_setting),
                                    escape_markdown_v2(location_setting),
                                    escape_markdown_v2(link_setting),
                                    escape_markdown_v2(contact_setting),
                                    separator="\n"
                                ),
                                parse_mode='MarkdownV2'
                            )

                            # Create the three buttons
                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("TURN ON", callback_data=f"personalized_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("TURN OFF", callback_data=f"personalized_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Choose Privacy Setting Status:", reply_markup=keyboard)

                        else:
                            activation_status = "OFF"
                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- PRIVACY SETTING --"),
                                    formatting.mbold("Activation Status: " + activation_status),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            # Create the three buttons
                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("TURN ON", callback_data=f"personalized_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("TURN OFF", callback_data=f"personalized_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Choose Privacy Setting Status:", reply_markup=keyboard)
                    else:
                        activation_status = "OFF"
                        setting_message = await bot.send_message(
                            message.from_user.id,
                            formatting.format_text(
                                formatting.munderline("-- PRIVACY SETTING --"),
                                formatting.mbold(f"Activation Status: {activation_status}"),
                                separator="\n"  # separator separates all strings
                            ),
                            parse_mode='MarkdownV2'
                        )

                        # Create the three buttons
                        keyboard = types.InlineKeyboardMarkup()
                        on_button = types.InlineKeyboardButton("TURN ON", callback_data=f"personalized_on_{message.chat.id}_{setting_message.message_id}")
                        off_button = types.InlineKeyboardButton("TURN OFF", callback_data=f"personalized_off_{message.chat.id}_{setting_message.message_id}")
                        keyboard.add(on_button, off_button)
                        await bot.send_message(message.from_user.id, "Choose Privacy Setting Status:", reply_markup=keyboard)

                except IOError as e:
                    print(f"An error occurred while accessing the file: {e}")

            else:
                await bot.send_message(message.chat.id, "Global mode is activated, Admin or owner group please deactivate the global mode first", reply_to_message_id=message.message_id)
                return
        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_on_'))
async def personalized_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]
    user_id = str(call.from_user.id)

    update_personalized_value(group_chat_id, user_id, 1)
    with open(personalized_path, 'r') as file:
        personalized = json.load(file)

    # Check if we have existing user data
    if personalized:
        user_setting = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == user_id)), None)

        if user_setting:
            activation_status = "ON"

            #sentiment setting
            sentiment = user_setting['sentiment']['value']
            sentiment_setting =''
            if sentiment == 1:
                sentiment_details = ""
                for attribute in user_setting['sentiment']['details']:
                    if user_setting['sentiment']['details'][attribute] == 1:
                        if sentiment_details != "":
                            sentiment_details += f", {attribute}"
                        else:
                            sentiment_details += attribute
                sentiment_setting = f"1. Negative sentiment prevention in chat : ON ({sentiment_details})"
            else:
                sentiment_setting = "1. Negative sentiment prevention in chat : OFF"

            #face setting
            face = user_setting['face']
            face_setting = ''
            if face == 0:
                face_setting =  "2. Human face prevention in image : OFF"
            elif face == 1:
                face_setting =  "2. Human face prevention in image : ON (Remove Image)"
            elif face == 2:
                face_setting =  "2. Human face prevention in image : ON (Blur Face)"
            else:
                face_setting =  "2. Human face prevention in image : ON (Emoji Face)"

            #location setting
            location = user_setting['location']['value']
            location_setting = ''
            if location == 1:
                location_details = ""
                for attribute in user_setting['location']['details']:
                    if attribute == "image" and user_setting['location']['details'][attribute] == 1:
                        location_details += "Private Location in Image Content, "
                    elif attribute == "image" and user_setting['location']['details'][attribute] == 1:
                        location_details += "Public Location in Image Content, "
                    elif attribute == "location_only" and user_setting['location']['details'][attribute] == 1:
                        location_details += "Location Sharing, "
                    elif attribute == "document" and user_setting['location']['details'][attribute] == 1:
                        location_details += "Location Metadata in Document (Raw Image)"
                location_setting = f"3. Location breach prevention : ON ({location_details})"
            else:
                location_setting = "3. Location breach prevention : OFF"


            #link setting
            link = user_setting['link']
            link_setting = ''
            if link == 1:
                link_setting = "4. Link preview prevention in chat : ON"
            else:
                link_setting = "4. Link preview prevention in chat : OFF"

            #contact setting
            contact = user_setting['contact']
            contact_setting = ''
            if contact == 1:
                contact_setting = "5. Contact sharing prevention : ON"
            else:
                contact_setting = "5. Contact sharing prevention : OFF"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- PRIVACY SETTING --"),
                        formatting.mbold(f"Activation Status: {activation_status}"),
                        escape_markdown_v2(sentiment_setting),
                        escape_markdown_v2(face_setting),
                        escape_markdown_v2(location_setting),
                        escape_markdown_v2(link_setting),
                        escape_markdown_v2(contact_setting),
                        separator="\n"
                    ),
                    parse_mode='MarkdownV2',
                    chat_id=call.from_user.id,
                    message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")

            await bot.answer_callback_query(call.id, "Personalized Privacy Setting Has Been Activated ")


@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_off_'))
async def personalized_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]
    user_id = str(call.from_user.id)

    update_personalized_value(group_chat_id, user_id, 0)

    activation_status = "OFF"
    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING --"),
                formatting.mbold("Activation Status: " + activation_status),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    await bot.answer_callback_query(call.id, "Personalized Privacy Setting Has Been Deactivated ")


def update_personalized_value(group_id_to_find, user_id_to_find ,new_activation_value):

    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            groups = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Check if we have any existing data
        if groups:
            # Iterate over each group configuration
            for group in groups:
                # Decrypt the group ID to see if it matches the group_id_to_find
                group_chat_id_decrypted = decrypt(group['group_id'], key)
                user_id_decrypted = decrypt(group['user_id'], key)
                if (group_chat_id_decrypted == group_id_to_find) and (user_id_decrypted == user_id_to_find):

                    # Update the activation and all other settings
                    group['activation'] = new_activation_value
                    found = True
                    break

        if not found:
            # Encrypt and update the JSON file if not found
            encrypted_group_chat_id = encrypt(group_id_to_find, key)
            encrypted_user_id = encrypt(user_id_to_find, key)
            new_group = {
                "group_id": encrypted_group_chat_id,
                "user_id": encrypted_user_id,
                "activation": 1,
                "sentiment": {
                    "value": 1,
                    "details": {
                        "obscene": 1,
                        "threat": 1,
                        "insult": 1,
                        "identity_attack": 1,
                        "sexual_explicit": 1
                    }
                },
                "face": 2,
                "location": {
                    "value": 1,
                    "details": {
                        "location_only": 1,
                        "document": 1,
                        "image": 1
                    }
                },
                "link": 1,
                "contact": 1
            }
            groups.append(new_group)

        # Write back to the JSON file if we made any changes
        with open(personalized_path, 'w') as file:
            json.dump(groups, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
#-------------------END OF BOT COMMAND PRIVACY SETTING HANDLER-------------------#

#-------------------BOT COMMAND LOCATION HANDLER-------------------#
@bot.message_handler(commands=['location'])
async def location_command(message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "Please use the location command in the group chat directly, thank you", reply_to_message_id=message.message_id)
    elif message.chat.type == 'group' or message.chat.type == 'supergroup':
        group_chat_id = str(message.chat.id)

        # Load the group settings from JSON file
        try:
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Find the group and check if it's activated
            group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)
            if group is None:
                await bot.send_message(message.chat.id, "Please activate privacy bot via /activate command first", reply_to_message_id=message.message_id)
                return
            else:
                # Store the "global" value into a variable called personalized
                global_setting = group['global']
                # Check if global is 1 or 0 (if 0, then personalized setting is activated)
                if global_setting == 1:
                    # Check if the user is an administrator or owner
                    if message.from_user.id in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:

                        location_setting = group['location']['value']
                        if location_setting == 0:
                            # Send the initial setting message
                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                                    formatting.mbold("Current Setting: OFF"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("ON", callback_data=f"location_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("OFF", callback_data=f"location_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Location Breach Prevention Status:", reply_markup=keyboard)

                            keyboard2 = types.InlineKeyboardMarkup()
                            location_button = types.InlineKeyboardButton("Location Share (ON/OFF)", callback_data=f"location_location_{message.chat.id}_{setting_message.message_id}")
                            document_button = types.InlineKeyboardButton("Document RAW Image (ON/OFF)", callback_data=f"location_document_{message.chat.id}_{setting_message.message_id}")
                            image_button = types.InlineKeyboardButton("Image Content (OFF/Public Only/Private Only)", callback_data=f"location_image_{message.chat.id}_{setting_message.message_id}")
                            keyboard2.add(image_button)
                            keyboard2.add(location_button)
                            keyboard2.add(document_button)
                            await bot.send_message(message.from_user.id, "Location Breach Prevention Type:", reply_markup=keyboard2)

                        else:
                            image_setting = group['location']['details']['image']
                            location_only_setting = group['location']['details']['location_only']
                            document_setting = group['location']['details']['document']

                            image_detail = f"1. Location Prevention in Image Content ({'Public Only' if image_setting == 1 else 'Private Only' if image_setting == 2 else 'OFF'})"
                            location_detail = f"2. Location Sharing Prevention ({'ON' if location_only_setting == 1 else 'OFF'})"
                            document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if document_setting == 1 else 'OFF'})"

                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                                    formatting.mbold("Current Setting: ON"),
                                    escape_markdown_v2(image_detail),
                                    escape_markdown_v2(location_detail),
                                    escape_markdown_v2(document_detail),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("ON", callback_data=f"location_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("OFF", callback_data=f"location_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Location Breach Prevention Status:", reply_markup=keyboard)

                            keyboard2 = types.InlineKeyboardMarkup()
                            location_button = types.InlineKeyboardButton("Location Share (ON/OFF)", callback_data=f"location_location_{message.chat.id}_{setting_message.message_id}")
                            document_button = types.InlineKeyboardButton("Document RAW Image (ON/OFF)", callback_data=f"location_document_{message.chat.id}_{setting_message.message_id}")
                            image_button = types.InlineKeyboardButton("Image Content (OFF/Public Only/Private Only)", callback_data=f"location_image_{message.chat.id}_{setting_message.message_id}")
                            keyboard2.add(image_button)
                            keyboard2.add(location_button)
                            keyboard2.add(document_button)
                            await bot.send_message(message.from_user.id, "Location Breach Prevention Type:", reply_markup=keyboard2)

                    else:
                        await bot.send_message(message.chat.id, "The command can only be executed by the owner or administrator", reply_to_message_id=message.message_id)
                else:
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            personalized_settings = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == str(message.from_user.id)) and (g['activation'] == 1)), None)

                            if personalized_settings:
                                image_setting = personalized_settings['location']['details']['image']
                                location_only_setting = personalized_settings['location']['details']['location_only']
                                document_setting = personalized_settings['location']['details']['document']

                                image_detail = f"1. Location Prevention in Image Content ({'Public Only' if image_setting == 1 else 'Private Only' if image_setting == 2 else 'OFF'})"
                                location_detail = f"2. Location Sharing Prevention ({'ON' if location_only_setting == 1 else 'OFF'})"
                                document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if document_setting == 1 else 'OFF'})"

                                setting_message = await bot.send_message(
                                    message.from_user.id,
                                    formatting.format_text(
                                        formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                                        formatting.mbold("Current Setting: ON"),
                                        escape_markdown_v2(image_detail),
                                        escape_markdown_v2(location_detail),
                                        escape_markdown_v2(document_detail),
                                        separator="\n" # separator separates all strings
                                    ),
                                    parse_mode='MarkdownV2'
                                )

                                keyboard = types.InlineKeyboardMarkup()
                                on_button = types.InlineKeyboardButton("ON", callback_data=f"personalized_location_on_{message.chat.id}_{setting_message.message_id}")
                                off_button = types.InlineKeyboardButton("OFF", callback_data=f"personalized_location_off_{message.chat.id}_{setting_message.message_id}")
                                keyboard.add(on_button, off_button)
                                await bot.send_message(message.from_user.id, "Location Breach Prevention Status:", reply_markup=keyboard)

                                keyboard2 = types.InlineKeyboardMarkup()
                                location_button = types.InlineKeyboardButton("Location Share (ON/OFF)", callback_data=f"personalized_location_location_{message.chat.id}_{setting_message.message_id}")
                                document_button = types.InlineKeyboardButton("Document RAW Image (ON/OFF)", callback_data=f"personalized_location_document_{message.chat.id}_{setting_message.message_id}")
                                image_button = types.InlineKeyboardButton("Image Content (OFF/Public Only/Private Only)", callback_data=f"personalized_location_image_{message.chat.id}_{setting_message.message_id}")
                                keyboard2.add(image_button)
                                keyboard2.add(location_button)
                                keyboard2.add(document_button)
                                await bot.send_message(message.from_user.id, "Location Breach Prevention Type:", reply_markup=keyboard2)
                            else:
                                await bot.send_message(
                                            message.chat.id,
                                            formatting.format_text(
                                                formatting.munderline("-- NOTIFICATION --"),
                                                formatting.mbold("Please activate personalized privacy bot via /privacy_setting command in group chat first"),
                                                separator="\n"  # separator separates all strings
                                            ),
                                            parse_mode='MarkdownV2',
                                            reply_to_message_id=message.message_id
                                )

                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)


def update_location_value(group_id_to_find, new_activation_value, attribute):

    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for group in groups:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(group['group_id'], key)
            if group_chat_id_decrypted == group_id_to_find:
                if attribute == 'value':
                    # Update the value
                    group['location']['value'] = new_activation_value
                else:
                    group['location']['details'][attribute] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(group_path, 'w') as file:
                json.dump(groups, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('location_on_'))
async def location_on_callback(call):

    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find group chat
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id), None)

        image_setting = group['location']['details']['image']
        location_only_setting = group['location']['details']['location_only']
        document_setting = group['location']['details']['document']

        image_detail = f"1. Location Prevention in Image Content ({'Public Only' if image_setting == 1 else 'Private Only' if image_setting == 2 else 'OFF'})"
        location_detail = f"2. Location Sharing Prevention ({'ON' if location_only_setting == 1 else 'OFF'})"
        document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if document_setting == 1 else 'OFF'})"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(image_detail),
                    escape_markdown_v2(location_detail),
                    escape_markdown_v2(document_detail),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

        await bot.answer_callback_query(call.id, "Location Breach Prevention Has Been Activated")
        update_location_value(group_chat_id, 1, 'value')

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('location_off_'))
async def location_off_callback(call):

    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Location Breach Prevention Has Been Deactivated")
    update_location_value(group_chat_id, 0, 'value')

@bot.callback_query_handler(func=lambda call: call.data.startswith('location_location_'))
async def location_location_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find group chat
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id), None)
        image_setting = group['location']['details']['image']
        location_only_setting = group['location']['details']['location_only']
        document_setting = group['location']['details']['document']

        #next_value
        if location_only_setting == 0:
            next_value = 1
            await bot.answer_callback_query(call.id, "Location Sharing Prevention Has Been Activated")
        else:
            next_value = 0
            await bot.answer_callback_query(call.id, "Location Sharing Prevention Has Been Deactivated")

        update_location_value(group_chat_id, next_value, 'location_only')

        image_detail = f"1. Location Prevention in Image Content ({'Public Only' if image_setting == 1 else 'Private Only' if image_setting == 2 else 'OFF'})"
        location_detail = f"2. Location Sharing Prevention ({'ON' if next_value == 1 else 'OFF'})"
        document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if document_setting == 1 else 'OFF'})"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(image_detail),
                    escape_markdown_v2(location_detail),
                    escape_markdown_v2(document_detail),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('location_document_'))
async def location_document_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find group chat
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id), None)
        image_setting = group['location']['details']['image']
        location_only_setting = group['location']['details']['location_only']
        document_setting = group['location']['details']['document']

        #next_value
        if document_setting == 0:
            next_value = 1
            await bot.answer_callback_query(call.id, "Location Prevention in RAW Image Metadata Has Been Activated")
        else:
            next_value = 0
            await bot.answer_callback_query(call.id, "Location Prevention in RAW Image Metadata Has Been Deactivated")

        update_location_value(group_chat_id, next_value, 'document')

        image_detail = f"1. Location Prevention in Image Content ({'Public Only' if image_setting == 1 else 'Private Only' if image_setting == 2 else 'OFF'})"
        location_detail = f"2. Location Sharing Prevention ({'ON' if location_only_setting == 1 else 'OFF'})"
        document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if next_value == 1 else 'OFF'})"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(image_detail),
                    escape_markdown_v2(location_detail),
                    escape_markdown_v2(document_detail),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('location_image_'))
async def location_image_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find group chat
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id), None)
        image_setting = group['location']['details']['image']
        location_only_setting = group['location']['details']['location_only']
        document_setting = group['location']['details']['document']

        #next_value
        if image_setting == 0:
            next_value = 1
            await bot.answer_callback_query(call.id, "Private Location Prevention in Image Content Has Been Activated")
        elif image_setting == 1:
            next_value = 2
            await bot.answer_callback_query(call.id, "Public Location Prevention in Image Content Has Been Activated")
        else:
            next_value = 0
        await bot.answer_callback_query(call.id, "Location Prevention in Image Content Has Been Deactivated")

        update_location_value(group_chat_id, next_value, 'image')

        image_detail = f"1. Location Prevention in Image Content ({'Public Only' if next_value == 1 else 'Private Only' if next_value == 2 else 'OFF'})"
        location_detail = f"2. Location Sharing Prevention ({'ON' if location_only_setting == 1 else 'OFF'})"
        document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if document_setting == 1 else 'OFF'})"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(image_detail),
                    escape_markdown_v2(location_detail),
                    escape_markdown_v2(document_detail),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def update_personalized_location_value(group_id_to_find, user_id_to_find, new_activation_value, attribute):
    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for user in personalized:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(user['group_id'], key)
            user_id_decrypted = decrypt(user['user_id'], key)
            if (group_chat_id_decrypted == group_id_to_find) and (user_id_decrypted == user_id_to_find):
                # Update the location
                if attribute == 'value':
                    # Update the value
                    user['location']['value'] = new_activation_value
                else:
                    user['location']['details'][attribute] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(personalized_path, 'w') as file:
                json.dump(personalized, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_location_on_'))
async def personalized_location_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Find group chat
        group = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == user_id)), None)

        image_setting = group['location']['details']['image']
        location_only_setting = group['location']['details']['location_only']
        document_setting = group['location']['details']['document']

        image_detail = f"1. Location Prevention in Image Content ({'Public Only' if image_setting == 1 else 'Private Only' if image_setting == 2 else 'OFF'})"
        location_detail = f"2. Location Sharing Prevention ({'ON' if location_only_setting == 1 else 'OFF'})"
        document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if document_setting == 1 else 'OFF'})"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(image_detail),
                    escape_markdown_v2(location_detail),
                    escape_markdown_v2(document_detail),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

        await bot.answer_callback_query(call.id, "Location Breach Prevention Has Been Activated")
        update_personalized_location_value(group_chat_id, user_id, 1, 'value')

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_location_off_'))
async def personalized_location_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Location Breach Prevention Has Been Deactivated")
    update_personalized_location_value(group_chat_id, user_id, 0, 'value')

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_location_location_'))
async def personalized_location_location_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Find group chat
        group = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == user_id)), None)

        image_setting = group['location']['details']['image']
        location_only_setting = group['location']['details']['location_only']
        document_setting = group['location']['details']['document']

        #next_value
        if location_only_setting == 0:
            next_value = 1
            await bot.answer_callback_query(call.id, "Location Sharing Prevention Has Been Activated")
        else:
            next_value = 0
            await bot.answer_callback_query(call.id, "Location Sharing Prevention Has Been Deactivated")

        update_personalized_location_value(group_chat_id, user_id, next_value, 'location_only')

        image_detail = f"1. Location Prevention in Image Content ({'Public Only' if image_setting == 1 else 'Private Only' if image_setting == 2 else 'OFF'})"
        location_detail = f"2. Location Sharing Prevention ({'ON' if next_value == 1 else 'OFF'})"
        document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if document_setting == 1 else 'OFF'})"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(image_detail),
                    escape_markdown_v2(location_detail),
                    escape_markdown_v2(document_detail),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_location_document_'))
async def personalized_location_document_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Find group chat
        group = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == user_id)), None)

        image_setting = group['location']['details']['image']
        location_only_setting = group['location']['details']['location_only']
        document_setting = group['location']['details']['document']

        #next_value
        if document_setting == 0:
            next_value = 1
            await bot.answer_callback_query(call.id, "Location Prevention in RAW Image Metadata Has Been Activated")
        else:
            next_value = 0
            await bot.answer_callback_query(call.id, "Location Prevention in RAW Image Metadata Has Been Deactivated")

        update_personalized_location_value(group_chat_id, user_id, next_value, 'document')

        image_detail = f"1. Location Prevention in Image Content ({'Public Only' if image_setting == 1 else 'Private Only' if image_setting == 2 else 'OFF'})"
        location_detail = f"2. Location Sharing Prevention ({'ON' if location_only_setting == 1 else 'OFF'})"
        document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if next_value == 1 else 'OFF'})"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(image_detail),
                    escape_markdown_v2(location_detail),
                    escape_markdown_v2(document_detail),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_location_image_'))
async def personalized_location_image_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Find group chat
        group = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == user_id)), None)

        image_setting = group['location']['details']['image']
        location_only_setting = group['location']['details']['location_only']
        document_setting = group['location']['details']['document']

        #next_value
        if image_setting == 0:
            next_value = 1
            await bot.answer_callback_query(call.id, "Private Location Prevention in Image Content Has Been Activated")
        elif image_setting == 1:
            next_value = 2
            await bot.answer_callback_query(call.id, "Public Location Prevention in Image Content Has Been Activated")
        else:
            next_value = 0
        await bot.answer_callback_query(call.id, "Location Prevention in Image Content Has Been Deactivated")

        update_personalized_location_value(group_chat_id, user_id, next_value, 'image')

        image_detail = f"1. Location Prevention in Image Content ({'Public Only' if next_value == 1 else 'Private Only' if next_value == 2 else 'OFF'})"
        location_detail = f"2. Location Sharing Prevention ({'ON' if location_only_setting == 1 else 'OFF'})"
        document_detail = f"3. Location Prevention in Raw Image Metadata ({'ON' if document_setting == 1 else 'OFF'})"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- LOCATION PRIVACY SETTING --"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(image_detail),
                    escape_markdown_v2(location_detail),
                    escape_markdown_v2(document_detail),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
            )
        except Exception as e:
            print(f"An error occurred: {e}")

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.message_handler(content_types=['location'])
async def handle_location(message: types.Message):
    if message.chat.type == 'private':
        # Handle location sharing in private chat
        await bot.send_message(message.chat.id, 'You sent location in private with me, be careful of stalking potential', reply_to_message_id=message.message_id)
    else:
        # First, check if the bot is an administrator in this group
        try:
            bot_user = await bot.get_me()
            bot_admin_status = await bot.get_chat_member(message.chat.id, bot_user.id)
            if bot_admin_status.status not in ['administrator', 'creator']:
                await bot.send_message(message.chat.id, "Please change the bot role into administrator to handle all shared contents", reply_to_message_id=message.message_id)
                return  # Bot is not an admin or the creator; do nothing further

            # Read group settings from JSON file
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Decrypt the group_id and check if bot is activated in this group
            group_chat_id = str(message.chat.id)
            group_settings = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

            #bot is activated in this group
            if group_settings:
                global_setting = group_settings['global']
                location_setting = group_settings['location']['value']
                location_only = group_settings['location']['details']['location_only']

                if global_setting == 1:
                    #global setting is activated
                    if location_setting == 1 and location_only == 1:
                        # Use bot.delete_message to delete the location message
                        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                        await bot.send_message(
                            message.chat.id,
                            formatting.format_text(
                                formatting.munderline("-- ALERT --"),
                                formatting.mbold(f"Sorry @{message.from_user.username}, location sharing is not allowed in this group"),
                                separator="\n"  # separator separates all strings
                            ),
                            parse_mode='MarkdownV2'
                        )
                else:
                    #personalized setting is activated
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            # Flag to check if we found the user
                            found = False
                            # Iterate over each group configuration
                            for user in personalized:
                                # Decrypt the group ID and user ID, then check if personalized setting has been activated by user
                                group_chat_id_decrypted = decrypt(user['group_id'], key)
                                user_id_decrypted = decrypt(user['user_id'], key)

                                #check if group chat, user id, activation, and location is activated
                                if (group_chat_id_decrypted == group_chat_id) and (user_id_decrypted == str(message.from_user.id) and (user['activation'] == 1) and (user['location']['value'] == 1) and  (user['location']['details']['location_only'] == 1)):
                                    # Update the activation and all other settings
                                    found = True
                                    break

                            #if personalized setting for location is found
                            if found:
                                # Use bot.delete_message to delete the location message
                                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                                await bot.send_message(
                                    message.from_user.id,
                                    formatting.format_text(
                                        formatting.munderline("-- ALERT --"),
                                        formatting.mbold("Your location sharing in group chat has been prevented successfully"),
                                        separator="\n"  # separator separates all strings
                                    ),
                                    parse_mode='MarkdownV2'
                                )
                                return
                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)
#-------------------END OF BOT COMMAND LOCATION HANDLER-------------------#

#-------------------BOT COMMAND CONTACT HANDLER-------------------#
@bot.message_handler(commands=['contact'])
async def contact_command(message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "Please use the contact command in the group chat directly, thank you", reply_to_message_id=message.message_id)
    elif message.chat.type == 'group' or message.chat.type == 'supergroup':
        group_chat_id = str(message.chat.id)

        # Load the group settings from JSON file
        try:
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Find the group and check if it's activated
            group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)
            if group is None:
                await bot.send_message(message.chat.id, "Please activate privacy bot via /activate command first", reply_to_message_id=message.message_id)
                return
            else:
                # Store the "global" value into a variable called personalized
                global_setting = group['global']
                # Check if global is 1 or 0 (if 0, then personalized setting is activated)
                if global_setting == 1:
                    # Check if the user is an administrator or owner
                    if message.from_user.id in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:

                        contact_setting = group['contact']
                        if contact_setting == 0:
                            # Send the initial setting message
                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- CONTACT PRIVACY SETTING --"),
                                    formatting.mbold("Current Setting: OFF"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            # Create the three buttons
                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("ON", callback_data=f"contact_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("OFF", callback_data=f"contact_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)
                        else:
                            # Send the initial setting message
                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- CONTACT PRIVACY SETTING --"),
                                    formatting.mbold("Current Setting: ON"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            # Create the three buttons
                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("ON", callback_data=f"contact_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("OFF", callback_data=f"contact_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)

                    else:
                        await bot.send_message(message.chat.id, "The command can only be executed by the owner or administrator", reply_to_message_id=message.message_id)
                else:
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            personalized_settings = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == str(message.from_user.id)) and (g['activation'] == 1)), None)

                            if personalized_settings:
                                contact_setting = personalized_settings['contact']

                                if contact_setting == 0:
                                    # Send the initial setting message
                                    setting_message = await bot.send_message(
                                        message.from_user.id,
                                        formatting.format_text(
                                            formatting.munderline("-- CONTACT PRIVACY SETTING --"),
                                            formatting.mbold("Current Setting: OFF"),
                                            separator="\n"  # separator separates all strings
                                        ),
                                        parse_mode='MarkdownV2'
                                    )

                                    # Create the three buttons
                                    keyboard = types.InlineKeyboardMarkup()
                                    on_button = types.InlineKeyboardButton("ON", callback_data=f"personalized_contact_on_{message.chat.id}_{setting_message.message_id}")
                                    off_button = types.InlineKeyboardButton("OFF", callback_data=f"personalized_contact_off_{message.chat.id}_{setting_message.message_id}")
                                    keyboard.add(on_button, off_button)
                                    await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)
                                else:
                                    # Send the initial setting message
                                    setting_message = await bot.send_message(
                                        message.from_user.id,
                                        formatting.format_text(
                                            formatting.munderline("-- CONTACT PRIVACY SETTING --"),
                                            formatting.mbold("Current Setting: ON"),
                                            separator="\n"  # separator separates all strings
                                        ),
                                        parse_mode='MarkdownV2'
                                    )

                                    # Create the three buttons
                                    keyboard = types.InlineKeyboardMarkup()
                                    on_button = types.InlineKeyboardButton("ON", callback_data=f"personalized_contact_on_{message.chat.id}_{setting_message.message_id}")
                                    off_button = types.InlineKeyboardButton("OFF", callback_data=f"personalized_contact_off_{message.chat.id}_{setting_message.message_id}")
                                    keyboard.add(on_button, off_button)
                                    await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)

                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)

def update_contact_value(group_id_to_find, new_activation_value):
    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for group in groups:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(group['group_id'], key)
            if group_chat_id_decrypted == group_id_to_find:
                # Update the activation and all other settings
                group['contact'] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(group_path, 'w') as file:
                json.dump(groups, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('contact_on_'))
async def contact_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- CONTACT PRIVACY SETTING --"),
                formatting.mbold("Current Setting: ON"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Contact Sharing Prevention Has Been Activated")
    update_contact_value(group_chat_id, 1)

@bot.callback_query_handler(func=lambda call: call.data.startswith('contact_off_'))
async def contact_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- CONTACT PRIVACY SETTING --"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Contact Sharing Prevention Has Been Deactivated")
    update_contact_value(group_chat_id, 0)

def update_personalized_contact_value(group_id_to_find, user_id_to_find, new_activation_value):

    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for user in personalized:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(user['group_id'], key)
            user_id_decrypted = decrypt(user['user_id'], key)
            if (group_chat_id_decrypted == group_id_to_find) and (user_id_decrypted == user_id_to_find):
                # Update the contact
                user['contact'] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(personalized_path, 'w') as file:
                json.dump(personalized, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_contact_on_'))
async def personalized_contact_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- CONTACT PRIVACY SETTING --"),
                formatting.mbold("Current Setting: ON"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Contact Sharing Prevention Has Been Activated")
    update_personalized_contact_value(group_chat_id, user_id, 1)


@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_contact_off_'))
async def personalized_contact_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- CONTACT PRIVACY SETTING --"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Contact Sharing Prevention Has Been Deactivated")
    update_personalized_contact_value(group_chat_id, user_id, 0)

@bot.message_handler(content_types=['contact'])
async def handle_contact(message: types.Message):
    if message.chat.type == 'private':
        # Handle contact sharing in private chat
        await bot.send_message(message.chat.id, 'You sent contact in private with me, be careful of stalking potential', reply_to_message_id=message.message_id)
    else:
        # First, check if the bot is an administrator in this group
        try:
            bot_user = await bot.get_me()
            bot_admin_status = await bot.get_chat_member(message.chat.id, bot_user.id)
            if bot_admin_status.status not in ['administrator', 'creator']:
                await bot.send_message(message.chat.id, "Please change the bot role into administrator to handle all shared contents", reply_to_message_id=message.message_id)
                return  # Bot is not an admin or the creator; do nothing further

            # Read group settings from JSON file
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Decrypt the group_id and check if bot is activated in this group
            group_chat_id = str(message.chat.id)
            group_settings = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

            #bot is activated in this group
            if group_settings:
                global_setting = group_settings['global']
                contact_setting = group_settings['contact']

                if global_setting == 1:
                    #global setting is activated
                    if contact_setting == 1:
                        # Use bot.delete_message to delete the contact message
                        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                        await bot.send_message(
                            message.from_user.id,
                            formatting.format_text(
                                formatting.munderline("-- ALERT --"),
                                formatting.mbold("Sorry @{message.from_user.username}, Contact sharing is not allowed in this group"),
                                separator="\n"  # separator separates all strings
                            ),
                            parse_mode='MarkdownV2'
                        )
                else:
                    #personalized setting is activated
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            # Flag to check if we found the user
                            found = False
                            # Iterate over each group configuration
                            for user in personalized:
                                # Decrypt the group ID and user ID, then check if personalized setting has been activated by user
                                group_chat_id_decrypted = decrypt(user['group_id'], key)
                                user_id_decrypted = decrypt(user['user_id'], key)

                                #check if group chat, user id, activation, and contact is activated
                                if (group_chat_id_decrypted == group_chat_id) and (user_id_decrypted == str(message.from_user.id) and (user['activation'] == 1) and (user['contact'] == 1)):
                                    # Update the activation and all other settings
                                    found = True
                                    break

                            #if personalized setting for contact is found
                            if found:
                                # Use bot.delete_message to delete the contact message
                                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                                await bot.send_message(
                                    message.from_user.id,
                                    formatting.format_text(
                                        formatting.munderline("-- ALERT --"),
                                        formatting.mbold("Your contact sharing in group chat has been prevented successfully"),
                                        separator="\n"  # separator separates all strings
                                    ),
                                    parse_mode='MarkdownV2'
                                )
                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)
#-------------------END OF BOT COMMAND CONTACT HANDLER-------------------#

#-------------------BOT COMMAND LINK HANDLER-------------------#
@bot.message_handler(commands=['link'])
async def link_command(message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "Please use the link command in the group chat directly, thank you", reply_to_message_id=message.message_id)
    elif message.chat.type == 'group' or message.chat.type == 'supergroup':
        group_chat_id = str(message.chat.id)

        # Load the group settings from JSON file
        try:
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Find the group and check if it's activated
            group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)
            if group is None:
                await bot.send_message(message.chat.id, "Please activate privacy bot via /activate command first", reply_to_message_id=message.message_id)
                return
            else:
                # Store the "global" value into a variable called personalized
                global_setting = group['global']
                # Check if global is 1 or 0 (if 0, then personalized setting is activated)
                if global_setting == 1:
                    # Check if the user is an administrator or owner
                    if message.from_user.id in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:

                        link_setting = group['link']
                        if link_setting == 0:
                            # Send the initial setting message
                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- LINK PREVIEW PRIVACY SETTING --"),
                                    formatting.mbold("Current Setting: OFF"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            # Create the buttons
                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("ON", callback_data=f"link_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("OFF", callback_data=f"link_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)
                        else:
                            # Send the initial setting message
                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- LINK PREVIEW PRIVACY SETTING --"),
                                    formatting.mbold("Current Setting: ON"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            # Create the buttons
                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("ON", callback_data=f"link_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("OFF", callback_data=f"link_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)
                    else:
                        await bot.send_message(message.chat.id, "The command can only be executed by the owner or administrator", reply_to_message_id=message.message_id)
                else:
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            personalized_settings = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == str(message.from_user.id)) and (g['activation'] == 1)), None)

                            if personalized_settings:
                                contact_setting = personalized_settings['contact']

                                if contact_setting == 0:
                                    # Send the initial setting message
                                    setting_message = await bot.send_message(
                                        message.from_user.id,
                                        formatting.format_text(
                                            formatting.munderline("-- LINK PREVIEW PRIVACY SETTING --"),
                                            formatting.mbold("Current Setting: OFF"),
                                            separator="\n"  # separator separates all strings
                                        ),
                                        parse_mode='MarkdownV2'
                                    )

                                    # Create the three buttons
                                    keyboard = types.InlineKeyboardMarkup()
                                    on_button = types.InlineKeyboardButton("ON", callback_data=f"personalized_link_on_{message.chat.id}_{setting_message.message_id}")
                                    off_button = types.InlineKeyboardButton("OFF", callback_data=f"personalized_link_off_{message.chat.id}_{setting_message.message_id}")
                                    keyboard.add(on_button, off_button)
                                    await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)
                                else:
                                    # Send the initial setting message
                                    setting_message = await bot.send_message(
                                        message.from_user.id,
                                        formatting.format_text(
                                            formatting.munderline("-- LINK PREVIEW PRIVACY SETTING --"),
                                            formatting.mbold("Current Setting: ON"),
                                            separator="\n"  # separator separates all strings
                                        ),
                                        parse_mode='MarkdownV2'
                                    )

                                    # Create the three buttons
                                    keyboard = types.InlineKeyboardMarkup()
                                    on_button = types.InlineKeyboardButton("ON", callback_data=f"personalized_link_on_{message.chat.id}_{setting_message.message_id}")
                                    off_button = types.InlineKeyboardButton("OFF", callback_data=f"personalized_link_off_{message.chat.id}_{setting_message.message_id}")
                                    keyboard.add(on_button, off_button)
                                    await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)

                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)

def update_link_value(group_id_to_find, new_activation_value):

    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for group in groups:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(group['group_id'], key)
            if group_chat_id_decrypted == group_id_to_find:
                # Update the activation and all other settings
                group['link'] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(group_path, 'w') as file:
                json.dump(groups, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('link_on_'))
async def link_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- LINK PREVIEW PRIVACY SETTING --"),
                formatting.mbold("Current Setting: ON"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Link Preview Prevention Has Been Activated")
    update_link_value(group_chat_id, 1)

@bot.callback_query_handler(func=lambda call: call.data.startswith('link_off_'))
async def link_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- LINK PREVIEW PRIVACY SETTING --"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Link Preview Prevention Has Been Deactivated")
    update_link_value(group_chat_id, 0)

def update_personalized_link_value(group_id_to_find, user_id_to_find, new_activation_value):

    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for user in personalized:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(user['group_id'], key)
            user_id_decrypted = decrypt(user['user_id'], key)
            if (group_chat_id_decrypted == group_id_to_find) and (user_id_decrypted == user_id_to_find):
                # Update the link
                user['link'] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(personalized_path, 'w') as file:
                json.dump(personalized, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_link_on_'))
async def personalized_link_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- LINK PREVIEW PRIVACY SETTING --"),
                formatting.mbold("Current Setting: ON"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Link Preview Prevention Has Been Activated")
    update_personalized_link_value(group_chat_id, user_id, 1)

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_link_off_'))
async def personalized_link_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- LINK PREVIEW PRIVACY SETTING --"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Link Preview Prevention Has Been Deactivated")
    update_personalized_link_value(group_chat_id, user_id, 0)
#-------------------END OF BOT COMMAND LINK HANDLER-------------------#

#-------------------BOT FACE COMMAND HANDLER--------------------------#
@bot.message_handler(commands=['face'])
async def face_command(message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "Please use the face command in the group chat directly, thank you", reply_to_message_id=message.message_id)
    elif message.chat.type == 'group' or message.chat.type == 'supergroup':
        group_chat_id = str(message.chat.id)

        # Load the group settings from JSON file
        try:
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Find the group and check if it's activated
            group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)
            if group is None:
                await bot.send_message(message.chat.id, "Please activate privacy bot via /activate command first", reply_to_message_id=message.message_id)
                return
            else:
                # Store the "global" value into a variable called personalized
                global_setting = group['global']
                # Check if global is 1 or 0 (if 0, then personalized setting is activated)
                if global_setting == 1:
                    # Check if the user is an administrator or owner
                    if message.from_user.id in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:

                        face_setting = group['face']
                        face_info = ""
                        if face_setting == 0:
                            face_info = "OFF"
                        elif face_setting == 1:
                            face_info = "Remove Image"
                        elif face_setting == 2:
                            face_info = "Blur The Face"
                        else:
                            face_info = "Change Face Into Emoji"

                        setting_message = await bot.send_message(
                            message.from_user.id,
                            formatting.format_text(
                                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                                formatting.mbold(f"Current Setting: {face_info}"),
                                separator="\n"  # separator separates all strings
                            ),
                            parse_mode='MarkdownV2'
                        )

                        keyboard = types.InlineKeyboardMarkup()
                        off_button = types.InlineKeyboardButton("Turn OFF", callback_data=f"face_off_{message.chat.id}_{setting_message.message_id}")
                        remove_button = types.InlineKeyboardButton("Remove Image", callback_data=f"face_remove_{message.chat.id}_{setting_message.message_id}")
                        blur_button = types.InlineKeyboardButton("Blur The Face", callback_data=f"face_blur_{message.chat.id}_{setting_message.message_id}")
                        emoji_button = types.InlineKeyboardButton("Change Face Into Emoji", callback_data=f"face_emoji_{message.chat.id}_{setting_message.message_id}")
                        keyboard.add(off_button)
                        keyboard.add(remove_button)
                        keyboard.add(blur_button)
                        keyboard.add(emoji_button)
                        await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)
                    else:
                        await bot.send_message(message.chat.id, "The command can only be executed by the owner or administrator", reply_to_message_id=message.message_id)
                else:
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            personalized_settings = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == str(message.from_user.id)) and (g['activation'] == 1)), None)

                            if personalized_settings:
                                face_setting = personalized_settings['face']
                                face_info = ""

                                if face_setting == 0:
                                    face_info = "OFF"
                                elif face_setting == 1:
                                    face_info = "Remove Image"
                                elif face_setting == 2:
                                    face_info = "Blur The Face"
                                else:
                                    face_info = "Change Face Into Emoji"

                                setting_message = await bot.send_message(
                                    message.from_user.id,
                                    formatting.format_text(
                                        formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                                        formatting.mbold(f"Current Setting: {face_info}"),
                                        separator="\n"  # separator separates all strings
                                    ),
                                    parse_mode='MarkdownV2'
                                )

                                keyboard = types.InlineKeyboardMarkup()
                                off_button = types.InlineKeyboardButton("Turn OFF", callback_data=f"personalized_face_off_{message.chat.id}_{setting_message.message_id}")
                                remove_button = types.InlineKeyboardButton("Remove Image", callback_data=f"personalized_face_remove_{message.chat.id}_{setting_message.message_id}")
                                blur_button = types.InlineKeyboardButton("Blur The Face", callback_data=f"personalized_face_blur_{message.chat.id}_{setting_message.message_id}")
                                emoji_button = types.InlineKeyboardButton("Change Face Into Emoji", callback_data=f"personalized_face_emoji_{message.chat.id}_{setting_message.message_id}")
                                keyboard.add(off_button)
                                keyboard.add(remove_button)
                                keyboard.add(blur_button)
                                keyboard.add(emoji_button)
                                await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)

                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)

def update_face_value(group_id_to_find, new_activation_value):

    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for group in groups:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(group['group_id'], key)
            if group_chat_id_decrypted == group_id_to_find:
                # Update the activation and all other settings
                group['face'] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(group_path, 'w') as file:
                json.dump(groups, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('face_off_'))
async def face_photo_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Human Face Prevention In Image Has Been Deactivated")
    update_face_value(group_chat_id, 0)

@bot.callback_query_handler(func=lambda call: call.data.startswith('face_remove_'))
async def face_photo_remove_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                formatting.mbold("Current Setting: Remove Image"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Human Face Prevention In Image Has Been Activated (Remove Image)")
    update_face_value(group_chat_id, 1)

@bot.callback_query_handler(func=lambda call: call.data.startswith('face_blur_'))
async def face_photo_blur_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                formatting.mbold("Current Setting: Blur The Face"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Human Face Prevention In Image Has Been Activated (Blur The Face)")
    update_face_value(group_chat_id, 2)

@bot.callback_query_handler(func=lambda call: call.data.startswith('face_emoji_'))
async def face_photo_emoji_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                formatting.mbold("Current Setting: Change Face Into Emoji"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Human Face Prevention In Image Has Been Activated (Change Face Into Emoji)")
    update_face_value(group_chat_id, 3)

def update_personalized_face_value(group_id_to_find, user_id_to_find, new_activation_value):

    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for user in personalized:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(user['group_id'], key)
            user_id_decrypted = decrypt(user['user_id'], key)
            if (group_chat_id_decrypted == group_id_to_find) and (user_id_decrypted == user_id_to_find):
                # Update the face_photo
                user['face'] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(personalized_path, 'w') as file:
                json.dump(personalized, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_face_off_'))
async def personalized_face_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Human Face Prevention In Image Has Been Deactivated")
    update_personalized_face_value(group_chat_id, user_id, 0)

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_face_remove_'))
async def personalized_face_remove_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                formatting.mbold("Current Setting: Remove Image"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Human Face Prevention In Image Has Been Activated (Remove Image)")
    update_personalized_face_value(group_chat_id, user_id, 1)

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_face_blur_'))
async def personalized_face_blur_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                formatting.mbold("Current Setting: Blur The Face"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Human Face Prevention In Image Has Been Activated (Blur The Face)")
    update_personalized_face_value(group_chat_id, user_id, 2)

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_face_emoji_'))
async def personalized_face_emoji_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- PRIVACY SETTING FOR FACE IN IMAGE --"),
                formatting.mbold("Current Setting: Change Face Into Emoji"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
            chat_id=call.from_user.id,
            message_id=message_id,
        )
    except Exception as e:
        print(f"An error occurred: {e}")

    await bot.answer_callback_query(call.id, "Human Face Prevention In Image Has Been Activated (Change Face Into Emoji)")
    update_personalized_face_value(group_chat_id, user_id, 3)
#-------------------END OF BOT FACE COMMAND HANDLER--------------------------#

#-------------------BOT COMMAND SENTIMENT HANDLER-------------------#
@bot.message_handler(commands=['negative_sentiment'])
async def sentiment_command(message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, "Please use the /negative_sentiment command in the group chat directly, thank you", reply_to_message_id=message.message_id)
    elif message.chat.type == 'group' or message.chat.type == 'supergroup':
        group_chat_id = str(message.chat.id)

        # Load the group settings from JSON file
        try:
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Find the group and check if it's activated
            group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)
            if group is None:
                await bot.send_message(message.chat.id, "Please activate privacy bot via /activate command first", reply_to_message_id=message.message_id)
                return
            else:
                # Store the "global" value into a variable called personalized
                global_setting = group['global']
                # Check if global is 1 or 0 (if 0, then personalized setting is activated)
                if global_setting == 1:
                    # Check if the user is an administrator or owner
                    if message.from_user.id in [admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)]:

                        sentiment_setting = group['sentiment']['value']
                        obscene_setting = group['sentiment']['details']['obscene']
                        threat_setting = group['sentiment']['details']['threat']
                        insult_setting = group['sentiment']['details']['insult']
                        identity_setting = group['sentiment']['details']['identity_attack']
                        sexual_setting = group['sentiment']['details']['sexual_explicit']

                        if obscene_setting == 0:
                            obscene_setting = "OFF"
                        else:
                            obscene_setting = "ON"

                        if threat_setting == 0:
                            threat_setting = "OFF"
                        else:
                            threat_setting = "ON"

                        if insult_setting == 0:
                            insult_setting = "OFF"
                        else:
                            insult_setting = "ON"

                        if identity_setting == 0:
                            identity_setting = "OFF"
                        else:
                            identity_setting = "ON"

                        if sexual_setting == 0:
                            sexual_setting = "OFF"
                        else:
                            sexual_setting = "ON"

                        if sentiment_setting == 0:
                            # Send the initial setting message
                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                                    formatting.mbold("Current Setting: OFF"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("TURN ON", callback_data=f"sentiment_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("TURN OFF", callback_data=f"sentiment_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)

                            keyboard2 = types.InlineKeyboardMarkup()
                            obscene_button = types.InlineKeyboardButton("Obscene", callback_data=f"sentiment_obscene_{message.chat.id}_{setting_message.message_id}")
                            threat_button = types.InlineKeyboardButton("Threatening", callback_data=f"sentiment_threat_{message.chat.id}_{setting_message.message_id}")
                            insult_button = types.InlineKeyboardButton("Insulting", callback_data=f"sentiment_insult_{message.chat.id}_{setting_message.message_id}")
                            identity_button = types.InlineKeyboardButton("Identity Attack", callback_data=f"sentiment_identity_{message.chat.id}_{setting_message.message_id}")
                            sexual_button = types.InlineKeyboardButton("Sexual Explicit", callback_data=f"sentiment_sexual_{message.chat.id}_{setting_message.message_id}")
                            keyboard2.add(obscene_button, threat_button, insult_button)
                            keyboard2.add(identity_button, sexual_button)
                            await bot.send_message(message.from_user.id, "Negative sentiment prevention type:", reply_markup=keyboard2)
                        else:
                            # Send the initial setting message
                            setting_message = await bot.send_message(
                                message.from_user.id,
                                formatting.format_text(
                                    formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                                    formatting.mbold("Current Setting: ON"),
                                    escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                                    escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                                    escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                                    escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                                    escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                            keyboard = types.InlineKeyboardMarkup()
                            on_button = types.InlineKeyboardButton("TURN ON", callback_data=f"sentiment_on_{message.chat.id}_{setting_message.message_id}")
                            off_button = types.InlineKeyboardButton("TURN OFF", callback_data=f"sentiment_off_{message.chat.id}_{setting_message.message_id}")
                            keyboard.add(on_button, off_button)
                            await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)

                            keyboard2 = types.InlineKeyboardMarkup()
                            obscene_button = types.InlineKeyboardButton("Obscene", callback_data=f"sentiment_obscene_{message.chat.id}_{setting_message.message_id}")
                            threat_button = types.InlineKeyboardButton("Threatening", callback_data=f"sentiment_threat_{message.chat.id}_{setting_message.message_id}")
                            insult_button = types.InlineKeyboardButton("Insulting", callback_data=f"sentiment_insult_{message.chat.id}_{setting_message.message_id}")
                            identity_button = types.InlineKeyboardButton("Identity Attack", callback_data=f"sentiment_identity_{message.chat.id}_{setting_message.message_id}")
                            sexual_button = types.InlineKeyboardButton("Sexual Explicit", callback_data=f"sentiment_sexual_{message.chat.id}_{setting_message.message_id}")
                            keyboard2.add(obscene_button, threat_button, insult_button)
                            keyboard2.add(identity_button, sexual_button)
                            await bot.send_message(message.from_user.id, "Negative sentiment prevention type:", reply_markup=keyboard2)
                    else:
                        await bot.send_message(message.chat.id, "The command can only be executed by the owner or administrator", reply_to_message_id=message.message_id)
                else:
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            personalized_setting = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == str(message.from_user.id)) and (g['activation'] == 1)), None)
                            if personalized_setting:

                                sentiment_setting = personalized_setting['sentiment']['value']
                                obscene_setting = personalized_setting['sentiment']['details']['obscene']
                                threat_setting = personalized_setting['sentiment']['details']['threat']
                                insult_setting = personalized_setting['sentiment']['details']['insult']
                                identity_setting = personalized_setting['sentiment']['details']['identity_attack']
                                sexual_setting = personalized_setting['sentiment']['details']['sexual_explicit']

                                if obscene_setting == 0:
                                    obscene_setting = "OFF"
                                else:
                                    obscene_setting = "ON"

                                if threat_setting == 0:
                                    threat_setting = "OFF"
                                else:
                                    threat_setting = "ON"

                                if insult_setting == 0:
                                    insult_setting = "OFF"
                                else:
                                    insult_setting = "ON"

                                if identity_setting == 0:
                                    identity_setting = "OFF"
                                else:
                                    identity_setting = "ON"

                                if sexual_setting == 0:
                                    sexual_setting = "OFF"
                                else:
                                    sexual_setting = "ON"

                                if sentiment_setting == 0:
                                    # Send the initial setting message
                                    setting_message = await bot.send_message(
                                        message.from_user.id,
                                        formatting.format_text(
                                            formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                                            formatting.mbold("Current Setting: OFF"),
                                            separator="\n"  # separator separates all strings
                                        ),
                                        parse_mode='MarkdownV2'
                                    )

                                    keyboard = types.InlineKeyboardMarkup()
                                    on_button = types.InlineKeyboardButton("TURN ON", callback_data=f"personalized_sentiment_on_{message.chat.id}_{setting_message.message_id}")
                                    off_button = types.InlineKeyboardButton("TURN OFF", callback_data=f"personalized_sentiment_off_{message.chat.id}_{setting_message.message_id}")
                                    keyboard.add(on_button, off_button)
                                    await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)

                                    keyboard2 = types.InlineKeyboardMarkup()
                                    obscene_button = types.InlineKeyboardButton("Obscene", callback_data=f"personalized_sentiment_obscene_{message.chat.id}_{setting_message.message_id}")
                                    threat_button = types.InlineKeyboardButton("Threatening", callback_data=f"personalized_sentiment_threat_{message.chat.id}_{setting_message.message_id}")
                                    insult_button = types.InlineKeyboardButton("Insulting", callback_data=f"personalized_sentiment_insult_{message.chat.id}_{setting_message.message_id}")
                                    identity_button = types.InlineKeyboardButton("Identity Attack", callback_data=f"personalized_sentiment_identity_{message.chat.id}_{setting_message.message_id}")
                                    sexual_button = types.InlineKeyboardButton("Sexual Explicit", callback_data=f"personalized_sentiment_sexual_{message.chat.id}_{setting_message.message_id}")
                                    keyboard2.add(obscene_button, threat_button, insult_button)
                                    keyboard2.add(identity_button, sexual_button)
                                    await bot.send_message(message.from_user.id, "Negative sentiment prevention type:", reply_markup=keyboard2)
                                else:
                                    # Send the initial setting message
                                    setting_message = await bot.send_message(
                                        message.from_user.id,
                                        formatting.format_text(
                                            formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                                            formatting.mbold("Current Setting: ON"),
                                            escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                                            escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                                            escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                                            escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                                            escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                                            separator="\n"  # separator separates all strings
                                        ),
                                        parse_mode='MarkdownV2'
                                    )

                                    keyboard = types.InlineKeyboardMarkup()
                                    on_button = types.InlineKeyboardButton("TURN ON", callback_data=f"personalized_sentiment_on_{message.chat.id}_{setting_message.message_id}")
                                    off_button = types.InlineKeyboardButton("TURN OFF", callback_data=f"personalized_sentiment_off_{message.chat.id}_{setting_message.message_id}")
                                    keyboard.add(on_button, off_button)
                                    await bot.send_message(message.from_user.id, "Please select an option below:", reply_markup=keyboard)

                                    keyboard2 = types.InlineKeyboardMarkup()
                                    obscene_button = types.InlineKeyboardButton("Obscene", callback_data=f"personalized_sentiment_obscene_{message.chat.id}_{setting_message.message_id}")
                                    threat_button = types.InlineKeyboardButton("Threatening", callback_data=f"personalized_sentiment_threat_{message.chat.id}_{setting_message.message_id}")
                                    insult_button = types.InlineKeyboardButton("Insulting", callback_data=f"personalized_sentiment_insult_{message.chat.id}_{setting_message.message_id}")
                                    identity_button = types.InlineKeyboardButton("Identity Attack", callback_data=f"personalized_sentiment_identity_{message.chat.id}_{setting_message.message_id}")
                                    sexual_button = types.InlineKeyboardButton("Sexual Explicit", callback_data=f"personalized_sentiment_sexual_{message.chat.id}_{setting_message.message_id}")
                                    keyboard2.add(obscene_button, threat_button, insult_button)
                                    keyboard2.add(identity_button, sexual_button)
                                    await bot.send_message(message.from_user.id, "Negative sentiment prevention type:", reply_markup=keyboard2)

                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)

def update_sentiment_value(group_id_to_find, new_activation_value, attribute):

    try:
        # Load the existing data from the JSON file
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each group configuration
        for group in groups:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(group['group_id'], key)
            if group_chat_id_decrypted == group_id_to_find:
                if attribute == 'value':
                    # Update the value
                    group['sentiment']['value'] = new_activation_value
                else:
                    group['sentiment']['details'][attribute] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(group_path, 'w') as file:
                json.dump(groups, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sentiment_on_'))
async def sentiment_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    update_sentiment_value(group_chat_id, 1, 'value')
    await bot.answer_callback_query(call.id, "Negative Sentiment Prevention Has Been Activated")

    try:
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if obscene_setting == 0:
            obscene_setting = "OFF"
        else:
            obscene_setting = "ON"

        if threat_setting == 0:
            threat_setting = "OFF"
        else:
            threat_setting = "ON"

        if insult_setting == 0:
            insult_setting = "OFF"
        else:
            insult_setting = "ON"

        if identity_setting == 0:
            identity_setting = "OFF"
        else:
            identity_setting = "ON"

        if sexual_setting == 0:
            sexual_setting = "OFF"
        else:
            sexual_setting = "ON"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                    escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                    escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                    escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                    escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                    chat_id=call.from_user.id,
                    message_id=message_id,
            )
        except Exception as e:
                print(f"An unexpected error occurred: {e}")

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sentiment_off_'))
async def sentiment_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    update_sentiment_value(group_chat_id, 0, 'value')
    await bot.answer_callback_query(call.id, "Negative Sentiment Prevention Has Been Deactivated")

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
        )
    except Exception as e:
            print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sentiment_obscene_'))
async def sentiment_obscene_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.from_user.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if obscene_setting == 0:
                obscene_setting = 1
                await bot.answer_callback_query(call.id, "Obscene Chat Prevention Has Been Activated")
            elif obscene_setting == 1:
                obscene_setting = 0
                await bot.answer_callback_query(call.id, "Obscene Chat Prevention Has Been Deactivated")

            update_sentiment_value(group_chat_id, obscene_setting, 'obscene')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sentiment_threat_'))
async def sentiment_threat_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if threat_setting == 0:
                threat_setting = 1
                await bot.answer_callback_query(call.id, "Threatening Chat Prevention Has Been Activated")
            elif threat_setting == 1:
                threat_setting = 0
                await bot.answer_callback_query(call.id, "Threatening Chat Prevention Has Been Deactivated")

            update_sentiment_value(group_chat_id, threat_setting, 'threat')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sentiment_insult_'))
async def sentiment_insult_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if insult_setting == 0:
                insult_setting = 1
                await bot.answer_callback_query(call.id, "Insulting Chat Prevention Has Been Activated")
            elif insult_setting == 1:
                insult_setting = 0
                await bot.answer_callback_query(call.id, "Insulting Chat Prevention Has Been Deactivated")

            update_sentiment_value(group_chat_id, insult_setting, 'insult')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sentiment_identity_'))
async def sentiment_identity_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if identity_setting == 0:
                identity_setting = 1
                await bot.answer_callback_query(call.id, "Identity Attack Chat Prevention Has Been Activated")
            elif identity_setting == 1:
                identity_setting = 0
                await bot.answer_callback_query(call.id, "Identity Attack Chat Prevention Has Been Deactivated")

            update_sentiment_value(group_chat_id, identity_setting, 'identity_attack')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('sentiment_sexual_'))
async def sentiment_sexual_callback(call):
    data = call.data.split('_')
    group_chat_id = data[2]
    message_id = data[3]

    try:
        with open(group_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sexual_setting == 0:
            await bot.answer_callback_query(call.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if sexual_setting == 0:
                sexual_setting = 1
                await bot.answer_callback_query(call.id, "Sexual Explicit Chat Prevention Has Been Activated")
            elif sexual_setting == 1:
                sexual_setting = 0
                await bot.answer_callback_query(call.id, "Sexual Explicit Chat Prevention Has Been Deactivated")

            update_sentiment_value(group_chat_id, sexual_setting, 'sexual_explicit')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def update_personalized_sentiment_value(group_id_to_find, user_id_to_find, new_activation_value, attribute):
    try:
        # Load the existing data from the JSON file
        with open(personalized_path, 'r') as file:
            personalized = json.load(file)

        # Flag to check if we found and updated the entry
        found = False

        # Iterate over each user configuration in the personalized list
        for user in personalized:
            # Decrypt the group ID to see if it matches the group_id_to_find
            group_chat_id_decrypted = decrypt(user['group_id'], key)
            user_id_decrypted = decrypt(user['user_id'], key)
            if (group_chat_id_decrypted == group_id_to_find) and (user_id_decrypted == user_id_to_find):
                # Update the sentiment value or attribute
                if attribute == 'value':
                    user['sentiment']['value'] = new_activation_value
                else:
                    user['sentiment']['details'][attribute] = new_activation_value
                found = True
                break

        # Write back to the JSON file if we made any changes
        if found:
            with open(personalized_path, 'w') as file:
                json.dump(personalized, file, indent=4)

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_sentiment_on_'))
async def personalized_sentiment_on_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    update_personalized_sentiment_value(group_chat_id, user_id, 1, 'value')
    await bot.answer_callback_query(call.id, "Negative Sentiment Prevention Has Been Activated")

    try:
        with open(personalized_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and decrypt(g['user_id'], key) == user_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if obscene_setting == 0:
            obscene_setting = "OFF"
        else:
            obscene_setting = "ON"

        if threat_setting == 0:
            threat_setting = "OFF"
        else:
            threat_setting = "ON"

        if insult_setting == 0:
            insult_setting = "OFF"
        else:
            insult_setting = "ON"

        if identity_setting == 0:
            identity_setting = "OFF"
        else:
            identity_setting = "ON"

        if sexual_setting == 0:
            sexual_setting = "OFF"
        else:
            sexual_setting = "ON"

        try:
            await bot.edit_message_text(
                formatting.format_text(
                    formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                    formatting.mbold("Current Setting: ON"),
                    escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                    escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                    escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                    escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                    escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                    separator="\n"  # separator separates all strings
                ),
                parse_mode='MarkdownV2',
                    chat_id=call.from_user.id,
                    message_id=message_id,
            )
        except Exception as e:
                print(f"An unexpected error occurred: {e}")

    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_sentiment_off_'))
async def personalized_sentiment_off_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    update_personalized_sentiment_value(group_chat_id, user_id, 0, 'value')
    await bot.answer_callback_query(call.id, "Negative Sentiment Prevention Has Been Deactivated")

    try:
        await bot.edit_message_text(
            formatting.format_text(
                formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                formatting.mbold("Current Setting: OFF"),
                separator="\n"  # separator separates all strings
            ),
            parse_mode='MarkdownV2',
                chat_id=call.from_user.id,
                message_id=message_id,
        )
    except Exception as e:
            print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_sentiment_obscene_'))
async def personalized_sentiment_obscene_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        with open(personalized_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and decrypt(g['user_id'], key) == user_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.from_user.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if obscene_setting == 0:
                obscene_setting = 1
                await bot.answer_callback_query(call.id, "Obscene Chat Prevention Has Been Activated")
            elif obscene_setting == 1:
                obscene_setting = 0
                await bot.answer_callback_query(call.id, "Obscene Chat Prevention Has Been Deactivated")

            update_personalized_sentiment_value(group_chat_id, user_id, obscene_setting, 'obscene')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_sentiment_threat_'))
async def personalized_sentiment_threat_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        with open(personalized_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and decrypt(g['user_id'], key) == user_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.from_user.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if threat_setting == 0:
                threat_setting = 1
                await bot.answer_callback_query(call.id, "Threatening Chat Prevention Has Been Activated")
            elif threat_setting == 1:
                threat_setting = 0
                await bot.answer_callback_query(call.id, "Threatening Chat Prevention Has Been Deactivated")

            update_personalized_sentiment_value(group_chat_id, user_id, threat_setting, 'threat')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_sentiment_insult_'))
async def personalized_sentiment_insult_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        with open(personalized_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and decrypt(g['user_id'], key) == user_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.from_user.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if insult_setting == 0:
                insult_setting = 1
                await bot.answer_callback_query(call.id, "Insulting Chat Prevention Has Been Activated")
            elif insult_setting == 1:
                insult_setting = 0
                await bot.answer_callback_query(call.id, "Insulting Chat Prevention Has Been Deactivated")

            update_personalized_sentiment_value(group_chat_id,  user_id, insult_setting, 'insult')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_sentiment_identity_'))
async def personalized_sentiment_identity_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        with open(personalized_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and decrypt(g['user_id'], key) == user_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.from_user.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if identity_setting == 0:
                identity_setting = 1
                await bot.answer_callback_query(call.id, "Identity Attack Chat Prevention Has Been Activated")
            elif identity_setting == 1:
                identity_setting = 0
                await bot.answer_callback_query(call.id, "Identity Attack Chat Prevention Has Been Deactivated")

            update_personalized_sentiment_value(group_chat_id, user_id, identity_setting, 'identity_attack')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('personalized_sentiment_sexual_'))
async def personalized_sentiment_sexual_callback(call):
    data = call.data.split('_')
    group_chat_id = data[3]
    message_id = data[4]
    user_id = str(call.from_user.id)

    try:
        with open(personalized_path, 'r') as file:
            groups = json.load(file)

        # Find the group and check if it's activated
        group = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and decrypt(g['user_id'], key) == user_id and g['activation'] == 1), None)

        sentiment_setting = group['sentiment']['value']
        obscene_setting = group['sentiment']['details']['obscene']
        threat_setting = group['sentiment']['details']['threat']
        insult_setting = group['sentiment']['details']['insult']
        identity_setting = group['sentiment']['details']['identity_attack']
        sexual_setting = group['sentiment']['details']['sexual_explicit']

        if sentiment_setting == 0:
            await bot.answer_callback_query(call.from_user.id, "Please Activate Negative Sentiment Prevention First")
        else:
            if sexual_setting == 0:
                sexual_setting = 1
                await bot.answer_callback_query(call.id, "Sexual Explicit Chat Prevention Has Been Activated")
            elif sexual_setting == 1:
                sexual_setting = 0
                await bot.answer_callback_query(call.id, "Sexual Explicit Chat Prevention Has Been Deactivated")

            update_personalized_sentiment_value(group_chat_id, user_id, sexual_setting, 'sexual_explicit')

            if obscene_setting == 0:
                obscene_setting = "OFF"
            else:
                obscene_setting = "ON"

            if threat_setting == 0:
                threat_setting = "OFF"
            else:
                threat_setting = "ON"

            if insult_setting == 0:
                insult_setting = "OFF"
            else:
                insult_setting = "ON"

            if identity_setting == 0:
                identity_setting = "OFF"
            else:
                identity_setting = "ON"

            if sexual_setting == 0:
                sexual_setting = "OFF"
            else:
                sexual_setting = "ON"

            try:
                await bot.edit_message_text(
                    formatting.format_text(
                        formatting.munderline("-- NEGATIVE SENTIMENT PREVENTION FOR CHAT--"),
                        formatting.mbold("Current Setting: ON"),
                        escape_markdown_v2(f"1. Obscene chat prevention: {obscene_setting}"),
                        escape_markdown_v2(f"2. Threatening chat prevention: {threat_setting}"),
                        escape_markdown_v2(f"3. Insulting chat prevention: {insult_setting}"),
                        escape_markdown_v2(f"4. Identity Attack chat prevention: {identity_setting}"),
                        escape_markdown_v2(f"5. Sexual Explicit chat prevention: {sexual_setting}"),
                        separator="\n"  # separator separates all strings
                    ),
                    parse_mode='MarkdownV2',
                        chat_id=call.from_user.id,
                        message_id=message_id,
                )
            except Exception as e:
                    print(f"An unexpected error occurred: {e}")
    except IOError as e:
        print(f"An error occurred while accessing the file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
#-------------------END OF BOT COMMAND SENTIMENT HANDLER-------------------#

#-------------------BOT TEXT CHAT HANDLER--------------------------#
@bot.message_handler(content_types=['text'])
async def handle_chat(message: types.Message):
    if message.chat.type == 'private':
        # Handle link sharing in private chat
        if message.entities and any(entity.type == 'url' for entity in message.entities):
            if getattr(message.link_preview_options, 'is_disabled', True):
                # If is_disabled is True, it means link preview was intentionally disabled
                await bot.send_message(message.chat.id, 'You sent a link without preview.', reply_to_message_id=message.message_id)
            else:
                # If is_disabled is not True, it means link preview is active
                await bot.send_message(message.chat.id, 'You sent a link with preview.', reply_to_message_id=message.message_id)
                preview_options = LinkPreviewOptions(is_disabled=True)
                full_name = f"{message.from_user.first_name} {message.from_user.last_name}"
                message_text = f"{full_name} send {message.text}"
                await bot.send_message(message.chat.id, message_text, reply_to_message_id=message.message_id, link_preview_options=preview_options)
    else:
        # First, check if the bot is an administrator in this group
        try:
            bot_user = await bot.get_me()
            bot_admin_status = await bot.get_chat_member(message.chat.id, bot_user.id)
            if bot_admin_status.status not in ['administrator', 'creator']:
                await bot.send_message(message.chat.id, "Please change the bot role into administrator to handle all shared contents", reply_to_message_id=message.message_id)
                return  # Bot is not an admin or the creator; do nothing further

            # Read group settings from JSON file
            with open(group_path, 'r') as file:
                groups = json.load(file)

            group_chat_id = str(message.chat.id)

            group_settings = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)
            #bot is activated in this group
            if group_settings:
                global_setting = group_settings['global']
                link_setting = group_settings['link']
                sentiment_setting = group_settings['sentiment']['value']

                if global_setting == 1:
                    #global setting is activated

                    # Check if message contains a URL
                    if message.entities and any(entity.type == 'url' for entity in message.entities):
                        if link_setting == 1:
                            #check if link preview prevention is activated
                            global_link_settings = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['link'] == 1), None)
                            if global_link_settings:
                                # Decide action based on link preview settings
                                if getattr(message.link_preview_options, 'is_disabled', True):
                                    return
                                else:
                                    # If link preview exists, delete the message and resend without preview
                                    preview_options = LinkPreviewOptions(is_disabled=True)
                                    await bot.send_message(
                                        message.chat.id,
                                        formatting.format_text(
                                            formatting.munderline("-- MESSAGE --"),
                                            formatting.mbold(f"@{message.from_user.username} send {message.text}"),
                                            separator="\n"  # separator separates all strings
                                        ),
                                        parse_mode='MarkdownV2',
                                        link_preview_options=preview_options
                                    )
                                    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                    else:
                        if sentiment_setting == 1:
                            #Use detox result with unbiased dataset
                            detox_results = Detoxify('unbiased').predict(message.text)
                            if(detox_results['toxicity'] > 0.5):
                                response = ''
                                if detox_results['obscene'] > 0.5 and group_settings['sentiment']['details']['obscene'] == 1:
                                    response += 'obscene, '
                                if detox_results['threat'] > 0.5 and group_settings['sentiment']['details']['threat'] == 1:
                                    response += 'threatening, '
                                if detox_results['insult'] > 0.5 and group_settings['sentiment']['details']['insult'] == 1:
                                    response += 'insulting, '
                                if detox_results['identity_attack'] > 0.5 and group_settings['sentiment']['details']['identity_attack'] == 1:
                                    response += 'identity attack, '
                                if detox_results['sexual_explicit'] > 0.5 and group_settings['sentiment']['details']['sexual_explicit'] == 1:
                                    response += 'sexual explicit'

                                response = response.rstrip(', ')
                                # Replace the last occurrence of ", " with " and "
                                if ', ' in response:
                                    response = response[::-1].replace(', '[::-1], 'and '[::-1], 1)[::-1]

                                if response != '':
                                    await bot.send_message(
                                        message.chat.id,
                                        formatting.format_text(
                                            formatting.munderline("-- ALERT --"),
                                            formatting.mbold(f"Your text chat contains elements that are {response}. Please be mindful of the community guidelines @{message.from_user.username}"),
                                            separator="\n"  # separator separates all strings
                                        ),
                                        parse_mode='MarkdownV2'
                                    )
                                    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                else:
                    #personalized setting is activated
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:

                            user_setting = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == str(message.from_user.id)) and (g['activation'] == 1)), None)

                            if user_setting:
                                link_setting = user_setting['link']
                                sentiment_setting = user_setting['sentiment']['value']

                                # Check if message contains a URL
                                if message.entities and any(entity.type == 'url' for entity in message.entities):
                                    if link_setting == 1:
                                        #check if link preview prevention is activated
                                        if getattr(message.link_preview_options, 'is_disabled', True):
                                            return
                                        else:
                                            # If link preview exists, delete the message and resend without preview
                                            preview_options = LinkPreviewOptions(is_disabled=True)
                                            await bot.send_message(
                                                message.chat.id,
                                                formatting.format_text(
                                                    formatting.munderline("-- MESSAGE --"),
                                                    formatting.mbold(f"@{message.from_user.username} send {message.text}"),
                                                    separator="\n"  # separator separates all strings
                                                ),
                                                parse_mode='MarkdownV2',
                                                link_preview_options=preview_options
                                            )

                                            await bot.send_message(
                                                message.from_user.id,
                                                formatting.format_text(
                                                    formatting.munderline("-- ALERT --"),
                                                    formatting.mbold("Your link preview has been prevented in group chat!"),
                                                    separator="\n"  # separator separates all strings
                                                ),
                                                parse_mode='MarkdownV2'
                                            )
                                            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                                else:
                                    if sentiment_setting == 1:
                                        #Use detox result with unbiased dataset
                                        detox_results = Detoxify('unbiased').predict(message.text)
                                        if(detox_results['toxicity'] > 0.5):
                                            response = ''
                                            if detox_results['obscene'] > 0.5 and user_setting['sentiment']['details']['obscene'] == 1:
                                                response += 'obscene, '
                                            if detox_results['threat'] > 0.5 and user_setting['sentiment']['details']['threat'] == 1:
                                                response += 'threatening, '
                                            if detox_results['insult'] > 0.5 and user_setting['sentiment']['details']['insult'] == 1:
                                                response += 'insulting, '
                                            if detox_results['identity_attack'] > 0.5 and user_setting['sentiment']['details']['identity_attack'] == 1:
                                                response += 'identity attack, '
                                            if detox_results['sexual_explicit'] > 0.5 and user_setting['sentiment']['details']['sexual_explicit'] == 1:
                                                response += 'sexual explicit'

                                            response = response.rstrip(', ')
                                            # Replace the last occurrence of ", " with " and "
                                            if ', ' in response:
                                                response = response[::-1].replace(', '[::-1], 'dna '[::-1], 1)[::-1]

                                            if response != '':
                                                await bot.send_message(
                                                    message.from_user.id,
                                                    formatting.format_text(
                                                        formatting.munderline("-- ALERT --"),
                                                        formatting.mbold(f"Your text chat contains elements that are {response}. It has been prevented in group chat!"),
                                                        separator="\n"  # separator separates all strings
                                                    ),
                                                    parse_mode='MarkdownV2'
                                                )
                                                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)
#-------------------END OF BOT TEXT CHAT HANDLER-------------------#

#-------------------BOT IMAGE FILE HANDLER--------------------------#
# Define VGG16_Places365 model architecture
def VGG16_Places365(weights_path=None):
    input_layer = Input(shape=(224, 224, 3))

    # Block 1
    x = Conv2D(64, (3, 3), activation='relu', padding='same', name='block1_conv1')(input_layer)
    x = Conv2D(64, (3, 3), activation='relu', padding='same', name='block1_conv2')(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block1_pool')(x)

    # Block 2
    x = Conv2D(128, (3, 3), activation='relu', padding='same', name='block2_conv1')(x)
    x = Conv2D(128, (3, 3), activation='relu', padding='same', name='block2_conv2')(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block2_pool')(x)

    # Block 3
    x = Conv2D(256, (3, 3), activation='relu', padding='same', name='block3_conv1')(x)
    x = Conv2D(256, (3, 3), activation='relu', padding='same', name='block3_conv2')(x)
    x = Conv2D(256, (3, 3), activation='relu', padding='same', name='block3_conv3')(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block3_pool')(x)

    # Block 4
    x = Conv2D(512, (3, 3), activation='relu', padding='same', name='block4_conv1')(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same', name='block4_conv2')(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same', name='block4_conv3')(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block4_pool')(x)

    # Block 5
    x = Conv2D(512, (3, 3), activation='relu', padding='same', name='block5_conv1')(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same', name='block5_conv2')(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same', name='block5_conv3')(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block5_pool')(x)

    # Classification block
    x = Flatten(name='flatten')(x)
    x = Dense(4096, activation='relu', name='fc1')(x)
    x = Dense(4096, activation='relu', name='fc2')(x)
    x = Dense(365, activation='softmax', name='predictions')(x)

    model = Model(inputs=input_layer, outputs=x, name='vgg16-places365')

    if weights_path:
        model.load_weights(weights_path)

    return model

# Paths to the model and categories file
WEIGHTS_PATH = 'configuration/vgg16-places365_weights_tf_dim_ordering_tf_kernels.h5'
CATEGORIES_PATH = 'configuration/categories_places365_map.txt'

# Load the VGG16_Places365 model with weights
place365_model = VGG16_Places365(weights_path=WEIGHTS_PATH)

# Load the class labels
with open(CATEGORIES_PATH) as class_file:
    classes = [line.strip().split(' ')[0][3:] for line in class_file]
classes = tuple(classes)

#human face detection model
face_model = YOLO('configuration/yolov8n-face.pt')

@bot.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, 'You send photo with me, thanks, but be mindful when sharing with unknown people', reply_to_message_id=message.message_id)
    else:
        # First, check if the bot is an administrator in this group
        try:
            bot_user = await bot.get_me()
            bot_admin_status = await bot.get_chat_member(message.chat.id, bot_user.id)
            if bot_admin_status.status not in ['administrator', 'creator']:
                await bot.send_message(message.chat.id, "Please change the bot role into administrator to handle all shared contents", reply_to_message_id=message.message_id)
                return

            # Read group settings from JSON file
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Decrypt the group_id and check settings
            group_chat_id = str(message.chat.id)
            group_settings = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

            if group_settings:
                global_setting = group_settings['global']
                face_setting = group_settings['face']
                location_setting = group_settings['location']['value']
                location_image_setting = group_settings['location']['details']['image']

                if global_setting == 1:
                    #global setting is activated

                    # Handle photo sharing in group chat
                    file_id = message.photo[-1].file_id
                    file_info = await bot.get_file(file_id)
                    file_path = file_info.file_path
                    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

                    # Download the image
                    image_folder = 'image'
                    os.makedirs(image_folder, exist_ok=True)
                    unique_filename = f"{image_folder}/{file_id}.jpg"
                    urllib.request.urlretrieve(file_url, unique_filename)

                    #initialize privacy breach
                    location_breach = ""
                    face_breach = False
                    formatted_place = ""
                    message_deleted = False

                    if (location_setting == 1) and (location_image_setting != 0):
                        #location setting is activated

                        # Load and preprocess the image
                        image = Image.open(unique_filename)
                        image = np.array(image, dtype=np.uint8)
                        image = cv2.resize(image, (224, 224))
                        image = np.expand_dims(image, 0)

                        # Predict the scene
                        preds = place365_model.predict(image)[0]
                        top_pred = np.argsort(preds)[::-1][0]

                        # Output the prediction
                        predicted_scene = classes[top_pred]
                        place, place_type = predicted_scene.split('-')

                        if (location_image_setting == 1) and (place_type == 'private'):
                            #public location only, private is not allowed
                            location_breach = "private"
                            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                            message_deleted = True
                        elif (location_image_setting == 2) and place_type == 'public':
                            #private location only, public is not allowed
                            location_breach = "public"
                            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                            message_deleted = True

                    if face_setting != 0:
                        #face setting is activated (remove, blur, or emoji)
                        image_face_check = Image.open(unique_filename)

                        # YOLOv8 face detection
                        results = face_model.predict(image_face_check, conf=0.40)

                        # Convert the PIL image to an OpenCV image
                        image_face_check = cv2.imread(unique_filename)

                        if results:
                            #face breach detected
                            face_breach = True
                            if message_deleted == False:
                                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

                            if face_setting == 2: #blur
                                for info in results:
                                    boxes = info.boxes
                                    for box in boxes:
                                        x1, y1, x2, y2 = box.xyxy[0]
                                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                                        w, h = x2 - x1, y2 - y1

                                        face = image_face_check[y1:y1+h, x1:x1+w]
                                        face = cv2.GaussianBlur(face, (23, 23), 30)
                                        image_face_check[y1:y1+h, x1:x1+w] = face

                                        # Save the processed image
                                        processed_filename = f"{image_folder}/processed_{file_id}.jpg"
                                        cv2.imwrite(processed_filename, image_face_check)

                                #if no location breach, send the image back to the chat
                                if (location_breach == ""):
                                    with open(processed_filename, 'rb') as photo:
                                        await bot.send_photo(message.chat.id, photo)

                                # Cleanup: Delete the processed image files from the server
                                os.remove(processed_filename)

                            elif face_setting == 3: #emoji
                                for info in results:
                                    boxes = info.boxes
                                    for box in boxes:
                                        x1, y1, x2, y2 = box.xyxy[0]
                                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                                        w, h = x2 - x1, y2 - y1

                                        emoji = cv2.imread('image/emoji.png', cv2.IMREAD_UNCHANGED)
                                        emoji_resized = cv2.resize(emoji, (w, h))

                                        # Check if emoji has an alpha channel
                                        if emoji_resized.shape[2] == 4:
                                            # Split the channels in the emoji image
                                            b, g, r, alpha = cv2.split(emoji_resized)
                                            # Create an RGB version of the resized emoji
                                            emoji_rgb = cv2.merge((b, g, r))
                                            # Create a mask using the alpha channel
                                            mask_inv = cv2.bitwise_not(alpha)

                                            # Black-out the area of the face in the original image
                                            roi = image_face_check[y1:y1+h, x1:x1+w]
                                            img_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)

                                            # Take only region of the emoji from emoji image.
                                            emoji_fg = cv2.bitwise_and(emoji_rgb, emoji_rgb, mask=alpha)

                                            # Put the emoji in the ROI and modify the main image
                                            dst = cv2.add(img_bg, emoji_fg)
                                            image_face_check[y1:y1+h, x1:x1+w] = dst

                                        # Save the processed image
                                        processed_filename = f"{image_folder}/processed_{file_id}.jpg"
                                        cv2.imwrite(processed_filename, image_face_check)

                                #if no location breach, send the image back to the chat
                                if (location_breach == ""):
                                    with open(processed_filename, 'rb') as photo:
                                        await bot.send_photo(message.chat.id, photo)

                                # Cleanup: Delete the processed image files from the server
                                os.remove(processed_filename)

                        if (face_breach) and (location_breach!=""):
                            await bot.send_message(
                                message.chat.id,
                                formatting.format_text(
                                    formatting.munderline("-- ALERT --"),
                                    formatting.mbold(f"Two privacy breaches detected, human face is detected in the image and the scenery recognized as a {location_breach} location @{message.from_user.username}"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )
                        elif (face_setting !=0) and (face_breach):
                            await bot.send_message(
                                message.chat.id,
                                formatting.format_text(
                                    formatting.munderline("-- ALERT --"),
                                    formatting.mbold(f"A privacy breach detected, human face is detected in the image @{message.from_user.username}"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )
                        elif (location_setting == 1) and (location_breach!=""):
                            await bot.send_message(
                                message.chat.id,
                                formatting.format_text(
                                    formatting.munderline("-- ALERT --"),
                                    formatting.mbold(f"A privacy breach detected, the scenery recognized as a {location_breach} location @{message.from_user.username}"),
                                    separator="\n"  # separator separates all strings
                                ),
                                parse_mode='MarkdownV2'
                            )

                    #remove original image
                    os.remove(unique_filename)

                else:
                    #personalized setting is activated
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            personalized_setting = next((g for g in personalized if (decrypt(g['group_id'], key) == group_chat_id) and (decrypt(g['user_id'], key) == str(message.from_user.id)) and (g['activation'] == 1)), None)

                            if personalized_setting:
                                face_setting = personalized_setting['face']
                                location_setting = personalized_setting['location']['value']
                                location_image_setting = personalized_setting['location']['details']['image']

                                # Handle photo sharing in group chat
                                file_id = message.photo[-1].file_id
                                file_info = await bot.get_file(file_id)
                                file_path = file_info.file_path
                                file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
                                # Download the image
                                image_folder = 'image'
                                os.makedirs(image_folder, exist_ok=True)
                                unique_filename = f"{image_folder}/{file_id}.jpg"
                                urllib.request.urlretrieve(file_url, unique_filename)

                                #initialize privacy breach
                                location_breach = ""
                                face_breach = False
                                formatted_place = ""
                                message_deleted = False

                                if (location_setting == 1) and (location_image_setting != 0):
                                    #location setting is activated

                                    # Load and preprocess the image
                                    image = Image.open(unique_filename)
                                    image = np.array(image, dtype=np.uint8)
                                    image = cv2.resize(image, (224, 224))
                                    image = np.expand_dims(image, 0)

                                    # Predict the scene
                                    preds = place365_model.predict(image)[0]

                                    top_pred = np.argsort(preds)[::-1][0]

                                    # Output the prediction
                                    predicted_scene = classes[top_pred]
                                    place, place_type = predicted_scene.split('-')

                                    if (location_image_setting == 1) and (place_type == 'private'):
                                        #public location only, private not allowed
                                        location_breach = "private"
                                        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                                        message_deleted = True
                                    elif (location_image_setting == 2) and place_type == 'public':
                                        #private location only, public not allowed
                                        location_breach = "public"
                                        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                                        message_deleted = True

                                    if face_setting != 0:
                                        #face setting is activated (remove, blur, or emoji)
                                        image_face_check = Image.open(unique_filename)

                                        # YOLOv8 face detection
                                        results = face_model.predict(image_face_check, conf=0.40)

                                        # Convert the PIL image to an OpenCV image
                                        image_face_check = cv2.imread(unique_filename)

                                        if results:
                                            #face breach detected
                                            face_breach = True
                                            if message_deleted == False:
                                                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

                                            if face_setting == 2: #blur
                                                for info in results:
                                                    boxes = info.boxes
                                                    for box in boxes:
                                                        x1, y1, x2, y2 = box.xyxy[0]
                                                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                                                        w, h = x2 - x1, y2 - y1

                                                        face = image_face_check[y1:y1+h, x1:x1+w]
                                                        face = cv2.GaussianBlur(face, (23, 23), 30)
                                                        image_face_check[y1:y1+h, x1:x1+w] = face

                                                        # Save the processed image
                                                        processed_filename = f"{image_folder}/processed_{file_id}.jpg"
                                                        cv2.imwrite(processed_filename, image_face_check)

                                                #if no location breach, send the image back to the chat
                                                if (location_breach == ""):
                                                    with open(processed_filename, 'rb') as photo:
                                                        await bot.send_photo(message.chat.id, photo, caption=f"Image from @{message.from_user.username}")

                                                # Cleanup: Delete the processed image files from the server
                                                os.remove(processed_filename)

                                            elif face_setting == 3: #emoji
                                                for info in results:
                                                    boxes = info.boxes
                                                    for box in boxes:
                                                        x1, y1, x2, y2 = box.xyxy[0]
                                                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                                                        w, h = x2 - x1, y2 - y1

                                                        emoji = cv2.imread('image/emoji.png', cv2.IMREAD_UNCHANGED)
                                                        emoji_resized = cv2.resize(emoji, (w, h))

                                                        # Check if emoji has an alpha channel
                                                        if emoji_resized.shape[2] == 4:
                                                            # Split the channels in the emoji image
                                                            b, g, r, alpha = cv2.split(emoji_resized)
                                                            # Create an RGB version of the resized emoji
                                                            emoji_rgb = cv2.merge((b, g, r))
                                                            # Create a mask using the alpha channel
                                                            mask_inv = cv2.bitwise_not(alpha)

                                                            # Black-out the area of the face in the original image
                                                            roi = image_face_check[y1:y1+h, x1:x1+w]
                                                            img_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)

                                                            # Take only region of the emoji from emoji image.
                                                            emoji_fg = cv2.bitwise_and(emoji_rgb, emoji_rgb, mask=alpha)

                                                            # Put the emoji in the ROI and modify the main image
                                                            dst = cv2.add(img_bg, emoji_fg)
                                                            image_face_check[y1:y1+h, x1:x1+w] = dst

                                                        # Save the processed image
                                                        processed_filename = f"{image_folder}/processed_{file_id}.jpg"
                                                        cv2.imwrite(processed_filename, image_face_check)

                                                #if no location breach, send the image back to the chat
                                                if (location_breach == ""):
                                                    with open(processed_filename, 'rb') as photo:
                                                        await bot.send_photo(message.chat.id, photo, caption=f"Image from @{message.from_user.username}")

                                                # Cleanup: Delete the processed image files from the server
                                                os.remove(processed_filename)

                                        if (face_breach) and (location_breach!=""):
                                            await bot.send_message(
                                                message.from_user.id,
                                                formatting.format_text(
                                                    formatting.munderline("-- ALERT --"),
                                                    formatting.mbold(f"Two privacy breaches detected, human face is detected in the image and the scenery recognized as a {location_breach} location!"),
                                                    separator="\n"  # separator separates all strings
                                                ),
                                                parse_mode='MarkdownV2'
                                            )
                                        elif (face_setting !=0) and (face_breach):
                                            await bot.send_message(
                                                message.from_user.id,
                                                formatting.format_text(
                                                    formatting.munderline("-- ALERT --"),
                                                    formatting.mbold(f"A privacy breach detected, human face is detected in the image!"),
                                                    separator="\n"  # separator separates all strings
                                                ),
                                                parse_mode='MarkdownV2'
                                            )
                                        elif (location_setting == 1) and (location_breach!=""):
                                            await bot.send_message(
                                                message.from_user.id,
                                                formatting.format_text(
                                                    formatting.munderline("-- ALERT --"),
                                                    formatting.mbold(f"A privacy breach detected, the scenery recognized as a {location_breach} location!"),
                                                    separator="\n"  # separator separates all strings
                                                ),
                                                parse_mode='MarkdownV2'
                                            )

                                    #remove original image
                                    os.remove(unique_filename)

                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)
#-------------------END OF BOT IMAGE HANDLER--------------------------#

#-------------------BOT DOCUMENT IMAGE HANDLER--------------------------#
@bot.message_handler(content_types=['document'])
async def handle_document(message: types.Message):
    if message.chat.type == 'private':
        await bot.send_message(message.chat.id, 'You sent a document to me, thanks, but be careful when sharing it with unknown people!', reply_to_message_id=message.message_id)
    else:
        # First, check if the bot is an administrator in this group
        try:
            bot_user = await bot.get_me()
            bot_admin_status = await bot.get_chat_member(message.chat.id, bot_user.id)
            if bot_admin_status.status not in ['administrator', 'creator']:
                await bot.send_message(message.chat.id, "Please change the bot role into administrator to handle all shared contents", reply_to_message_id=message.message_id)
                return

            # Read group settings from JSON file
            with open(group_path, 'r') as file:
                groups = json.load(file)

            # Decrypt the group_id and check if bot is activated in this group
            group_chat_id = str(message.chat.id)
            group_settings = next((g for g in groups if decrypt(g['group_id'], key) == group_chat_id and g['activation'] == 1), None)

            #bot is activated in this group
            if group_settings:
                global_setting = group_settings['global']
                location_setting = group_settings['location']['value']
                location_document_setting = group_settings['location']['details']['document']

                if global_setting == 1:
                    #global setting is activated
                    if (location_setting == 1) and (location_document_setting == 1):

                        document = message.document
                        if document.mime_type.startswith('image/'):
                            file_info = await bot.get_file(document.file_id)
                            file_path = file_info.file_path
                            file_extension = file_path.split('.')[-1]

                            if file_extension.lower() in ['jpg', 'jpeg', 'png']:
                                # Prepare a folder to store images
                                image_folder = 'image'
                                os.makedirs(image_folder, exist_ok=True)  # Ensure the directory exists

                                # Define paths for the original and modified images
                                original_file_path = f'{image_folder}/{document.file_id}.{file_extension}'
                                modified_file_path = f'{image_folder}/modified_{document.file_id}.{file_extension}'

                                # Download the image file into the image folder
                                downloaded_file_data = await bot.download_file(file_path)
                                with open(original_file_path, 'wb') as image_file:
                                    image_file.write(downloaded_file_data)

                                GPS_found = False
                                # Process the image to remove EXIF
                                with Image.open(original_file_path) as image:
                                    exif_data = image.info.get('exif')
                                    if exif_data:
                                        exif_dict = piexif.load(exif_data)
                                        if 'GPS' in exif_dict:
                                            GPS_found = True
                                            del exif_dict['GPS']
                                            new_exif = piexif.dump(exif_dict)
                                            image.save(modified_file_path, exif=new_exif)
                                        else:
                                            image.save(modified_file_path)
                                    else:
                                        image.save(modified_file_path)

                                if GPS_found:
                                    # Send modified file
                                    with open(modified_file_path, 'rb') as modified_file:
                                        await bot.send_document(message.chat.id, modified_file, caption=f"Location information removed, secure raw image from @{message.from_user.id}")
                                        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

                                #clean up
                                os.remove(original_file_path)
                                os.remove(modified_file_path)
                                return

                else:
                    #personalized setting is activated
                    try:
                        with open(personalized_path, 'r') as file:
                            personalized = json.load(file)

                        #check if the file is not empty
                        if personalized:
                            # Flag to check if we found the user
                            found = False
                            # Iterate over each group configuration
                            for user in personalized:
                                # Decrypt the group ID and user ID, then check if personalized setting has been activated by user
                                group_chat_id_decrypted = decrypt(user['group_id'], key)
                                user_id_decrypted = decrypt(user['user_id'], key)

                                #check if group chat, user id, activation, and location is activated
                                if (group_chat_id_decrypted == group_chat_id) and (user_id_decrypted == str(message.from_user.id) and (user['activation'] == 1) and (user['location']['value'] == 1) and (user['location']['details']['document'] == 1)):
                                    found = True
                                    break

                            #if personalized setting for location is found
                            if found:
                                document = message.document
                                if document.mime_type.startswith('image/'):
                                    file_info = await bot.get_file(document.file_id)
                                    file_path = file_info.file_path
                                    file_extension = file_path.split('.')[-1]

                                    if file_extension.lower() in ['jpg', 'jpeg', 'png']:
                                        # Prepare a folder to store images
                                        image_folder = 'image'
                                        os.makedirs(image_folder, exist_ok=True)  # Ensure the directory exists

                                        # Define paths for the original and modified images
                                        original_file_path = f'{image_folder}/{document.file_id}.{file_extension}'
                                        modified_file_path = f'{image_folder}/modified_{document.file_id}.{file_extension}'

                                        # Download the image file into the image folder
                                        downloaded_file_data = await bot.download_file(file_path)
                                        with open(original_file_path, 'wb') as image_file:
                                            image_file.write(downloaded_file_data)

                                        GPS_found = False
                                        # Process the image to remove EXIF
                                        with Image.open(original_file_path) as image:
                                            exif_data = image.info.get('exif')
                                            if exif_data:
                                                exif_dict = piexif.load(exif_data)
                                                if 'GPS' in exif_dict:
                                                    GPS_found = True
                                                    del exif_dict['GPS']
                                                    new_exif = piexif.dump(exif_dict)
                                                    image.save(modified_file_path, exif=new_exif)
                                                else:
                                                    image.save(modified_file_path)
                                            else:
                                                image.save(modified_file_path)

                                        if GPS_found:
                                            # Send modified file
                                            with open(modified_file_path, 'rb') as modified_file:
                                                await bot.send_document(message.chat.id, modified_file, caption=f"RAW Image from @{message.from_user.username}")
                                                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                                                await bot.send_message(
                                                    message.from_user.id,
                                                    formatting.format_text(
                                                        formatting.munderline("-- ALERT --"),
                                                        formatting.mbold(f"Location breach in group chat has been prevented, and the location information from your RAW Image file has been removed!"),
                                                        separator="\n"  # separator separates all strings
                                                    ),
                                                    parse_mode='MarkdownV2'
                                                )

                                        #clean up
                                        os.remove(original_file_path)
                                        os.remove(modified_file_path)
                                        return
                    except IOError as e:
                        print(f"An error occurred while accessing the file: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")
            await bot.send_message(message.chat.id, "An error occurred while processing your request.", reply_to_message_id=message.message_id)
#-------------------END OF BOT DOCUMENT IMAGE HANDLER------------------#

async def start_polling(bot):
    try:
        await bot.polling()
    except aiohttp.ClientOSError as e:
        logging.error("ClientOSError encountered: %s. Restarting polling.", str(e))
        await asyncio.sleep(10)  # wait for 10 seconds before restarting
        await start_polling(bot)  # recursively restart polling

asyncio.run(start_polling(bot))
