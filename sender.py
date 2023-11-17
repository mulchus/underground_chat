import asyncio
import argparse
import logging
import json
import socket

from environs import Env


def get_args(env):
    parser = argparse.ArgumentParser(description='Скрипт чтения подпольного чата')
    parser.add_argument(
        '--message',
        nargs='*',
        type=str,
        help='сообщение (обязательно)',
        required=True,
    )
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

    host = parser.parse_args().host if parser.parse_args().host else env('HOST', 'minechat.dvmn.org')
    sender_port = parser.parse_args().sender_port if parser.parse_args().sender_port else int(env('SENDER_PORT', 5050))
    token = parser.parse_args().token if parser.parse_args().token else env('TOKEN', '')
    nickname = ' '.join(parser.parse_args().nickname) if parser.parse_args().nickname else env('NICKNAME', '')
    message = ' '.join(parser.parse_args().message)

    return message, host, sender_port, token, nickname


async def register(reader, writer):
    await reader.readuntil(separator=b'\n')   # не удалять, т.к. нарушается количество считанных от сервера сообщений

    message = '\n'
    writer.write(message.encode())
    await writer.drain()
    
    await reader.readuntil(separator=b'\n')

    logging.info('Регистрация нового участника чата.')
    await asyncio.sleep(.5)
    while True:
        nickname = input('Введите ваш ник: ')
        if len(nickname):
            nickname += '\n'
            break
    
    writer.write(nickname.encode())
    await writer.drain()
    
    new_user_encoding = await reader.readuntil(separator=b'\n')
    
    new_user = json.loads((new_user_encoding.decode()).split('\n')[0])
    token = new_user['account_hash']
    nickname = new_user['nickname']

    with open('.env', 'a') as file:
        file.write(f'TOKEN={token}\n')
        file.write(f'NICKNAME={nickname}\n')
        file.close()

    await reader.readuntil(separator=b'\n')

    writer.close()
    await writer.wait_closed()
    logging.info('Регистрация завершена успешно! Данные нового пользователя сохранены в файле .env.')
    return token, nickname
    

async def authorise(reader, writer, token):
    await reader.readuntil(separator=b'\n')     # не удалять, т.к. нарушается количество считанных от сервера сообщений

    writer.write((token + '\n').encode())
    await writer.drain()
    
    user = await reader.readuntil(separator=b'\n')
    if 'null' in user.decode():
        logging.info('Неизвестный токен. Проверьте его или удалите из настроек.')
        writer.close()
        await writer.wait_closed()
        return False
    else:
        try:
            user = json.loads((user.decode()).split('\n')[0])
            token = user['account_hash']
            nickname = user['nickname']
        except json.JSONDecodeError:
            logging.error(f'Ошибка. Проверьте настройки.')
            return False

        logging.info(f'Успешная Авторизация пользователя {nickname} с токеном {token}')
        return True
    

async def submit_message(reader, writer, message):
    while True:
        if not message:
            message = input('Введите сообщение: ')
        if len(message):
            message += '\n\n'
            break

    writer.write(message.encode())
    await writer.drain()
    
    await reader.readuntil(separator=b'\n')


async def main():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8',
        level=logging.INFO,
    )

    env = Env()
    env.read_env()
    message, host, server_port, token, nickname = get_args(env)
    
    try:
        if not token:
            reader, writer = await asyncio.open_connection(host, server_port)
            token, nickname = await register(reader, writer)
    
        try:
            reader, writer = await asyncio.open_connection(host, server_port)
            if not await authorise(reader, writer, token):
                writer.close()
                await writer.wait_closed()
                return
        except socket.gaierror as error:
            logging.info(f'Ошибка. Проверьте настройки.{error}')
            return
    
        if not message:
            await submit_message(reader, writer, f'Всем привет!!!')
        else:
            await submit_message(reader, writer, message)
        message = ''
        while True:
            await submit_message(reader, writer, message)
    except (Exception, ConnectionResetError) as error:
        logging.info(f'Непредвиденная ошибка. {error}')
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
    