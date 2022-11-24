from time import sleep
import random
from multiprocessing import Process, Event
from little_red_hood import story
from engage_senteces import sentences
from furhat_remote_api import FurhatRemoteAPI
from collections import deque
import numpy as np

ip = '192.168.0.103'

def check_engagement(user_engaged_e):
  
  furhat = FurhatRemoteAPI(ip)

  # Detected the user to read to  
  users = furhat.furhat_users_get()
  print(users)
  user_id = users[0].id
  print('I am reading a story for user: ', user_id)
  
  # init 
  average_len = 20
  engaged_q = deque([1]*average_len, maxlen=average_len)
  default_rot = np.array([0, 180])

  while True:
    users = furhat.furhat_users_get()

    user = None
    for u in users:
      if u.id == user_id:
        user = u

    if (user is None) or (users == []):
      print('User not detected.')

    user_rot = np.array([user.rotation.x, user.rotation.y])
    disengagement = np.abs(user_rot-default_rot)
    # print(disengagement)

    if (disengagement[0] > 20) or (disengagement[1] > 20):
      engaged_q.append(0)
    else:
      engaged_q.append(1)

    # Compute moving average
    sma = sum(engaged_q)/len(engaged_q)

    # Check if user engaged
    if sma < 0.4:
      # Stop talking
      furhat.say_stop()

      # Indicate user is not engaged
      user_engaged_e.clear()
      
      # Wait for user to be engaged again
      user_engaged_e.wait()
      engaged_q = deque([1]*average_len, maxlen=average_len)

    print(disengagement)
    print(engaged_q)
    print(sma)
    sleep(0.1)  


def read(user_engaged_e, story):
  story_s = story.split('.')[:-1][:5]
  story_s = [s + '.' for s in story_s]
  furhat = FurhatRemoteAPI(ip)

  sentence_i = 0
  while True:
    if user_engaged_e.is_set():
      
      # read
      furhat.say(text=story_s[sentence_i], blocking=True)
      
      # Only increase count if engaged
      if user_engaged_e.is_set():
        sentence_i += 1

      if sentence_i == len(story_s):
        break

    else:
      # Try to engage back
      sentence = random.choice(sentences)
      furhat.say(text=sentence, blocking=True)

      # Listen to yes
      result = furhat.listen()
      print(result)

      if 'yes' in result.message:
        furhat.say(text='Great, where did we end?', blocking=True)
        sleep(0.5)
        furhat.say(text='Oh, let me just read the last sentence again.', blocking=True)
        sleep(0.5)
        user_engaged_e.set()

      elif 'no' in result.message:
        furhat.say(text='Ok, but just so you know, you made me very sad.', blocking=True)
        furhat.gesture(name="ExpressSad")
        break
        
  
if __name__=='__main__':
  
  # Look for user to engage with
  furhat = FurhatRemoteAPI(ip)
  print('connected')
  while True:
    users = furhat.get_users()
    print(users)
    if users is not []:
      user_id = users[0].id
      break
    else:
      print('no user detected')
  
  furhat.gesture(name="BrowRaise")
  furhat.gesture(name="Roll")
  furhat.say(text='Greetings traveler! Whould you like to hear a short story?', blocking=True)

  while True:
    result = furhat.listen()
    if 'yes' in result.message:
      furhat.say(text='Great! Let me begin.', blocking=True)
      print(result.message)
      break
    else:
      # furhat.gesture(name="")
      furhat.say(text='Are you sure about that? Let me ask you again: Would you like to hear a short story? Please!', blocking=True)

  # Start the reading process
  user_engaged_e = Event()
  user_engaged_e.set()
  check_engagement_p = Process(target=check_engagement, args=(user_engaged_e,))
  check_engagement_p.start()
  read_p = Process(target=read, args=(user_engaged_e, story,))
  read_p.start()

  check_engagement_p.join()
  read_p.join()
  