import asyncio
import logging


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
        logging.info(f'Received: {data.decode()}')
    
    message = 'rECEIVED: hELLO %USERNAME%! ....\n\n'
    writer.write(message.encode())
    await writer.drain()
    
    data = await reader.readuntil(separator=b'\n')
    logging.info(f'Received: {data.decode()}')
    
    message = 'вАШ КОД ОТПРАВЛЕН НА ПРОВЕРКУ. пРЕПОДАВАТЕЛЬ посмотрит и ответит в течение 1 рабочего дня..\n\n'
    writer.write(message.encode())
    await writer.drain()
    
    data = await reader.readuntil(separator=b'\n')
    logging.info(f'Received: {data.decode()}')
   
    writer.close()
    await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
    