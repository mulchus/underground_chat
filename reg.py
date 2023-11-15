import asyncio
import logging
import json


host = 'minechat.dvmn.org'
port = 5050


async def main():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8',
        level=logging.INFO,
    )
    
    reader, writer = await asyncio.open_connection(host, port)
    data = await reader.readuntil(separator=b'\n')
    logging.info(f'Received: {data.decode()}')
    
    message = '\n'
    writer.write(message.encode())
    await writer.drain()
    
    data = await reader.readuntil(separator=b'\n')
    logging.info(f'Received: {data.decode()}')
    
    print('Регистрация нового участника чата.')
    while True:
        user_nik = input('Введите ваш ник: ')
        if len(user_nik):
            user_nik += '\n'
            break
    
    writer.write(user_nik.encode())
    await writer.drain()
    
    new_user_encoding = await reader.readuntil(separator=b'\n')
    
    new_user = json.loads((new_user_encoding.decode()).split('\n')[0])
    account_hash = new_user['account_hash']
    with open('account_hash', 'w') as file:
        file.write(account_hash)
        file.close()
    
    writer.close()
    await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
    