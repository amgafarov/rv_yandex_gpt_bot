import asyncio
import io
import os
from telegram_secure import __token__ as token
from telegram_secure import __admins__ as admins
from yandex_services.yandex_gpt_request import get_response, admin_get_temp, admin_set_temp
from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode, content_type
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
import datetime
from functions import get_secure, get_users, read_text_file, add_user, create_image, create_m_image, \
    remove_image_background, image_watermark, convert_heic_to_jpg, video_watermark, text_to_speech

dp = Dispatcher()
bot = Bot(token=token, parse_mode=ParseMode.HTML)
r = Router()

logging.basicConfig(level=logging.INFO, filename="logs/py_log.log")

last_textes = dict()
__file_path__ = 'files/'

text_file_types = ('.doc', '.docx', '.txt', '.rtf', '.xlsx', '.pdf')

telegram_promt = ('Напиши простой и понятный пост в Telegram из этого сообщения. '
                  'Пусть его длина не превышает трех или четырех предложений. Он должен легко читаться.'
                  ' НЕ ИСПОЛЬЗУЙ страдательный залог В твоем ответе должна '
                  'содержаться только написанная новость, НИКАКИХ ПРИМЕЧАНИЙ ИЛИ СПРАВОК БЫТЬ НЕ ДОЛЖНО!')


# TODO : AUDIO — TEXT
# TODO : VIDEO — AUDIO — TEXT

async def send_rewrite(message: types.Message, response, markups=True):
    if 'result' in response:
        answer = str(response['result']['alternatives'][0]['message']['text'])
        logging.info(f'REWRITE RESULT: {message.chat.id} ({message.from_user.first_name} '
                     f'{message.from_user.last_name}) : {response}')

        if markups:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text='Новый вариант', callback_data='new_variant'),
                types.InlineKeyboardButton(text='Пост в Telegram', callback_data='telegram-post')
            )
            builder.row(
                types.InlineKeyboardButton(text='SEO: Заголовок и описание', callback_data='seo'),
                types.InlineKeyboardButton(text='Заголовки', callback_data='titles')
            )
            answer = answer.replace('*', '')
            answer = answer.replace('Заголовок:', '')
            answer = answer.replace('Лид:', '')
            answer = answer.replace('Текст новости:', '')
            answer = answer.replace('\n ', '\n')
            answer = answer.replace(' %', '%')
            answer = answer.replace('ё', 'е')
            answer = answer.replace('Ё', 'Е')
            await message.reply(answer, reply_markup=builder.as_markup())
        else:
            await message.reply(answer)
    elif 'error' in response:
        logging.error(f'REWRITE: {message.chat.id}\nmessage: {str(message.text)}\n'
                      f'error status: {response}')

        answer = 'При подготовке ответа я столкнулся со следующей ошибкой:\n\n'
        if str(response['error']['message']).__contains__('number of input tokens must be'):
            answer += 'Для обработки вы передали мне слишком большой текст'
        elif str(response['error']['message']).__contains__('An answer to a given topic cannot be generated'):
            answer += 'Вы передали мне для обработки неэтичный запрос'
        else:
            answer += str(response['error']['message'])

        await message.reply(answer)


async def send_telegram_post(message: types.Message, text):
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text='Переписать пост', callback_data='new_tg_post'),
    )
    await message.reply(text=text, reply_markup=builder.as_markup())


async def send_not_secure_message(message: types.Message):
    text = (f'{message.from_user.first_name}, к сожалению, <b>вам запрещено</b> пользоваться моим функционалом\n\n'
            'Если вы уверены, что доступ вам разрешен, то выполнитле 3 простых шага:\n'
            '1. Запустите команду /id\n'
            '2. Нажмите на полученные цифры - они скопируются\n'
            '3. Отправьте ваш уникальный <i>ID</i> администратору')

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text='Администратор', url='tg://user?id=421349553'),
    )

    await message.reply(text, reply_markup=builder.as_markup())


@r.message(Command('start', 'id'))
async def start_function(message: types.Message) -> None:
    logging.info(f'{datetime.datetime.now()} ID {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {message.text}')

    text = f'{message.from_user.first_name}, ваш уникальный ID: <b><code>{message.chat.id}</code></b>'
    await message.answer(text)


