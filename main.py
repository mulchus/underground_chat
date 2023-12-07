import asyncio
import anyio
import tkinter as tk
import gui
import argparse
import logging
import socket
import json
import time

from environs import Env
from pathlib import Path
from async_timeout import timeout
from anyio import create_task_group
from tkinter import Entry, Button, Label


messages_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()
messages_to_save_queue = asyncio.Queue()
watchdog_queue = asyncio.Queue()


file_logger = logging.getLogger('file_logger')
watchdog_logger = logging.getLogger('watchdog_logger')
client_reader, client_writer = None, None
sender_reader, sender_writer = None, None


def get_args(environ):
    parser = argparse.ArgumentParser(description='Скрипт чтения подпольного чата')
    parser.add_argument(
        '--host',
        nargs='?',
        type=str,
        help='хост сервера чата'
    )
    parser.add_argument(
        '--sender_port',
        nargs='?',
        type=int,
        help='порт сервера чата'
    )
    parser.add_argument(
        '--client_port',
        nargs='?',
        type=int,
        help='порт сервера чата'
    )
    parser.add_argument(
        '--token',
        nargs='?',
        type=str,
        help='токен зарегистрированного пользователя'
    )
    parser.add_argument(
        '--nickname',
        nargs='*',
        type=str,
        help='никнейм (прозвище) зарегистрированного пользователя'
    )
    parser.add_argument(
        '--history',
        nargs='?',
        type=str,
        help='относительный путь к файлу сообщений чата, включая имя файла'
    )

    host = parser.parse_args().host if parser.parse_args().host else environ('HOST', 'minechat.dvmn.org')
    sender_port = parser.parse_args().sender_port if parser.parse_args().sender_port \
        else int(environ('SENDER_PORT', 5050))
    client_port = parser.parse_args().client_port if parser.parse_args().client_port \
        else int(environ('CLIENT_PORT', 5000))
    token = parser.parse_args().token if parser.parse_args().token else environ('TOKEN', '')
    nickname = ' '.join(parser.parse_args().nickname) if parser.parse_args().nickname else environ('NICKNAME', '')
    history = parser.parse_args().history if parser.parse_args().history else environ('HISTORY', 'chat.txt')

    return host, sender_port, client_port, token, nickname, history


def inform_everywhere(message):
    file_logger.info(message)
    watchdog_logger.info(message)
    messages_queue.put_nowait(message)


def send_error_everywhere(message):
    file_logger.error(message)
    watchdog_logger.error(message)
    messages_queue.put_nowait(message)


async def authorise(token):
    global client_reader, client_writer, sender_reader, sender_writer
    await sender_reader.readuntil(separator=b'\n')  # не удалять, нарушается количество считанных от сервера сообщений
    sender_writer.write((token + '\n').encode())
    await sender_writer.drain()
    user = await sender_reader.readuntil(separator=b'\n')
    
    if 'null' in user.decode():
        sender_writer.close()
        await sender_writer.wait_closed()
        try:
            send_error_everywhere('Неизвестный токен. Проверьте его или удалите из настроек.')
            raise gui.InvalidToken('Проблема с токеном', 'Проверьте токен. Сервер его не узнал')
        except SystemExit:
            exit()
            
    else:
        await sender_reader.readuntil(separator=b'\n')
        user = json.loads((user.decode()).split('\n')[0])
        nickname = user['nickname']
        inform_everywhere(f'Успешная авторизация пользователя {nickname}.')
        event = gui.NicknameReceived(f' {nickname}')
        status_updates_queue.put_nowait(event)


