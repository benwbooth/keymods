#!/usr/bin/env python3
import evdev, aiostream, pprint, asyncio, re, sys, subprocess
from evdev import ecodes
from evdev.ecodes import *
from collections.abc import Iterable, Awaitable
from shlex import quote as q
from contextlib import asynccontextmanager

DOWN = 1
UP = 0
pattern = sys.argv[1] or r'Keyboard.*-kbd$'

devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
# ls -l /dev/input/by-id
kbds = [d for d in devices if re.search(pattern, d.name)]
if len(kbds) > 1:
    print(f"Multiple keyboards matched pattern {q(pattern)}: {' '.join(q(k.name) for k in kbds)}", file=sys.stderr)
    sys.exit(1)
if len(kbds) == 0:
    print(f"No keyboards matched pattern {q(pattern)}, check /dev/input/by-id:", file=sys.stderr)
    subprocess.run(["ls","-l","/dev/input/by-id"])
    sys.exit(1)
kbd = kbds[0]

# async generator objects: pep525; g.asend(); x = yield y

class ParserFail(Exception)

async def pressed(key=None):
    ev = yield
    if not (ev.type == EV_KEY and (key is None or ev.code == key) and ev.value == DOWN):
        raise ParserFail()
    return ev.code

async def wait_pressed(key=None):
    ev = yield
    while not (ev.type == EV_KEY and (key is None or ev.code == key) and ev.value == DOWN):
        ev = yield
    return ev.code

async def released(key=None):
    ev = yield
    if not (ev.type == EV_KEY and (key is None or ev.code == key) and ev.value == UP):
        raise ParserFail()
    return ev.code
 
async def wait_released(key=None):
    ev = yield
    while not (ev.type == EV_KEY and (key is None or ev.code == key) and ev.value == UP):
        ev = yield
    return ev.code
 
async def pushed(key=None):
    yield pressed(key)
    yield wait_released(key)

@asynccontextmanager
async def held(key=None)
    await pressed(key)
    yield

async def combine(*parsers):
    while True:
        ev = yield
        for p in parsers:
            p.asend(ev)

async def layout():
    async def caps2esc():
        await pushed(KEY_CAPSLOCK)
        press(KEY_ESCAPE)

    async def space2meta():
        pass

    asyncio.gather(caps2esc, space2meta)

async def handler(device):
    parsers = set()
    async for event in device.async_read_loop():
        parsers.add(layout())
        next_parsers = set()
        for p in parsers:
            result = await p.asend(event)
            for r in (result if isinstance(result, Iterable) else [result]):
                next_parsers.add(r)
        parsers = next_parsers

asyncio.ensure_future(handler(kbd))
asyncio.get_event_loop().run_forever()
