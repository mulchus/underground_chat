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
    data = await reader.read(100)
    logging.info(f'Received: {data.decode()}')
    
    message = '0a85606e-83ba-11ee-aae7-0242ac110002\n'
    writer.write(message.encode())
    await writer.drain()

    await asyncio.sleep(1)
    data = await reader.read(100)
    decode_answer = data.decode()
    logging.info(f'Received: {decode_answer}')
    
    message = 'rECEIVED: hELLO %USERNAME%! ....\n\n'
    writer.write(message.encode())
    await writer.drain()
    
    data = await reader.read(100)
    logging.info(f'Received: {data.decode()}')
    
    message = 'вАШ КОД ОТПРАВЛЕН НА ПРОВЕРКУ. пРЕПОДАВАТЕЛЬ посмотрит и ответит в течение 1 рабочего дня..\n\n'
    writer.write(message.encode())
    await writer.drain()
    
    data = await reader.read(100)
    logging.info(f'Received: {data.decode()}')
   
    writer.close()
    await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
    