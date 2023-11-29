import asyncio
import gui
import argparse
import logging
import socket
import json

from environs import Env
from pathlib import Path


messages_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()
messages_to_save_queue = asyncio.Queue()
watchdog_queue = asyncio.Queue()


file_logger = logging.getLogger('file_logger')
watchdog_logger = logging.getLogger('watchdog_logger')


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


async def authorise(reader, writer, token):
    await reader.readuntil(separator=b'\n')     # не удалять, т.к. нарушается количество считанных от сервера сообщений

    writer.write((token + '\n').encode())
    await writer.drain()

    user = await reader.readuntil(separator=b'\n')
    if 'null' in user.decode():
        watchdog_logger.warning('Неизвестный токен. Проверьте его или удалите из настроек.')
        writer.close()
        await writer.wait_closed()
        return False
    else:
        try:
            user = json.loads((user.decode()).split('\n')[0])
            token = user['account_hash']
            nickname = user['nickname']
        except json.JSONDecodeError:
            watchdog_logger.error('Ошибка. Проверьте настройки.')    # , exc_info=True)
            return False

        # file_logger.info(f'Успешная Авторизация пользователя {nickname} с токеном {token}')
        # messages_queue.put_nowait(f'Успешная Авторизация пользователя {nickname}')
        event = gui.NicknameReceived(f' {nickname}')
        status_updates_queue.put_nowait(event)
        watchdog_queue.put_nowait(f'Connection is alive. Authorization done')
        return True


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


async def read_msgs(host, client_port):
    reader, writer = None, None
    while True:
        if not reader:
            try:
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
                reader, writer = await asyncio.open_connection(host, client_port)
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            except socket.gaierror as error:
                watchdog_logger.error(f'Ошибка домена (IP адреса) {error}')    # , exc_info=True)
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
                await asyncio.sleep(3)
        else:
            try:
                while True:
                    data = await reader.readuntil(separator=b'\n')
                    message = str(f'{data.decode()}').replace('\n', '')
                    messages_queue.put_nowait(message)
                    watchdog_queue.put_nowait(f'Connection is alive. New message in chat')
                    messages_to_save_queue.put_nowait(message)
            except ConnectionAbortedError as error:
                watchdog_logger.error(f'ConnectionAbortedError {error}')    # , exc_info=True)
                reader = None
                writer.close()
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            except asyncio.exceptions.CancelledError as error:
                watchdog_logger.error(f'CancelledError {error}')    # , exc_info=True)
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)


async def put_message_to_server(reader, writer, message):
    message += '\n\n'
    writer.write(message.encode())
    await writer.drain()
    await reader.readuntil(separator=b'\n')


async def send_msgs(host, sender_port, token):
    while True:
        try:
            reader, writer = await chat_connection(host, sender_port, token)
        except TypeError:
            await asyncio.sleep(0)
        try:
            message = await sending_queue.get()
            await put_message_to_server(reader, writer, message)
            watchdog_queue.put_nowait(f'Connection is alive. Message sent')
        except ConnectionAbortedError as error:
            watchdog_logger.error(f'ConnectionAbortedError {error}')    # , exc_info=True)
            reader = None
            writer.close()
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
        except asyncio.exceptions.CancelledError as error:
            watchdog_logger.error(f'CancelledError {error}')    # , exc_info=True)
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)


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
        watchdog_message = await watchdog_queue.get()
        if watchdog_message:
            watchdog_logger.info(watchdog_message)


async def chat_connection(host, sender_port, token):
    # подключение к чату - авторизация с регистрацией (при необходимости)
    reader, writer = None, None
    try:
        # if not token:
        #     reader, writer = await asyncio.open_connection(host, sender_port)
        #     token, nickname = await register(reader, writer)
        try:
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
            reader, writer = await asyncio.open_connection(host, sender_port)
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            if not await authorise(reader, writer, token):
                writer.close()
                await writer.wait_closed()
                raise gui.InvalidToken('Проблема с токеном', 'Проверьте токен. Сервер его не узнал')
        except ConnectionAbortedError as error:
            watchdog_logger.error(f'ConnectionAbortedError {error}')    # , exc_info=True)
            reader = None
            writer.close()
            status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
            await asyncio.sleep(0)
        except socket.gaierror as error:
            watchdog_logger.error(f'Ошибка. Проверьте настройки.{error}')    # , exc_info=True)
            return
    except Exception as error:
        watchdog_logger.error(f'Непредвиденная ошибка. {error}')    # , exc_info=True)
        try:
            writer.close()
            await writer.wait_closed()
        except UnboundLocalError:
            pass
    return reader, writer


async def main():
    host, sender_port, client_port, token, nickname, history = get_args(env)
    filepath = Path.joinpath(Path.cwd(), history)
    Path.mkdir(filepath.parent, exist_ok=True)
    configuring_logging(history)

    if Path.is_file(filepath):
        load_old_messages(filepath)

    file_logger.info(f'Начинаем трансляцию из {host}:{client_port} в {Path.joinpath(Path.cwd(), history)}')

    watchdog_queue.put_nowait(f'Connection is alive. Prompt before auth')
    await chat_connection(host, sender_port, token)


    # обработка сообщений в циклах корутин
    await asyncio.gather(
        read_msgs(host, client_port),
        send_msgs(host, sender_port, token),
        save_messages_to_file(),
        watch_for_connection(),
        gui.draw(messages_queue, sending_queue, status_updates_queue),
    )


if __name__ == "__main__":
    env = Env()
    env.read_env()
    asyncio.run(main())
