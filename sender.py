import asyncio
import logging
import json


host = 'minechat.dvmn.org'
port = 5050


async def register(reader, writer):
    data = await reader.readuntil(separator=b'\n')
    # logging.info(f'Received: {data.decode()}')
    
    message = '\n'
    writer.write(message.encode())
    await writer.drain()
    
    data = await reader.readuntil(separator=b'\n')
    # logging.info(f'Received: {data.decode()}')
    
    logging.info('Регистрация нового участника чата.')
    await asyncio.sleep(.5)
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
    
    data = await reader.readuntil(separator=b'\n')
    # logging.info(f'Received: {data.decode()}')
    
    writer.close()
    await writer.wait_closed()
    logging.info('End registration!')
    

async def authorise(reader, writer):
    data = await reader.readuntil(separator=b'\n')
    # logging.info(f'Received: {data.decode()}')
    
    with open('account_hash', 'r') as file:
        account_hash = file.read()
    
    writer.write((account_hash + '\n').encode())
    await writer.drain()
    
    data = await reader.readuntil(separator=b'\n')
    if 'null' in data.decode():
        logging.info('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
        writer.close()
        await writer.wait_closed()
        return
    else:
        # logging.info(f'Received: {data.decode()}')
        pass
    
    logging.info('End authorise!')
    

async def submit_message(reader, writer):
    while True:
        message = input('Введите сообщение: ')
        if len(message):
            message += '\n\n'
            break
    
    writer.write(message.encode())
    await writer.drain()
    
    data = await reader.readuntil(separator=b'\n')
    # logging.info(f'Received: {data.decode()}')
    

async def main():
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        encoding='utf-8',
        level=logging.INFO,
    )
    reader, writer = await asyncio.open_connection(host, port)
    await register(reader, writer)
    reader, writer = await asyncio.open_connection(host, port)
    await authorise(reader, writer)
    while True:
        await submit_message(reader, writer)
        
    writer.close()
    await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
    