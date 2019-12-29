import os
import time
import json
import logging
import datetime
import requests
import telegram
import platform
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from PIL import Image
from pylab import mpl
from telegram.ext import Updater
from telegram.ext import CommandHandler, MessageHandler
from telegram.ext.filters import Filters
from config import DEV_TOKEN, PUB_TOKEN, TEST_ID, HEWEATHER_KEY, MZQ_CODE, PUB_NODE, BIGJPG_KEY

location_code = MZQ_CODE
GDOU_Group = '@GDOU_Water'
BIGJPG_LINK = 'https://bigjpg.com/api/task/'

if platform.node() == PUB_NODE:
    ENV = 'PUB'
    updater = Updater(token=PUB_TOKEN, use_context=True)  # PUB
else:
    ENV = 'DEV'
    updater = Updater(token=DEV_TOKEN, use_context=True)  # DEV

dispatcher = updater.dispatcher
job = updater.job_queue

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def screen_log(message, trigger):
    if message.chat.type == 'private':
        if message.chat.username:
            print(f'{message.chat.username} triggered {trigger}')
        else:
            print(
                f'{message.chat.first_name} {message.chat.last_name} triggered {trigger}')
    else:
        if message.from_user.username:
            print(
                f'{message.from_user.username} triggered {trigger} in {message.chat.title}')
        else:
            print(
                f'{message.from_user.first_name} {message.from_user.last_name} triggered {trigger}')


def start(update, context):
    # update.message info printer
    print(update.message)
    text = 'Hi, this is bot for @GDOU_water'
    screen_log(update.message, 'start')
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def jw(update, context):
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)
    screen_log(update.message, 'jw')
    text = requests.get('http://www.gdou.edu.cn/jw/zf.html').text
    text = text.split('<div class="div">')[1].split('</A>')[:-1]
    links = []
    texts = []
    for t in text:
        t = t.split(' target="_blank">')
        texts.append(t[-1])
        links.append(t[0].split('"')[1])
    text = ['广东海洋大学教务系统: ']
    for t in range(len(texts)):
        text.append(f'[{texts[t]}]({links[t]})')
    context.bot.send_message(chat_id=update.effective_chat.id, text='\n'.join(
        text), parse_mode=telegram.ParseMode.MARKDOWN)


def yjpj(update, context):
    screen_log(update.message, 'yjpj')
    text = '计协一键评教 (Win) 下载: \nhttps://dwz.cn/KOGwwRL6'
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def make_sticker(update, context):
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)
    if str(update.message.chat_id) != TEST_ID:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='权限不足')
    else:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
        context.bot.get_file(file_id).download(file_name)
        with Image.open(file_name) as img:
            size = img.size
            output_name = ''
            if size[0] < 512:
                headers = {'X-API-KEY': BIGJPG_KEY,
                           'Content-Type': 'application/x-www-form-urlencoded'}
                params = {'style': 'art', 'noise': '0', 'x2': '2', 'file_name': file_name, "files_size": os.path.getsize(
                    file_name), "file_height": size[1], "file_width": size[0], 'input': f'https://bigjpg.burgertown.tk/{file_name}'}
                response = requests.post(
                    BIGJPG_LINK, data=f'conf={json.dumps(params)}', headers=headers).json()
                tid = response['tid']
                remaining = response['remaining_api_calls']
                text = f'使用BigJpg API\n这个月API还剩下{remaining}次'
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=text)
                time.sleep(3)
                response = requests.get(f'{BIGJPG_LINK}{tid}').json()[tid]
                while response['status'] != 'success':
                    time.sleep(3)
                    response = requests.get(f'{BIGJPG_LINK}{tid}').json()[tid]
                with open(file_name, 'wb') as f:
                    f.write(requests.get(response['url']).content)
            else:
                img = img.resize((512, int(size[1]*512/size[0])))
                if file_name.split('.')[-1] == 'png':
                    img.save(file_name)
                else:
                    output_name = file_name.split('.')
                    output_name[-1] = 'png'
                    output_name = '.'.join(output_name)
                    print(output_name)
                    img.save(output_name)

        print(f'{file_name} converted')
        if output_name:
            context.bot.send_document(
                chat_id=update.effective_chat.id, document=open(output_name, 'rb'))
            os.remove(output_name)
        else:
            context.bot.send_document(
                chat_id=update.effective_chat.id, document=open(file_name, 'rb'))
        os.remove(file_name)


