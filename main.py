import asyncio
import gui

from time import strftime, localtime


loop = asyncio.get_event_loop()

messages_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()


async def generate_msgs():
    while True:
        messages_queue.put_nowait(f'{strftime("%a, %d %b %Y %H:%M:%S %Z", localtime())}')
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(
        generate_msgs(),
        gui.draw(messages_queue, sending_queue, status_updates_queue),
    )


if __name__ == "__main__":
    asyncio.run(main())
