import asyncio
import logging
import shlex

from aioimaplib import aioimaplib


class Error(Exception):

  def __str__(self):
    return str(self.message)


class AuthError(Error):

  def __init__(self, host, port, login, password):
    self.host = host
    self.port = port
    self.login = login
    self.password = password
    msg = "could not authenticate to {host}:{port} using {login}:{password}"
    self.message = msg.format(
        host=host, port=port, login=login, password=password)


class Notifier:

  def __init__(self, host, port, login, password):
    self.host = host
    self.port = port
    self.login = login
    self.password = password
    self.boxes = {}
    self.logger = logging.getLogger('imapnotify')

  async def _connect(self, box):
    self.logger.info('connecting to {0}:{1} for {2}'.format(self.host,
                                                            self.port, box))
    imap_client = aioimaplib.IMAP4_SSL(host=self.host)
    try:
      await imap_client.wait_hello_from_server()
      resp = await imap_client.login(self.login, self.password)
    except:
      await imap_client.logout()
    if resp.result == 'OK':
      self.logger.info('connected to {0}:{1} for {2}'.format(self.host,
                                                             self.port, box))
    else:
      await imap_client.logout()
      raise AuthError(self.host, self.port, self.login, self.password)
    self.logger.debug('[{}] connected'.format(box))
    return imap_client

  def add_box(self, name, on_new_message, on_new_message_post=None):
    self.logger.debug('adding {}'.format(name))
    self.boxes[name] = {
        'on_new_message': on_new_message,
        'on_new_message_post': on_new_message_post
    }

  async def run(self):
    self.tasks = [asyncio.ensure_future(self._idle(box)) for box in self.boxes]
    done, pending = await asyncio.wait(self.tasks)
    for task in done:
      err = task.exception()
      if err:
        self.logger.error(err)

  async def stop(self):
    for box in self.boxes.values():
      if 'connection' in box:
        box['connection'].idle_done()
        await box['connection'].logout()
    for task in self.tasks:
      task.cancel()

  async def _idle(self, box):
    await self._select_box(box)
    try:
      client = self.boxes[box]['connection']
      while True:
        msg = await client.wait_server_push()
        self.logger.debug('[{box}] new data: {msg}'.format(box=box, msg=msg))
        if self._is_new_msg(msg):
          self.logger.info('[{box}] new msg detected'.format(box=box))
          await self._on_new_message(box)
          await self._on_new_message_post(box)
    finally:
      self.logger.debug('[{}] idle done'.format(box))
      client.idle_done()

  async def _select_box(self, box='INBOX'):
    self.boxes[box]['connection'] = imap_client = await self._connect(box)
    await imap_client.select(mailbox=box)
    self.logger.debug('[{}] set idle mode'.format(box))
    self.boxes[box]['idle'] = asyncio.ensure_future(imap_client.idle())

  def _is_new_msg(self, msg):
    return 'EXISTS' in msg

  async def _on_new_message(self, box):
    command = self.boxes[box]['on_new_message']
    if '%s' in command:
      command = command % box
    self.logger.debug('[{box}] on_new_message: {command}'.format(
        box=box, command=command))
    return await self._run_on_new_message_callback(run_command,
                                                   shlex.split(command))

  async def _on_new_message_post(self, box):
    if self.boxes[box]['on_new_message_post'] is not None:
      command = self.boxes[box]['on_new_message_post']
      if '%s' in command:
        command = command % box
      self.logger.debug('[{box}] on_new_message_post: {command}'.format(
          box=box, command=command))
      return await self._run_on_new_message_callback(run_command,
                                                     shlex.split(command))
    return noop()

  async def _run_on_new_message_callback(self, callback, box):
    try:
      self.logger.debug('[{box}] firing callback {cb}'.format(
          box=box, cb=callback))
      callback_result = await callback(box)
      self.logger.debug('[{box}] callback result: {res}'.format(
          box=box, res=callback_result))
    except Exception as e:
      self.logger.error(
          '[{box}] error during running callback {cb}: {e}'.format(
              box=box, cb=callback, e=get_error_message(e)))


async def popen_stream(args, **kwargs):
  create = asyncio.subprocess.create_subprocess_exec(*args, **kwargs)
  proc = await create
  return proc


async def check_output(args, **kwargs):
  kwargs['stdout'] = asyncio.subprocess.PIPE
  kwargs['stderr'] = asyncio.subprocess.PIPE
  proc = await popen_stream(args, **kwargs)
  data = bytearray()
  async for line in proc.stdout:
    data.extend(line)
  return data


def get_error_message(exception):
  err_msg = str(exception)
  if not err_msg and hasattr(exception, 'message'):
    err_msg = exception.message
  if not err_msg:
    err_msg = repr(exception)
  return err_msg


def noop():
  fut = asyncio.Future()
  fut.set_result(None)
  return fut


async def run_command(command):
  return await check_output(command)