def weather_now(update, context):
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)
    screen_log(update.message, 'weather_now')
    weather_type = 'now'
    link = f'https://free-api.heweather.net/s6/weather/{weather_type}'
    payload = {'location': location_code, 'key': HEWEATHER_KEY}
    result = requests.get(link, params=payload).json()['HeWeather6'][0]['now']
    text = '现在天气如下:\n体感温度: {fl}\n温度: {tmp}\n天气: {cond_txt} \n降水量: {pcpn}'.format(
        **result)
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def draw_subplot(type, times, data, today):
    plt.plot(times, data)
    plt.ylim(min(data)-2, max(data)+2)
    if type == 'tmp':
        plt.ylabel('温度 °C')
        plt.title(f'{today} 温度预报')
    else:
        plt.ylabel('降水概率 %')
        plt.title(f'{today} 降水预报')

    max_indx = np.argmax(data)
    plt.plot(max_indx, data[max_indx], 'ks')
    show_max = '['+str(times[max_indx])+' '+str(data[max_indx])+']'
    plt.annotate(show_max, xytext=(
        max_indx, data[max_indx]), xy=(max_indx, data[max_indx]))


def daily_forecast(context: telegram.ext.CallbackContext):
    context.bot.send_chat_action(
        chat_id=GDOU_Group, action=telegram.ChatAction.TYPING)
    weather_type = 'forecast'
    link = f'https://free-api.heweather.net/s6/weather/{weather_type}'
    payload = {'location': location_code, 'key': HEWEATHER_KEY}
    result = requests.get(link, params=payload).json()
    days = result['HeWeather6'][0]['daily_forecast']
    today = str(datetime.date.today())
    for day in days:
        if day['date'] == today:
            t = day
    text = '*{date}*\n天气预告如下\n今日温度 {tmp_min}-{tmp_max}\n降水概率 {pop}%\n白天天气 {cond_txt_d} \n晚间天气 {cond_txt_n}\n日出时间 {sr}\n日落时间 {ss}\n*Have A Nice Day*'.format(
        **t)
    # context.bot.send_message(chat_id=TEST_ID,
    #                          text=text, parse_mode=telegram.ParseMode.MARKDOWN)
    context.bot.send_message(chat_id=GDOU_Group,
                             text=text, parse_mode=telegram.ParseMode.MARKDOWN)
    weather_type = 'hourly'
    link = f'https://free-api.heweather.net/s6/weather/{weather_type}'
    result = requests.get(link, params=payload).json()
    datas = result['HeWeather6'][0]['hourly']
    tmps, pops, times = [], [], []
    for data in datas:
        times.append(data['time'].split(' ')[1])
        tmps.append(int(data['tmp']))
        pops.append(int(data['pop']))

    plt.rcParams['font.family'] = 'Sarasa Mono T SC'  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    plt.subplots_adjust(hspace=0.2)

    ax1 = plt.subplot(211)
    draw_subplot('tmp', times, tmps, today)
    plt.subplot(212)
    draw_subplot('pop', times, pops, today)
    plt.xlabel('时间')
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.savefig(f'{today}.png')
    plt.close()

    context.bot.send_photo(chat_id=GDOU_Group,
                           photo=open(f'{today}.png', 'rb'))
    # context.bot.send_photo(chat_id=TEST_ID,
    #                        photo=open(f'{today}.png', 'rb'))
    print(f'{datetime.date.today()} forecast pushed')


def welcome_new_member(update, context):
    for member in update.message.new_chat_members:
        if member.username:
            update.message.reply_text(f'欢迎 {member.username}')
        else:
            update.message.reply_text(
                f'欢迎 {member.first_name} {member.last_name}')


def get_sticker_id(update, context):
    context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=telegram.ChatAction.TYPING)
    if str(update.message.chat_id) != TEST_ID:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text='权限不足')
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text=update.message.sticker.file_id)


def tql(update, context):
    context.bot.send_sticker(
        chat_id=update.effective_chat.id, sticker='CAADBQADBQAD6EXBEZeMDoztApb_FgQ')


def test():
    text = '111'
    telegram.Bot(BOT_TOKEN).send_sticker(chat_id=TEST_ID,
                                         sticker='CAADBQADBQAD6EXBEZeMDoztApb_FgQ')


job.run_daily(daily_forecast, time=datetime.time(0, 0, 0))
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('jw', jw))
dispatcher.add_handler(CommandHandler('yjpj', yjpj))
dispatcher.add_handler(CommandHandler('weather_now', weather_now))
dispatcher.add_handler(CommandHandler('tql', tql))
dispatcher.add_handler(MessageHandler(Filters.document.image, make_sticker))
dispatcher.add_handler(MessageHandler(
    Filters.status_update.new_chat_members, welcome_new_member))
dispatcher.add_handler(MessageHandler(Filters.sticker, get_sticker_id))
# test()
updater.start_polling()