def configuring_logging(history):
    file_logger.setLevel(logging.INFO)
    file_logger_handler = logging.FileHandler(filename=history, encoding='utf-8')
    file_logger_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%d-%m-%Y %H:%M:%S')
    file_logger_handler.setFormatter(file_logger_formatter)
    file_logger.addHandler(file_logger_handler)

    watchdog_logger.setLevel(logging.INFO)
    watchdog_logger_handler = logging.StreamHandler()
    watchdog_logger_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%d-%m-%Y %H:%M:%S')
    watchdog_logger_handler.setFormatter(watchdog_logger_formatter)
    watchdog_logger.addHandler(watchdog_logger_handler)


async def read_msgs():
    while True:
        data = await client_reader.readuntil(separator=b'\n')
        message = str(f'{data.decode()}').replace('\n', '')
        messages_queue.put_nowait(message)
        messages_to_save_queue.put_nowait(message)
        watchdog_queue.put_nowait(f'Соединение стабильно. Новое сообщение в чате.')


async def send_msgs():
    while True:
        message = await sending_queue.get()
        message += '\n\n'
        sender_writer.write(message.encode())
        await sender_writer.drain()
        await sender_reader.readuntil(separator=b'\n')
        watchdog_queue.put_nowait(f'Соединение стабильно. Сообщение отправлено.')


async def save_messages_to_file():
    while True:
        message = await messages_to_save_queue.get()
        file_logger.info(message.replace('\n', ''))


def load_old_messages(filepath):
    with open(filepath, 'rb') as file:
        for line in file:
            messages_queue.put_nowait(line.decode().replace('\n', ''))


async def watch_for_connection():
    while True:
        try:
            async with timeout(5) as cm:
                watchdog_message = await watchdog_queue.get()
                if watchdog_message:
                    watchdog_logger.info(watchdog_message)
        except TimeoutError:
            if cm.expired:
                send_error_everywhere('Длительное бездействие. Попытка переподключения к сети.')
                raise ConnectionError


async def ping_pong():
    timing = 700     # перерыв между проверками, 7200 = 2 часа
    while True:
        try:
            async with timeout(timing) as cm:
                await anyio.sleep(timing-1)
                sender_writer.write('\n\n'.encode())
                await sender_writer.drain()
                await sender_reader.readuntil(separator=b'\n')
        except TimeoutError:
            if cm.expired:
                send_error_everywhere('Нет ответа от сервера. Разрываем соединение и завершаем.')
                await connection_close()
                exit()


async def connection_close():
    global client_reader, client_writer, sender_reader, sender_writer
    time.sleep(1)
    try:    # при запуске скрипта без интернета выдает AttributeError, надо игнорить
        client_writer.close()
        sender_writer.close()
    except AttributeError:
        exit()
    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)


async def handle_connection(host, client_port, sender_port, token):
    global client_reader, client_writer, sender_reader, sender_writer
    while True:
        try:
            async with create_task_group() as task_group:
                task_group.start_soon(watch_for_connection)
                task_group.start_soon(ping_pong)
                task_group.start_soon(read_msgs)
                task_group.start_soon(send_msgs)

        except* (ConnectionError, KeyboardInterrupt, asyncio.exceptions.CancelledError, SystemExit) as excgroup:
            for _ in excgroup.exceptions:
                task_group.cancel_scope.cancel()
            # TODO: это сообщение надо как то сделать однократным, а не в цикле корутины
            # file_logger.info('Ошибка соединения...')
            await connection_close()
                
        if await connection_server(host, client_port, sender_port):
            await authorise(token)


