import asyncio
import gui

from time import strftime, localtime


loop = asyncio.get_event_loop()

messages_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()


async def generate_msgs():
    messages_queue.put_nowait(f'{strftime("%a, %d %b %Y %H:%M:%S %Z", localtime())}')
    print(f'{strftime("%a, %d %b %Y %H:%M:%S %Z", localtime())}')
    await asyncio.sleep(1)


async def main():
    # await generate_msgs()
    # await asyncio.sleep(1)
    # res = await gui.draw(messages_queue, sending_queue, status_updates_queue)
    # print(res)
    while True:
        await generate_msgs(),
        # res = await asyncio.gather(
        #     generate_msgs(),
        #     generate_msgs(),
        #     generate_msgs(),
        #     generate_msgs(),
        #     # gui.update_tk(root_frame),
        #     # gui.update_conversation_history(conversation_panel, messages_queue),
        #     # asyncio.sleep(1)
        #     # gui.draw(messages_queue, sending_queue, status_updates_queue),
        #     # generate_msgs(),
        #     # gui.draw(messages_queue, sending_queue, status_updates_queue),
        # )
        await gui.draw(messages_queue, sending_queue, status_updates_queue)
        # status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
        # print(res)


if __name__ == "__main__":
    # loop.run_until_complete(gui.draw(messages_queue, sending_queue, status_updates_queue))
    asyncio.run(main())
    
    
    
