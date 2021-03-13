#! /home/nathan/.virtualenvs/rollem/bin/python
import sys
import time
import re
import random
import traceback
import unicodedata
import logging
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from codecs import encode,decode
from datetime import datetime
from ast import literal_eval

ladder = {
    8  : 'Legendary',
    7  : 'Epic',
    6  : 'Fantastic',
    5  : 'Superb',
    4  : 'Great',
    3  : 'Good',
    2  : 'Fair',
    1  : 'Average',
    0  : 'Mediocre',
    -1 : 'Poor',
    -2 : 'Terrible'
}

def get_ladder(result):
    if result > 8:
        return 'Beyond Legendary'
    elif result < -2:
        return 'Terrible'
    else:
        return ladder[result]

fate_options = { 
        -1 : '[-]', 
        0  : '[  ]', 
        1  : '[+]' 
    }

def rf(update: Update, context: CallbackContext):
    if len(context.args) > 0:
        context.args[0] = '4df+' + str(context.args[0])
    else:
        context.args = ['4df']
    process(update, context)

def process(update: Update, context: CallbackContext):
    username = update.message.from_user.username if update.message.from_user.username else update.message.from_user.first_name
    equation = context.args[0].strip() if len(context.args) > 0 else False
    equation_list = re.findall(r'(\w+!?>?\d*)([+*/()-]?)', equation)
    comment = ' ' + ' '.join(context.args[1:]) if len(context.args) > 1 else ''
    space = ''
    dice_num = None
    is_fate = False
    use_ladder = False
    result = {
        'visual': [],
        'equation': [],
        'total': ''
    }

    try:
        for pair in equation_list:
            logging.debug(f"pair: {pair}")
            pair = [i for i in pair if i]
            for item in pair:
                logging.debug(f"item: {item}")
                if item and len(item) > 1 and any(d in item for d in ['d', 'D']):
                    dice = re.search(r'(\d*)d([0-9f]+)([!hl])?', item.lower())
                    dice_num = int(dice.group(1)) if dice.group(1) else 1
                    if dice_num > 1000:
                        raise Exception('Maximum number of rollable dice is 1000')
                    sides = dice.group(2)
                    space = ' '
                    result['visual'].append(space + '(')
                    result['equation'].append('(')
                    fate_dice = ''
                    current_die_results = ''
                    current_visual_results = ''
                    plus = ''
                    explode = False
                    highest = False
                    lowest = False
                    if dice.group(3) and dice.group(3)[0] == '!' and int(dice.group(2)) > 1:
                        explode = True 
                    elif dice.group(3) and dice.group(3)[0] in ['h','H']:
                        highest = True
                    elif dice.group(3) and dice.group(3)[0] in ['l','L']:
                        lowest = True

                    while dice_num > 0:
                        random_start_num = 1
                        if sides in ['f','F']:
                            is_fate = True
                            use_ladder = True
                            sides = 1
                            random_start_num = -1
                        else:
                            sides = int(sides)

                        last_roll = random.randint(random_start_num, sides)
                        if is_fate:
                            fate_dice += fate_options[last_roll] + ' '

                        if (highest or lowest) and current_die_results:
                            #print(current_die_results)
                            if highest:
                                if last_roll > int(current_die_results):
                                    current_die_results = str(last_roll)
                                current_visual_results += plus + str(last_roll)
                            else: #lowest
                                if last_roll < int(current_die_results):
                                    current_die_results = str(last_roll)
                                current_visual_results += plus + str(last_roll)

                        else:
                            current_die_results += plus + str(last_roll)
                            current_visual_results += plus + str(last_roll)

                        if not (explode and last_roll == sides):
                            dice_num -= 1

                        if len(plus) == 0: 
                            # Adds all results to result unless it is the first one
                            plus = ' + '

                    if is_fate:
                        is_fate = False
                        result['visual'].append(' ' + fate_dice)
                    else:
                        result['visual'].append(current_visual_results)
                    result['equation'].append(current_die_results)
                    result['visual'].append(')')
                    result['equation'].append(')')
                    if highest or lowest:
                        result['visual'].append(dice.group(3)[0])
                else:
                    if item and (item in ['+','-','/','*',')','('] or int(item)):
                        result['visual'].append(' ')
                        result['visual'].append(item)
                        result['equation'].append(item)

        result['total'] = str(''.join(result['equation'])).replace(" ","")
        if bool(re.match('^[0-9+*/ ()-]+$', result['total'])):
            result['total'] = eval(result['total'])
        else:
            raise Exception('Request was not a valid equation!')

        logging.debug(' '.join(context.args) + ' = ' + ''.join(result['equation']) + ' = ' + str(result['total']))

        if use_ladder:
            # Set if final result is positive or negative
            sign = '+' if result['total'] > -1 else ''
            ladder_result = get_ladder(result['total'])
            result['total'] = sign + str(result['total']) + ' ' + ladder_result

        # Only show part of visual equation if bigger than 300 characters
        result['visual'] = ''.join(result['visual'])
        if len(result['visual']) > 275:
            result['visual'] = result['visual'][0:275] + ' . . . )'

        response = (f'@{username} rolled<b>{comment}</b>:\r\n {result["visual"]} =\r\n<b>{str(result["total"])}</b>')
        error = ''

    except Exception as e:
        response = f'@{username}: <b>Invalid equation!</b>\r\n'
        if dice_num and dice_num > 1000:
            response += str(e) + '.\r\n'
        response += ('Please use <a href="https://en.wikipedia.org/wiki/Dice_notation">dice notation</a>.\r\n' +
                'For example: <code>3d6</code>, or <code>1d20+5</code>, or <code>d12</code>\r\n\r\n' +
                'For more information, type <code>/help</code>'
            )
        error = traceback.format_exc().replace('\r', '').replace('\n', '; ')
        logging.debug('EQUATION: ' + str(equation) + ' | RESPONSE: ' + response + ' | ERROR: ' + str(error))

        logging.error(error + '\r\nRESPONSE: ' + response )

    context.bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=ParseMode.HTML)


def help(update: Update, context: CallbackContext):
    help_file = open('help.html', 'r')
    response = (help_file.read())
    help_file.close()
    print('help')
    job = context.job
    context.bot.send_message(chat_id=update.message.chat_id, text=response, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    
TOKEN = sys.argv[1]

logging.basicConfig(
        filename='roll.log', 
        encoding='utf-8', 
        format='====> %(asctime)s | %(name)s | %(levelname)s | %(message)s',
        level=logging.INFO
    )
logging.basicConfig(
        format='====> %(asctime)s | %(name)s | %(levelname)s | %(message)s', 
        hamdlers = [logging.StreamHandler(sys.stdout)], 
        level=logging.DEBUG
    )

updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

roll_handler = CommandHandler(['roll','r'], process, pass_args=True)
dispatcher.add_handler(roll_handler)

roll_handler = CommandHandler('rf', rf, pass_args=True)
dispatcher.add_handler(roll_handler)

help_handler = CommandHandler('help', help)
dispatcher.add_handler(help_handler)

updater.start_polling()