async def register():
    def process_new_message():
        nonlocal user_input
        user_input = reg_input.get()
        inputs.delete(0, tk.END)
    
    async def get_userinput():
        while True:
            reg_root.update()
            if user_input:
                return user_input
    
    user_input = ''
    reg_root = tk.Tk()
    reg_input = tk.StringVar(reg_root)
    reg_root.title('Чат Майнкрафтера - Регистрация')
    
    label = Label(height=3, width=60, bg='black', fg='white', anchor='w', justify='left')
    inputs = Entry(borderwidth=4, textvariable=reg_input)
    button = Button(text="Отправить", command=process_new_message)
    label.pack(side="top", fill=tk.X, expand=True)
    inputs.pack(side="left", fill=tk.X, expand=True)
    button.pack()
    
    await sender_reader.readuntil(separator=b'\n')  # не удалять, нарушается количество считанных от сервера сообщений
    sender_writer.write('\n'.encode())
    await sender_writer.drain()
    await sender_reader.readuntil(separator=b'\n')
    inform_everywhere('Регистрация нового участника чата.')
    label['text'] = 'Введите ваш ник: '
    nickname = await get_userinput() + '\n'
    sender_writer.write(nickname.encode())
    await sender_writer.drain()
    
    new_user_encoding = await sender_reader.readuntil(separator=b'\n')
    
    new_user = json.loads((new_user_encoding.decode()).split('\n')[0])
    token = new_user['account_hash']
    nickname = new_user['nickname']
    
    with open('.env', 'a') as file:
        file.write(f'\nTOKEN={token}\n')
        file.write(f'NICKNAME={nickname}\n')
        file.close()
    
    await sender_reader.readuntil(separator=b'\n')
    inform_everywhere('Регистрация завершена успешно! Данные нового пользователя сохранены в файле .env.')
    reg_root.destroy()
    return token, nickname


async def connection_server(host, client_port, sender_port):
    global client_reader, client_writer, sender_reader, sender_writer
    
    try:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
        
        client_reader, client_writer = await asyncio.open_connection(host, client_port)
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
        
        sender_reader, sender_writer = await asyncio.open_connection(host, sender_port)
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
        
        inform_everywhere('Успешное соединение с сервером.')
        return True
   
    except ConnectionAbortedError as error:
        watchdog_logger.error(f'ConnectionAbortedError {error}')  # , exc_info=True)
        await connection_close()
    except socket.gaierror as error:
        watchdog_logger.error(f'Ошибка соединения. Проверьте настройки.{error}')  # , exc_info=True)
        await connection_close()
    except Exception as error:
        watchdog_logger.error(f'Непредвиденная ошибка. {error}')  # , exc_info=True)
        await connection_close()
    

# async def connection_chat(token):
#     global client_reader, client_writer, sender_reader, sender_writer
#     authorised = await authorise(sender_reader, sender_writer, token)
#     if not authorised:
#         sender_writer.close()
#         await sender_writer.wait_closed()
#         try:
#             send_error_everywhere('Неизвестный токен. Проверьте его или удалите из настроек.')
#             raise gui.InvalidToken('Проблема с токеном', 'Проверьте токен. Сервер его не узнал')
#         except SystemExit:
#             exit()


async def main():
    host, sender_port, client_port, token, nickname, history = get_args(env)
    filepath = Path.joinpath(Path.cwd(), history)
    Path.mkdir(filepath.parent, exist_ok=True)
    configuring_logging(history)

    if Path.is_file(filepath):
        load_old_messages(filepath)

    file_logger.info(f'Старт. Сервер {host}:{client_port}. Сохраняем в {Path.joinpath(Path.cwd(), history)}')

    await connection_server(host, client_port, sender_port)
    
    if not token:
        token, nickname = await register()
        inform_everywhere(f'Успешная авторизация пользователя {nickname}.')
        event = gui.NicknameReceived(f' {nickname}')
        status_updates_queue.put_nowait(event)
    else:
        await authorise(token)
    
    try:
        async with create_task_group() as task_group:
            task_group.start_soon(handle_connection, host, client_port, sender_port, token)
            task_group.start_soon(save_messages_to_file)
            task_group.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
    
    except* asyncio.exceptions.CancelledError as excgroup:
        for _ in excgroup.exceptions:
            task_group.cancel_scope.cancel()
        await connection_close()
        inform_everywhere(f'Работа прервана вручную.')
        

if __name__ == "__main__":
    env = Env()
    env.read_env()
    anyio.run(main)
