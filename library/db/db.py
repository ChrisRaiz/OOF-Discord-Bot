from os.path import isfile
from sqlite3 import connect, OperationalError

from apscheduler.triggers.cron import CronTrigger

DB_PATH = "./data/db/database.db"
BUILD_PATH = "./data/db/build.sql"

cxn = connect(DB_PATH, check_same_thread=False)
cursor = cxn.cursor()

def with_commit(func):
	def inner(*args, **kwargs):
		func(*args, **kwargs)
		commit()

	return inner
  
@with_commit
def build():
  print('Build() execution start')
  if isfile(BUILD_PATH):
    script_execute(BUILD_PATH)
  print('Build() execution end')

def commit():
  cxn.commit()

def autosave(sched):
	sched.add_job(commit, CronTrigger(second=0))
  
def close():
  cxn.close()

def field(command, *values):
  cursor.execute(command, tuple(values))

  if (fetch := cursor.fetchone()) is not None:
    return fetch[0]

def record(command, *values):
  cursor.execute(command, tuple(values))

  return cursor.fetchone()

def records(command, *values):
  cursor.execute(command, tuple(values))

  return cursor.fetchall()

def column(command, *values):
  cursor.execute(command, tuple(values))

  return [item[0] for item in cursor.fetchall()]

def execute(command, *values):
  cursor.execute(command, tuple(values))

def multi_execute(command, valueset):
  cursor.executemany(command, valueset)

def script_execute(path):
  with open(path, "r", encoding="utf-8") as script:
    cursor.executescript(script.read())

def fetch_polls():
  try:
    polls =  {}
    rows = records("SELECT Question, MessageID, ChannelID FROM polls")
    for row in rows:
        polls[row[0]] = (row[1], row[2])
    return polls
  except OperationalError as e:
      print(e)