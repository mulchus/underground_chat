import asyncio
import argparse
import logging
import time


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


async def tcp_client(parser_args, host, port):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        data = await reader.readuntil(separator=b'\n')
        message = f'{time.strftime("%d.%m.%Y %H:%M")}: {data.decode()}'
        fix_message(parser_args, message)
        
        # while not reader.at_eof():
        #     data = await asyncio.wait_for(reader.read(100), 3.0)
        #     print('raw data received: {}'.format(data))
        
    finally:
        writer.close()


async def tcp_reconnect(parser_args, host, port):
    server = '{} {}'.format(host, port)
    while True:
        print('Connecting to server {} ...'.format(server))
        try:
            await tcp_client(parser_args, host, port)
        except (ConnectionRefusedError, ConnectionAbortedError):
            print('Connection to server {} failed!'.format(server))
        except asyncio.TimeoutError:
            print('Connection to server {} timed out!'.format(server))
        else:
            print('Connection to server {} is closed.'.format(server))
        # await asyncio.sleep(2.0)


async def main():
    parser_args = get_args()
    host = parser_args.host
    port = parser_args.port
    _logging = parser_args.logging
    print(_logging)
    if parser_args.logging:
        logging.basicConfig(
            filename='chat.txt',
            encoding='utf-8',
            level=logging.INFO
        )
    
    coros = tcp_reconnect(parser_args, host, port)
    await asyncio.gather(coros)
    
    # reader, writer = await asyncio.open_connection(host, port)
    
    # while True:
    #     try:
    #         # with open('chat.txt', '+a', encoding='utf-8') as file:
    #         # while True:
    #         data = await reader.readuntil(separator=b'\n')
    #         message = f'{time.strftime("%d.%m.%Y %H:%M")}: {data.decode()}'
    #         fix_message(parser_args, message)
    #         # file.writelines(message)
    #     except asyncio.exceptions.CancelledError:
    #         fix_message(parser_args, f'{time.strftime("%d.%m.%Y %H:%M")}: Close the connection')
    #     except IndexError:
    #         fix_message(parser_args, f'{time.strftime("%d.%m.%Y %H:%M")}: IndexError')
    #     except SystemExit :
    #         fix_message(parser_args, f'{time.strftime("%d.%m.%Y %H:%M")}: SystemExit error')
    #     except (ConnectionAbortedError, Exception) as error:
    #         fix_message(parser_args, f'{time.strftime("%d.%m.%Y %H:%M")}: {error}')
    #         time.sleep(1)
            # reader, writer = await asyncio.open_connection(host, port)
        # finally:
            # writer.close()
            # await writer.wait_closed()
            # reader, writer = await asyncio.open_connection(host, port)


if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.create_task(main())
