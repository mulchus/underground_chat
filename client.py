import asyncio
import argparse
import logging
import time
import socket

from environs import Env
from pathlib import Path


def get_args(env):
    parser = argparse.ArgumentParser(description='Скрипт чтения подпольного чата')
    parser.add_argument(
        '--host',
        nargs='?',
        type=str,
        default='minechat.dvmn.org',
        help='хост сервера чата'
    )
    parser.add_argument(
        '--port',
        nargs='?',
        type=int,
        default=5000,
        help='порт сервера чата'
    )
    parser.add_argument(
        '--history',
        nargs='?',
        type=str,
        help='относительный путь к файлу сообщений чата, включая имя файла'
    )

    host = env('HOST') if env('HOST') else parser.parse_args().host
    port = int(env('PORT')) if env('PORT') else parser.parse_args().port
    history = env('HISTORY') if env('HISTORY') else parser.parse_args().history

    return host, port, history


def fix_message(history, message):
    if history:
        logging.info(message)
    else:
        print(message)


async def main():
    env = Env()
    env.read_env()
    host, port, history = get_args(env)
    if history:
        Path.mkdir(Path.joinpath(Path.cwd(), history).parent, exist_ok=True)
    print(f'Начинаем трансляцию из {host}:{port} в {Path.joinpath(Path.cwd(), history) if history else "терминал"}')

    if history:
        logging.basicConfig(
            filename=history,
            encoding='utf-8',
            level=logging.INFO
        )

    reader, writer = None, None

    while True:
        if not reader:
            try:
                reader, writer = await asyncio.open_connection(host, port)
            except socket.gaierror as error:
                fix_message(history, f'{time.strftime("%d.%m.%Y %H:%M:%S")}: Ошибка домена (IP адреса) {error}')
                await asyncio.sleep(3)
        else:
            try:
                while True:
                    data = await reader.readuntil(separator=b'\n')
                    message = f'{time.strftime("%d.%m.%Y %H:%M:%S")}: {data.decode()}'
                    fix_message(history, message)
            except ConnectionAbortedError as error:
                fix_message(history, f'{time.strftime("%d.%m.%Y %H:%M:%S")}: ConnectionAbortedError {error}')
                reader = None
                writer.close()
            except asyncio.exceptions.CancelledError as error:
                fix_message(history, f'{time.strftime("%d.%m.%Y %H:%M:%S")}: CancelledError {error}')


if __name__ == "__main__":
    asyncio.run(main())
