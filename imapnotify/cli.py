import argparse
import asyncio
import json
import logging

from .core import Notifier


def setup_logging(name='imapnotify', verbosity=1):
  log_level = {
      1: logging.WARNING,
      2: logging.INFO,
      3: logging.DEBUG,
  }.get(verbosity, logging.ERROR)
  logger = logging.getLogger(name)
  logger.setLevel(log_level)
  sh = logging.StreamHandler()
  sh.setFormatter(
      logging.Formatter(
          "%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s"))
  logger.addHandler(sh)
  return logger


def read_config(path):
  with open(path) as fp:
    return json.load(fp)


def parse_args():
  parser = argparse.ArgumentParser(
      description='use IDLE command to wait on new mail')
  parser.add_argument('-c', '--config', required=True)
  parser.add_argument('--verbose', '-v', action='count', default=0)
  return parser.parse_args()


def main():
  args = parse_args()
  loop = asyncio.get_event_loop()
  config = read_config(args.config)
  verbosity = args.verbose + 1
  if verbosity >= 4:
    setup_logging('imapnotify', verbosity=3)
    setup_logging('aioimaplib.aioimaplib', verbosity=verbosity - 3)
  else:
    setup_logging('imapnotify', verbosity=verbosity)
  n = Notifier(config['host'], config.get('port', 993), config['username'],
               config['password'])
  for box in config['boxes']:
    n.add_box(box, config['onNewMail'], config['onNewMailPost'])
  try:
    loop.run_until_complete((n.run()))
  except KeyboardInterrupt:
    n.logger.error('KeyboardInterrupt, exiting')
    loop.run_until_complete((n.stop()))
