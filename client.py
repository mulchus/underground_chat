import asyncio


# async def handle_message():
#
#     # print(f'Send: {message!r}')
#     # writer.write(message.encode())
#     # await writer.drain()
#
#     data = await reader.read(100)
#     print(f'Received: {data.decode()!r}')
#
#     print('Close the connection')
#     writer.close()
#     await writer.wait_closed()


async def main():
    reader, writer = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)
    
    try:
        while True:
            # time = await reader.
            data = await reader.readuntil(separator=b'\n')  # readline()
            # print(f'{data.decode()!r}')
            print(f'Received: {data.decode()!r}')
    except Exception:
        print('Close the connection')
        writer.close()
        await writer.wait_closed()
    

asyncio.run(main())
