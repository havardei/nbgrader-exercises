import asyncio
import structlog
import argparse
import random
import time
import socket
from user import User, OperationError
from dummy import login_dummy
from functools import partial


async def simulate_user(hub_url, username, password, delay_seconds, code_execute_seconds):
    await asyncio.sleep(delay_seconds)
    async with User(username, hub_url, partial(login_dummy, password=password)) as u:
        try:
            await u.login()
            await u.ensure_server()
            await u.start_kernel()
            await u.clone_and_release()
        except OperationError:
            pass
        finally:
            try:
                if u.state == User.States.KERNEL_STARTED:
                    await u.stop_kernel()
            except OperationError:
                # We'll try to sto the server anyway
                pass
            try:
                if u.state == User.States.SERVER_STARTED:
                    await u.stop_server()
            except OperationError:
                # Nothing to do
                pass

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        'hub_url',
        help='Hub URL to send traffic to (without a trailing /)'
    )
    argparser.add_argument(
        'user',
        help='username'
    )
    argparser.add_argument(
        'passwd',
        help='passwordd'
    )
    argparser.add_argument(
        '--user-prefix',
        default=socket.gethostname(),
        help='Prefix to use when generating user names'
    )
    argparser.add_argument(
        '--user-session-min-runtime',
        default=60,
        type=int,
        help='Min seconds user is active for'
    )
    argparser.add_argument(
        '--user-session-max-runtime',
        default=300,
        type=int,
        help='Max seconds user is active for'
    )
    argparser.add_argument(
        '--user-session-max-start-delay',
        default=60,
        type=int,
        help='Max seconds by which all users should have logged in'
    )
    argparser.add_argument(
        '--json',
        action='store_true',
        help='True if output should be JSON formatted'
    )
    args = argparser.parse_args()

    processors=[structlog.processors.TimeStamper(fmt="ISO")]

    if args.json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(processors=processors)

    awaits = []
    for i in range(1):
        awaits.append(simulate_user(
            args.hub_url,
            args.user,
            args.passwd,
            0,
            int(random.uniform(args.user_session_min_runtime, args.user_session_max_runtime))
        ))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*awaits))

if __name__ == '__main__':
    main()
