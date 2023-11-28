import asyncio
import gui
import argparse
import logging
import socket

from time import strftime, localtime
from environs import Env
from pathlib import Path


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
    history = parser.parse_args().history if parser.parse_args().history else environ('HISTORY', '')

    return host, sender_port, client_port, token, nickname, history


def fix_message(history, message):
    if history:
        logging.info(message)
    else:
        print(message)


def configuring_logging(host, client_port, history):
    if history:
        Path.mkdir(Path.joinpath(Path.cwd(), history).parent, exist_ok=True)
    print(f'Начинаем трансляцию '
          f'из {host}:{client_port} в {Path.joinpath(Path.cwd(), history) if history else "терминал"}')

    if history:
        logging.basicConfig(
            filename=history,
            encoding='utf-8',
            level=logging.INFO
        )


async def read_msgs(host, client_port, messages_queue, history):
    reader, writer = None, None
    while True:
        if not reader:
            try:
                reader, writer = await asyncio.open_connection(host, client_port)
            except socket.gaierror as error:
                fix_message(history, f'{strftime("%d.%m.%Y %H:%M:%S")}: Ошибка домена (IP адреса) {error}')
                await asyncio.sleep(3)
        else:
            try:
                while True:
                    data = await reader.readuntil(separator=b'\n')
                    message = f'{strftime("%d.%m.%Y %H:%M:%S")}: {data.decode()}'
                    messages_queue.put_nowait(message)
                    fix_message(history, message)
            except ConnectionAbortedError as error:
                fix_message(history, f'{strftime("%d.%m.%Y %H:%M:%S")}: ConnectionAbortedError {error}')
                reader = None
                writer.close()
            except asyncio.exceptions.CancelledError as error:
                fix_message(history, f'{strftime("%d.%m.%Y %H:%M:%S")}: CancelledError {error}')


async def generate_msgs(messages_queue):
    while True:
        messages_queue.put_nowait(f'{strftime("%a, %d %b %Y %H:%M:%S %Z", localtime())}')
        await asyncio.sleep(1)


async def main():
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    host, sender_port, client_port, token, nickname, history = get_args(env)
    configuring_logging(host, client_port, history)

    await asyncio.gather(
        read_msgs(host, client_port, messages_queue, history),
        gui.draw(messages_queue, sending_queue, status_updates_queue),
    )


if __name__ == "__main__":
    env = Env()
    env.read_env()
    asyncio.run(main())
