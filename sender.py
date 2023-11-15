import asyncio


host = 'minechat.dvmn.org'
port = 5050


async def main():
    reader, writer = await asyncio.open_connection(host, port)

    print(reader, writer)

    message = '0a85606e-83ba-11ee-aae7-0242ac110002'
    # msg_byt = str.encode(message)
    # print(type(msg_byt))
    # print(msg_byt)

    # print(str.encode(message))
    # print(message.encode())
    # message = ''
    # print(str.encode(message))
    # print(message.encode())

    writer.write(message.encode())
    writer.write(message.encode())
    message = ''
    writer.write(message.encode())

    writer.write(str.encode(message))
    message = ''
    writer.write(str.encode(message))


    # writer.close()
    # await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())