@r.message(Command('s', 'short'))
async def make_short_text(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    short_promt = ('Ты профессиональный журналист. '
                   'Максимально сократи эту новость до 2-4 предложений с обязательным сохранением сути новости.')

    assist_message = await message.answer('Готовлю сокращение новости')

    text = str(message.text)
    if text.startswith('/short'):
        text = text.replace('/short', '')
    else:
        text = text.replace('/s', '')

    if len(text) == 0 or text is None:
        await message.reply('Вы не ввели текст!')
        await bot.delete_message(message.chat.id, assist_message.message_id)
        return

    response = get_response(admin_promt=short_promt, user_promt=text).json()
    if 'error' in response:
        answer = str(response['error']['message'])
        answer = answer.replace('An answer to a given topic cannot be generated',
                                'Вы передали неэтичный запрос')
    else:
        answer = str(response['result']['alternatives'][0]['message']['text'])

    answer = answer.replace('*', '')
    await bot.edit_message_text(text=answer, chat_id=assist_message.chat.id, message_id=assist_message.message_id)


@r.message(Command('help'))
async def help_function(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    logging.info(f'{datetime.datetime.now()} HELP {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {message.text}')

    with open('help.txt') as file:
        text = file.read()
    await message.answer(text)


@r.message(Command('text'))
async def pdf_to_text(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    logging.info(f'{datetime.datetime.now()} PDF TO TEXT {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name})')

    if not message.document:
        await message.reply('Вы не отправили документ')
        return

    if not str(message.document.file_name).lower().endswith('.pdf'):
        await message.reply('Отправьте мне PDF-файл')
        return

    assist_message = await message.answer(text='Перевожу PDF-файл в текстовый')
    pdf_file = f'{__file_path__}{str(message.from_user.id)}-{message.document.file_name}'
    temp = io.BytesIO()
    await bot.download(message.document.file_id, temp)

    with open(pdf_file, 'wb') as pdf:
        pdf.write(temp.read())

    text = read_text_file(pdf_file)

    if text is None or text.strip() == '':
        text = read_text_file(pdf_file)

    file = message.document.file_name.lower().split('.pdf')[0] + '.txt'
    with open(file, 'w+') as f:
        f.write(text)
    await bot.delete_message(message.chat.id, assist_message.message_id)
    await message.reply_document(types.FSInputFile(file))
    os.remove(file)


@r.message(Command('status'))
async def get_status(message: types.Message) -> None:
    logging.info(f'{datetime.datetime.now()} STATUS {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {message.text}')
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    if str(message.chat.id) in admins:
        text = f'{message.from_user.first_name}, вы <b>АДМИНИСТРАТОР</b>'
    else:
        text = f'{message.from_user.first_name}, вы <b>ПОЛЬЗОВАТЕЛЬ</b>'

    await message.reply(text, parse_mode='html')


@r.message(Command('message'))
async def get_message_code(message: types.Message) -> None:
    logging.info(f'{datetime.datetime.now()} MESSAGE {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {message.text}')
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    if str(message.chat.id) in admins:
        try:
            await message.answer(str(message))
        except Exception as e:
            logging.error(
                f'{datetime.datetime.now()} MESSAGE SEND ERROR {message.chat.id} ({message.from_user.first_name} '
                f'{message.from_user.last_name}) : {message}')
            await message.reply('Не получилось выполнить запрос')
            logging.error(e.with_traceback)


@r.message(Command('add_user'))
async def add_user_to_list(message: types.Message) -> None:
    logging.info(f'{datetime.datetime.now()} ADD USER COMMAND {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {message.text}')
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    if str(message.chat.id) in admins:
        elements = str(message.text).split(' ')
        elements = elements[1:]

        if len(elements) == 0:
            await message.reply('Вы не ввели ID пользователя')
        else:
            allowed_users = get_users()
            for user in elements:
                if user not in allowed_users:
                    add_user(user)
                    try:
                        await message.answer(chat_id=str(user),
                                             text='Теперь вам <b>разрешено</b> пользоваться моими функциями',
                                             parse_mode='html')
                    except:
                        pass
            await message.answer('Пользователи добавлены')


@r.message(Command('delete_user'))
async def delete_user_from_list(message: types.Message) -> None:
    logging.info(f'{datetime.datetime.now()} DELETE USER COMMAND {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {str(message.text)}')
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    if str(message.chat.id) in admins:
        elements = str(message.text).split(' ')
        elements = elements[1:]

        if len(elements) == 0:
            await message.reply('Вы не ввели ID пользователя')
        else:
            allowed_users = get_users()
            for user in elements:
                if user in allowed_users:
                    allowed_users.remove(user)
                    try:
                        del last_textes[str(user)]
                    except:
                        logging.error(f'DELETE LAST TEXT OF {user}')
                    try:
                        await message.answer(chat_is=str(user),
                                             text='Теперь вам <b>запрещено</b> пользоваться моими функциями',
                                             parse_mode='html')
                    except:
                        pass
            f = open('accepted_users', 'w')
            f.write('')
            f.close()
            for user in allowed_users:
                add_user(user)
            await message.answer(text='Пользователи удалены')


@r.message(Command('is_user'))
async def is_user_command(message: types.Message) -> None:
    logging.info(f'{datetime.datetime.now()} IS USER COMMAND {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {message.text}')
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    if str(message.chat.id) in admins:
        elements = str(message.text).split(' ')
        elements = elements[1:]
        if len(elements) == 0:
            await message.reply(text='Вы не ввели ID пользователя')
        else:
            allowed_users = get_users()
            for user in elements:
                if user in allowed_users:
                    await message.answer(text=f'ID <code>{user}</code> <b>зарегистрирован</b>',
                                         parse_mode='html')
                else:
                    await message.answer(text=f'ID <code>{user}</code> <b>НЕ зарегистрирован</b>',
                                         parse_mode='html')


@r.message(Command('generate'))
async def generate_using_promt(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    logging.info(f'{datetime.datetime.now()} GENERATE ACTION {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {message.text}')

    if '-promt' not in str(message.text) or '-text' not in str(message.text):
        await message.reply(text='Вы не ввели задание или текст.\n'
                                 'Для этого используйте теги <code>-promt</code> для указания задания\n'
                                 'и <code>-text</code> для указания текста\n\n'
                                 'Подробнее — /help', parse_mode='html')
        return

    if str(message.text).count('-text ') > 1 or str(message.text).count('-promt ') > 1:
        await message.reply(text='Вы ввели слишком много параметров.\n'
                                 'Количество тегов <code>-promt</code> и <code>-text</code> '
                                 'должно быть равно единице.\n\n'
                                 'Подробнее — /help', parse_mode='html')
        return

    assist_message = await message.reply(text='Выполняю задание. Пожалуйста, подождите...')
    full_text = message.text.split('/generate')[1].strip()

    if full_text.startswith('-promt'):
        parts = full_text.split('-text')
        text = parts[1].strip()
        parts = parts[0].split('-promt')
        promt = parts[1].strip()
    else:
        parts = full_text.split('-promt')
        promt = parts[1].strip()
        parts = parts[0].split('-text')
        text = parts[1].strip()

    if len(text) == 0 or len(promt) == 0 or text is None or promt is None:
        await message.answer(text='Вы не ввели задание или текст.\n'
                                  'Для этого используйте теги <code>-promt</code> для указания задания\n'
                                  'и <code>-text</code> для указания текста\n\n'
                                  'Подробнее — /help', parse_mode='html')
        return

    response = get_response(user_promt=text, admin_promt=promt).json()
    await send_rewrite(message=message, response=response)
    await bot.delete_message(message.chat.id, assist_message.message_id)


@r.message(Command('admin_help'))
async def admin_help_command(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    if str(message.chat.id) not in admins:
        await message.reply('Команда доступна только администраторам. Узнать свой статус — /status')
        return

    logging.info(f'{datetime.datetime.now()} ADMIN HELP {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name})')

    text = (f'<b>Команды администратора:</b>\n'
            f'1. <code>/temp</code> [0-100] — Устанавливает температуру нейросети\n'
            f'2. <code>/add_user</code> [ID list] — Разрешает людям по ID пользоваться ботом\n'
            f'3. <code>/delete_user</code> [ID list] — Запрещает людям по ID пользоваться ботом\n'
            f'4. <code>/is_user</code> [ID list] — Проверяет, разрешено ли людям по ID пользоваться ботом ')
    await message.answer(text=text)


@r.message(Command('temp'))
async def set_new_temp(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    if not str(message.chat.id) in admins:
        await message.reply('Эта функция доступна только администраторам')
        return

    parts = str(message.text).split(' ')
    if len(parts) == 1:
        await message.answer(f'Текущая температура: {admin_get_temp()}')
        logging.info(f'{datetime.datetime.now()} TEMPERATURE STATUS {message.chat.id} ({message.from_user.first_name} '
                     f'{message.from_user.last_name}) : {admin_get_temp()}')
        return

    try:
        temp = int(parts[1]) / 100
    except:
        await message.reply('В значении температуры не целое число от 0 до 100')
        return

    if temp < 0 or temp > 1:
        await message.reply('В значении температуры не целое число от 0 до 100')
        return

    logging.info(f'{datetime.datetime.now()} NEW TEMPERATURE {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {temp}')
    admin_set_temp(temp)
    await message.reply(f'Температура установлена на значение: {temp}')


@r.message(Command('post'))
async def make_telegram_post(message: types.Message):
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    assist_message = await message.answer('Готовлю пост в Telegram')

    text = str(message.text).replace('/post', '')
    text = text.replace('💻Читайте подробнее на realnoevremya.ru', '')

    if len(text) == 0 or text is None:
        await message.reply('Вы не ввели текст!')
        await bot.delete_message(message.chat.id, assist_message.message_id)
        return

    response = get_response(admin_promt=telegram_promt, user_promt=text).json()
    response = get_response(user_promt=response['result']['alternatives'][0]['message']['text'])
    if 'error' in response.json():
        answer = str(response.json()['error']['message'])
        answer = answer.replace('An answer to a given topic cannot be generated',
                                'Вы передали неэтичный запрос')
    else:
        answer = str(response.json()['result']['alternatives'][0]['message']['text'])

    answer = answer.replace('*', '')
    await send_telegram_post(message, answer)
    await bot.delete_message(message.chat.id, assist_message.message_id)


@r.message(Command('img'))
async def create_image_func(message: types.Message):
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    text = message.text[5:]
    logging.info(f'{datetime.datetime.now()} TEXT IMAGE FROM {message.from_user.full_name} TEXT : {text.strip()}')
    if len(text) == 0:
        await message.reply('Вы не ввели текст')
        return

    assist_message = await message.reply('Создаю изображение')
    image = create_image(text, str(message.chat.id))
    try:
        await message.reply_photo(types.FSInputFile(image))
        await bot.delete_message(message.chat.id, assist_message.message_id)
    except Exception as e:
        logging.error(f'{datetime.datetime.now()} ERROR : {e.with_traceback}')
    finally:
        if os.path.exists(image):
            os.remove(image)


@r.message(Command('imgm'))
async def create_image_func(message: types.Message):
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    text = message.text[6:]
    text = text.strip()
    logging.info(f'{datetime.datetime.now()} TEXT IMAGE FROM {message.from_user.full_name} TEXT : {text.strip()}')
    if len(text) == 0:
        await message.reply('Вы не ввели текст')
        return

    assist_message = await message.reply('Создаю изображение')
    image = create_m_image(text.strip(), str(message.chat.id))
    try:
        await message.reply_photo(types.FSInputFile(image))
        await bot.delete_message(message.chat.id, assist_message.message_id)
    except Exception as e:
        logging.error(f'{datetime.datetime.now()} ERROR : {e.with_traceback}')
    finally:
        if os.path.exists(image):
            os.remove(image)


@r.message(Command('wm', 'watermark'))
async def make_watermark(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    if not message.photo and not message.document and not message.video:
        await message.answer('Вы не отправили мне изображение или видео')
        return

    if message.document:
        part = message.document.file_name.split('.')[-1].lower()
        if part not in ['png', 'jpg', 'jpeg', 'heic']:
            await message.answer('Вы не отправили мне изображение\n\nЕсли вы хотите отправить видео, '
                                 'то отправляйте его в сжатом виде')
            return

    assist_message = await message.answer('Наношу водяной знак')

    logging.info(f'{datetime.datetime.now()} PHOTO FROM {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name})')

    if message.photo:
        src = f'{__file_path__}{str(message.from_user.id)}-{message.photo[0].file_id}.jpg'
        temp = io.BytesIO()
        await bot.download(message.photo[-1], temp)
    elif message.video:

        if message.video.duration > 180:
            await message.reply('Видео длится более 3 минут. Сократите его')
            return
        if message.video.file_size > 30 * 1024 * 1024:
            await message.reply('Видео весит больше 200 МБайт. Сожмите его')
            return

        src = (f'{__file_path__}{str(message.from_user.id)}-'
               f'{message.video.file_id}.{message.video.file_name.split(".")[-1]}')
        temp = io.BytesIO()
        await bot.download(message.video, temp)
    else:
        src = f'{__file_path__}{str(message.from_user.id)}-{message.document.file_name}'
        temp = io.BytesIO()
        await bot.download(message.document.file_id, temp)

    with open(src, 'wb') as file:
        file.write(temp.read())

    if src.lower().endswith('.heic'):
        src = convert_heic_to_jpg(src)

    if message.video:
        file = video_watermark(src)
    else:
        file = image_watermark(src)

    await bot.delete_message(assist_message.chat.id, assist_message.message_id)
    await message.reply_document(types.FSInputFile(file))

    if os.path.exists(src):
        os.remove(src)
    if os.path.exists(file):
        os.remove(file)


@r.message(Command('bg'))
async def remove_bg_func(message: types.Message):
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    logging.info(f'{datetime.datetime.now()} REMOVE BG FROM {message.from_user.full_name}')

    if not message.document and not message.photo:
        await message.reply('Отправьте мне изображение')
        return

    if message.document:
        file_type = str(message.document.file_name).upper().split('.')[-1]
        if not (file_type.lower() == 'png' or file_type.lower() == 'jpg' or file_type.lower() == 'jpeg'
                or file_type.lower() == 'heic'):
            await message.reply('Формат файла должен быть png, jpg, heic')
            return

    assist_message = await message.reply('Начинаю удалять фон. Это займет некоторое время...')
    temp = io.BytesIO()

    if message.document:
        await bot.download(message.document.file_id, temp)
        src = f'image_creator/{message.from_user.id}-image-to-remove-{message.document.file_name}'
    if message.photo:
        await bot.download(message.photo[-1].file_id, temp)
        src = f'image_creator/{message.from_user.id}-image-to-remove-{message.photo[-1].file_id}.png'

    with open(src, 'wb') as file:
        file.write(temp.read())

    if src.lower().endswith('.heic'):
        src = convert_heic_to_jpg(src)

    result = remove_image_background(src)
    try:
        await message.reply_document(types.FSInputFile(result))
        await bot.delete_message(message.chat.id, assist_message.message_id)
    except Exception as e:
        logging.error(f'{datetime.datetime.now()} ERROR : {e.with_traceback}')
    finally:
        if os.path.exists(file.name):
            os.remove(file.name)
        if os.path.exists(result):
            os.remove(result)


@r.message(Command('tts'))
async def synthesis_audio_from_text(message: types.Message):
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    if message.document:
        logging.info(
            f'{datetime.datetime.now()} DOCUMENT FOR TTS FROM {message.chat.id} ({message.from_user.first_name} '
            f'{message.from_user.last_name}) : {message.document.file_name}')

        readable_filetype = message.document.file_name.endswith(text_file_types)

        if readable_filetype:
            src = f'{__file_path__}{str(message.from_user.id)}-{message.document.file_name}'
            temp = io.BytesIO()
            await bot.download(message.document.file_id, temp)

            with open(src, 'wb') as file:
                file.write(temp.read())
            try:
                text = read_text_file(src)
            except Exception as e:
                logging.error(e.with_traceback)
                await message.answer('К сожалению, я не смог открыть данный файл. Попробуйте еще раз '
                                     'или переместите текст в файл .txt')
                return
            finally:
                if os.path.exists(src):
                    logging.info(
                        f'{datetime.datetime.now()}:DELETE FILE FROM ({message.from_user.full_name}) FILE: {src}')
                    os.remove(src)
        else:
            await message.reply('Вы прислали мне файл в неверном формате')
    else:
        logging.info(
            f'{datetime.datetime.now()} TEXT FOR TTS FROM {message.chat.id} ({message.from_user.first_name} '
            f'{message.from_user.last_name}) : {message.text}')
        text = message.text.replace('/tts', '').strip()
        if text == '' or text is None:
            await message.reply('Вы не прислали текст')
            return

    assist_message = await message.reply('Начинаю синтезировать аудио')
    file = text_to_speech(text, str(message.from_user.id))

    await message.reply_document(types.FSInputFile(file))
    await message.reply_voice(types.FSInputFile(file))
    await bot.delete_message(assist_message.chat.id, assist_message.message_id)
    if os.path.exists(file):
        os.remove(file)


@r.message(Command('log', 'logs'))
async def send_update_logs(message: types.Message):
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    if str(message.chat.id) not in admins:
        await message.reply('Вы не администратов')
        return

    users = get_users()
    text = '<b>Нововведения в боте:</b>\n\n'.upper()
    with open('last_update.txt', 'r') as file:
        text += file.read()
    for user in users:
        try:
            await bot.send_message(user, text=text)
        except:
            next()


# ===================================================================


# TODO : .ppt .doc reader
@r.message(lambda message: message.document and not message.animation)
async def document_parser(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    logging.info(f'{datetime.datetime.now()} DOCUMENT FROM {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {message.document.file_name}')

    readable_filetype = message.document.file_name.endswith(text_file_types)

    if readable_filetype:
        file_type = str(message.document.file_name).upper().split('.')[-1]
        assist_message = await message.answer(text=f'Обрабатываю содержание '
                                                   f'{file_type}-файла')
        src = f'{__file_path__}{str(message.from_user.id)}-{message.document.file_name}'
        temp = io.BytesIO()
        await bot.download(message.document.file_id, temp)

        with open(src, 'wb') as file:
            file.write(temp.read())

        text = ''
        if message.caption is not None:
            text = message.caption

        # Получаем текст из файла в зависимости от его формата
        try:
            text += read_text_file(src)
        except Exception as e:
            logging.error(e.with_traceback)
            await message.answer('К сожалению, я не смог открыть данный файл. Попробуйте еще раз '
                                 'или переместите текст в файл .txt')
            return
        finally:
            if os.path.exists(src):
                logging.info(f'{datetime.datetime.now()}:DELETE FILE FROM ({message.from_user.full_name}) FILE: {src}')
                os.remove(src)

        # If empty text
        if len(text) == 0:
            await message.answer('Не удалось считать текст из файла и его описания. Пожалуйста, попробуйте '
                                 'отправить его еще раз или скопируйте текст из файла и '
                                 'отправьте его простым сообщением')
            return

        # Получаем рерайт текста из файла
        response = get_response(user_promt=text).json()
        await send_rewrite(message, response)
        await bot.delete_message(message.chat.id, assist_message.message_id)

    # Обработка файла pdf
    # elif str(message.document.file_name).lower().endswith('.pdf'):
    #    assist_message = await message.answer(text='Обрабатываю содержание PDF-файла')
    #    pdf_file = f'{__file_path__}{str(message.from_user.id)}-{message.document.file_name}'
    #    temp = io.BytesIO()
    #    await bot.download(message.document.file_id, temp)

    #    with open(pdf_file, 'wb') as pdf:
    #        pdf.write(temp.read())

    #    text = read_pdf_file(pdf_file)

    #    if text is None or text.strip() == '':
    #        text = text_from_pdf_scan(pdf_file)

    #    temp_file = message.document.file_name.lower().split('.pdf')[0] + '.txt'
    #    with open(temp_file, 'w+') as f:
    #        f.write(text)
    #    readed_file = await message.reply_document(types.FSInputFile(temp_file))
    #    os.remove(temp_file)

    # Получаем рерайт текста из файла
    #    response = get_response(user_promt=text).json()
    #    await send_rewrite(readed_file, response)
    #    await bot.delete_message(message.chat.id, assist_message.message_id)

    elif str(message.document.file_name).lower().endswith('.heic'):
        assist_message = await message.reply('Конвертирую .heic в .jpg')
        src = f'{__file_path__}{str(message.from_user.id)}-{message.document.file_name}'
        temp = io.BytesIO()
        await bot.download(message.document.file_id, temp)

        with open(src, 'wb') as file:
            file.write(temp.read())

        file = convert_heic_to_jpg(src)
        await message.reply_document(types.FSInputFile(file))
        await bot.delete_message(assist_message.chat.id, assist_message.message_id)

        if os.path.exists(src):
            os.remove(src)
        if os.path.exists(file):
            os.remove(file)

    elif message.caption is not None:
        assist_message = await message.answer('Я не умею работать с файлами такого типа, поэтому '
                                              'сделаю рерайт только по его описанию',
                                              reply_to_message_id=message.message_id)
        text = message.caption
        response = get_response(user_promt=text).json()
        await send_rewrite(message, response)
        await bot.delete_message(message.chat.id, assist_message.message_id)
    else:
        await message.reply('Я не умею работать с изображениями, видео или аудиофайлами\n\n'
                            'Подробнее о функционале - /help')


@r.message(lambda message: message.photo or message.animation or message.video)
async def files_with_caption(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return

    if message.caption is None:
        await message.reply('Я не умею работать с изображениями, видео или аудиофайлами\n\n'
                            'Подробнее о функционале - /help')
        logging.error(
            f'{datetime.datetime.now()} INCORRECT DOCUMENT FROM {message.chat.id} ({message.from_user.first_name} '
            f'{message.from_user.last_name})')
        return

    logging.info(f'{datetime.datetime.now()} REWRITE FROM REPOST {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {str(message.caption)}')
    assist_message = await message.answer(text='Готовлю рерайт ТЕКСТА в этом сообщении\n\n'
                                               'Содержание видео, фотографий и других файлов я <b>НЕ ОБРАБАТЫВАЮ</b>',
                                          parse_mode='html')

    if message.forward_origin is not None and message.forward_origin.chat.title is not None:
        text = f'"{message.forward_origin.chat.title}"' + ' сообщает:\n'
    else:
        text = ''

    text += message.caption
    response = get_response(user_promt=text).json()
    await send_rewrite(message, response)
    await bot.delete_message(message.chat.id, assist_message.message_id)


@r.message(lambda message: message.voice or message.audio)
async def transcribe_audio(message: types.Message):
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    if message.audo:
        file_id = message.audio.file_id
    else:
        file_id = message.voice.file_id

    temp = io.BytesIO()
    await bot.download(file_id, temp)


@r.message(lambda message: message.text)
async def rewrite_text(message: types.Message) -> None:
    if not get_secure(message.chat.id):
        await send_not_secure_message(message)
        return
    logging.info(f'{datetime.datetime.now()} REWRITE {message.chat.id} ({message.from_user.first_name} '
                 f'{message.from_user.last_name}) : {str(message.text)}')

    assist_message = await message.answer(text='Готовлю рерайт')

    # Обрабатываем ссылки
    link_message = None

    text = ''
    try:
        text = f'"{message.forward_origin.chat.title}"' + ' сообщает:\n'
    except:
        pass

    # Обрабатываем текст
    text += message.text
    response = get_response(user_promt=text).json()
    await send_rewrite(message, response)
    await bot.delete_message(message.chat.id, assist_message.message_id)
    if link_message is not None:
        await bot.delete_message(message.chat.id, link_message.message_id)


@r.callback_query()
async def callback_btn_handler(callback: types.CallbackQuery) -> None:
    if not get_secure(callback.message.chat.id):
        await send_not_secure_message(callback.message)
        return

    logging.info(f'{datetime.datetime.now()} REWRITE {callback.message.chat.id} ({callback.from_user.first_name} '
                 f'{callback.from_user.last_name}) : '
                 f'{str(callback.message.text)}')
    if callback.data == 'new_variant':
        if callback.message.reply_to_message.content_type == content_type.ContentType.TEXT:
            try:
                if str(callback.message.reply_to_message.text).startswith('/generate'):
                    await generate_using_promt(callback.message.reply_to_message)
                else:
                    await rewrite_text(callback.message.reply_to_message)
            except Exception as e:
                await callback.answer(
                    'Что-то пошло не так и я не могу найти изначальное сообщение. Возможно, вы его удалили')
                logging.error(e)
        elif callback.message.reply_to_message.content_type == content_type.ContentType.DOCUMENT:
            try:
                await document_parser(callback.message.reply_to_message)
            except Exception as e:
                await callback.answer(
                    'Что-то пошло не так и я не могу найти изначальное сообщение. Возможно, вы его удалили')
                logging.error(e)
        elif ((callback.message.reply_to_message.content_type in
               [content_type.ContentType.PHOTO, content_type.ContentType.ANIMATION,
                content_type.ContentType.VIDEO, content_type.ContentType.AUDIO]) or
              callback.message.reply_to_message.caption is not None):
            try:
                await files_with_caption(callback.message.reply_to_message)
            except Exception as e:
                await callback.answer(
                    'Что-то пошло не так и я не могу найти изначальное сообщение. Возможно, вы его удалили')
                logging.error(e)
    elif callback.data == 'telegram-post' or callback.data == 'new_tg_post':
        if callback.data == 'new_tg_post':
            await make_telegram_post(callback.message.reply_to_message)
        else:
            await make_telegram_post(callback.message)
    elif callback.data == 'seo':
        assist_message = await callback.message.reply('Готовлю SEO заголовок и описание')
        admin_promt = ('Ты — профессиональный копирайтер, который разбирается в SEO. Напиши для этого текста '
                       'SEO-заголовок длиной СТРОГО НЕ БОЛЕЕ 75 символов (с учетом пробелов) и SEO-описание '
                       'длиной СТРОГО НЕ БОЛЕЕ 160 символов (с учетом пробелов)')
        user_promt = callback.message.text
        response = get_response(admin_promt=admin_promt, user_promt=user_promt)

        answer = str(response.json()['result']['alternatives'][0]['message']['text'])
        answer = answer.replace('*', '')
        await bot.edit_message_text(text=answer, chat_id=callback.message.chat.id,
                                    message_id=assist_message.message_id)
    elif callback.data == 'titles' or callback.data == 'new_title_variant':
        if callback.data == 'titles':
            assist_message = await callback.message.reply('Придумываю варианты заголовка к этой новости')
        else:
            assist_message = await callback.message.reply_to_message.reply(
                'Придумываю варианты заголовка к этой новости')
        admin_promt = ('Ты — профессиональный журналист. '
                       'Придумал 15 вариантов простых и понятных заголовков к этой нвости. '
                       'В заголовке обязательно должны быть подлежащее в виде существиетльного '
                       'и глагол в виде сказуемого. Длина заголовка не должна превышать 160 символов. '
                       'Заголовок должен быть емким и понятным!')

        if callback.data == 'titles':
            user_promt = callback.message.text
        else:
            user_promt = callback.message.reply_to_message.text

        response = get_response(admin_promt=admin_promt, user_promt=user_promt)
        answer = str(response.json()['result']['alternatives'][0]['message']['text'])
        answer = answer.replace('*', '')
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text='Новый вариант', callback_data='new_title_variant'),
        )
        await bot.edit_message_text(text=answer, chat_id=callback.message.chat.id,
                                    message_id=assist_message.message_id, reply_markup=builder.as_markup())


async def start() -> None:
    logging.info(f'{datetime.datetime.now()} START BOT')
    dp.include_router(r)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(start())
