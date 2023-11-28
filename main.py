import asyncio
import gui
import argparse
import logging
import socket

from time import strftime, localtime
from environs import Env
from pathlib import Path


messages_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()
messages_to_save_queue = asyncio.Queue()


def create_logger():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8',
        level=logging.INFO,
    )


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


def fix_message(history, message):
    if history:
        logging.info(message)
    else:
        print(message)


def configuring_logging(host, client_port, history):
    logging.basicConfig(
        filename=history,
        encoding='utf-8',
        level=logging.INFO
    )
    print(f'Начинаем трансляцию из {host}:{client_port} в {Path.joinpath(Path.cwd(), history)}')


async def read_msgs(host, client_port, history):
    reader, writer = None, None
    while True:
        if not reader:
            try:
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
                reader, writer = await asyncio.open_connection(host, client_port)
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            except socket.gaierror as error:
                fix_message(history, f'{strftime("%d.%m.%Y %H:%M:%S")}: Ошибка домена (IP адреса) {error}')
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
                await asyncio.sleep(3)
        else:
            try:
                while True:
                    data = await reader.readuntil(separator=b'\n')
                    message = f'{strftime("%d.%m.%Y %H:%M:%S")}: {data.decode()}'
                    messages_queue.put_nowait(message)
                    messages_to_save_queue.put_nowait(message)
            except ConnectionAbortedError as error:
                fix_message(history, f'{strftime("%d.%m.%Y %H:%M:%S")}: ConnectionAbortedError {error}')
                reader = None
                writer.close()
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
            except asyncio.exceptions.CancelledError as error:
                fix_message(history, f'{strftime("%d.%m.%Y %H:%M:%S")}: CancelledError {error}')
                status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)


async def generate_msgs():
    while True:
        messages_queue.put_nowait(f'{strftime("%a, %d %b %Y %H:%M:%S %Z", localtime())}')
        await asyncio.sleep(1)


async def save_messages():
    while True:
        msg = await messages_to_save_queue.get()
        logging.info(msg)


def load_old_messages(filepath):
    with open(filepath, 'r') as file:
        for line in file:
            messages_queue.put_nowait(line)


async def main():
    host, sender_port, client_port, token, nickname, history = get_args(env)
    filepath = Path.joinpath(Path.cwd(), history)
    Path.mkdir(filepath.parent, exist_ok=True)
    configuring_logging(host, client_port, history)

    if Path.is_file(filepath):
        load_old_messages(filepath)

    await asyncio.gather(
        read_msgs(host, client_port, history),
        save_messages(),
        gui.draw(messages_queue, sending_queue, status_updates_queue),
    )


if __name__ == "__main__":
    env = Env()
    env.read_env()
    asyncio.run(main())
