import asyncio
import argparse
import logging
import time
import socket


def get_args():
    parser = argparse.ArgumentParser(description='Скрипт чтения подпольного чата')
    parser.add_argument(
        '--logging',
        nargs='?',
        type=bool,
        default=False,
        help='включить или выключить логирование'
    )
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
        '--size',
        nargs='?',
        type=int,
        default=100,
        help='размер считываемого сообщения'
    )
    return parser.parse_args()


def fix_message(parser_args, message):
    if parser_args.logging:
        logging.info(message)
    else:
        print(message)


async def main():
    parser_args = get_args()
    host = parser_args.host
    port = parser_args.port
    _logging = parser_args.logging
    
    if parser_args.logging:
        logging.basicConfig(
            filename='chat.txt',
            encoding='utf-8',
            level=logging.INFO
        )

    reader, writer = None, None

    while True:
        if not reader:
            try:
                reader, writer = await asyncio.open_connection(host, port)
            except socket.gaierror as error:
                fix_message(parser_args, f'{time.strftime("%d.%m.%Y %H:%M:%S")}: Ошибка домена (IP адреса) {error}')
                await asyncio.sleep(3)
        else:
            try:
                while True:
                    data = await reader.readuntil(separator=b'\n')
                    message = f'{time.strftime("%d.%m.%Y %H:%M:%S")}: {data.decode()}'
                    fix_message(parser_args, message)
            except ConnectionAbortedError as error:
                fix_message(parser_args, f'{time.strftime("%d.%m.%Y %H:%M:%S")}: ConnectionAbortedError {error}')
                reader = None
                writer.close()
            except asyncio.exceptions.CancelledError as error:
                fix_message(parser_args, f'{time.strftime("%d.%m.%Y %H:%M:%S")}: CancelledError {error}')


if __name__ == "__main__":
    asyncio.run(main())
