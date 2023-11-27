import asyncio
import gui
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
        help='хост сервера чата'
    )
    parser.add_argument(
        '--client_port',
        nargs='?',
        type=int,
        help='порт сервера чата'
    )
    parser.add_argument(
        '--history',
        nargs='?',
        type=str,
        help='относительный путь к файлу сообщений чата, включая имя файла'
    )

    host = parser.parse_args().host if parser.parse_args().host else env('HOST', 'minechat.dvmn.org')
    client_port = parser.parse_args().client_port if parser.parse_args().client_port else int(env('CLIENT_PORT', 5000))
    history = parser.parse_args().history if parser.parse_args().history else env('HISTORY', '')

    return host, client_port, history


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
        

async def main():
    env = Env()
    env.read_env()
    host, client_port, history = get_args(env)
    
    configuring_logging(host, client_port, history)

    reader, writer = None, None

    while True:
        if not reader:
            try:
                reader, writer = await asyncio.open_connection(host, client_port)
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
    loop = asyncio.get_event_loop()

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    messages_queue.put_nowait('Привет обитателям чата!')
    messages_queue.put_nowait('Как дела?')

    loop.run_until_complete(gui.draw(messages_queue, sending_queue, status_updates_queue))

    asyncio.run(main())
