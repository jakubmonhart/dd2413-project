from time import sleep
import random
from multiprocessing import Process, Event
from little_red_hood import lrh_story
from engage_senteces import sentences
from furhat_remote_api import FurhatRemoteAPI
from collections import deque
import numpy as np
import math

# ip = '192.168.0.103'

def check_engagement(user_engaged_e):
  
  furhat = FurhatRemoteAPI(ip)

  # Detected the user to read to  
  users = furhat.furhat_users_get()
  print(users)
  user_id = users[0].id
  print('I am reading a story for user: ', user_id)
  
  # init 
  average_len = 40
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

    alpha = 180 * math.atan2(-user.location.x, user.location.z)/math.pi
    user_rot = np.array([user.rotation.x, user.rotation.y-alpha])
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
    sleep(0.01)  


def read(user_engaged_e, story):
  story_s = lrh_story.split('.')[:-1]
  story_s = [s + '.' for s in story_s]
  furhat = FurhatRemoteAPI(ip)

  sentence_i = 0
  disengagement_count = 0
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
      disengagement_count += 1

      if disengagement_count == 3:
        furhat.say(text='I see you are not enjoying this one. Maybe you would like to hear another story?', blocking=True)
        
        # Listen to yes
        result = furhat.listen()
        print(result)

        if 'yes' in result.message:
          # Change the story
          story_s = lrh_story.split('.')[:-1]
          story_s = [s + '.' for s in story_s]
          sentence_i = 0
          disengagement_count = 0
          furhat.say(text='Ok, here is another one.', blocking=True)
          sleep(0.5)
          user_engaged_e.set()

        if 'no' in result.message:
          disengagement_count = 0
          furhat.say(text='Great, where did we end?', blocking=True)
          sleep(0.5)
          furhat.say(text='Oh, let me just read the last sentence again.', blocking=True)
          sleep(0.5)
          user_engaged_e.set()
      
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
          furhat.say(text='Ok, it was nice reading to you, see you next time.', blocking=True)
          furhat.gesture(name="ExpressSad")
          break


# def attend(user_id):
#   furhat = FurhatRemoteAPI(ip)

#   while True:
#     users = furhat.furhat_users_get()

#     user = None
#     for u in users:
#       if u.id == user_id:
#         user = u

#     if (user is None) or (users == []):
#       print('User not detected.')

#     # Attend
#     furhat.attend(userid=user_id)

#     sleep(0.5)

  
if __name__=='__main__':
  
  # Look for user to engage with
  furhat = FurhatRemoteAPI(ip)
  print('connected')
  while True:
    users = furhat.get_users()
    print(users)
    if users != []:
      user_id = users[0].id
      break
    else:
      print('no user detected')
  
  furhat.say(text='Greetings!', blocking=True)
  furhat.gesture(name="BrowRaise")
  result = furhat.listen()
  furhat.attend(userid=user_id)

  furhat.say(text=
    'I am a story teller. I read short stories and try to make sure people enjoy them. \
    If you are enjoying the story, I expect you to look at me. \
    With that, would you like to hear some story?')

  # furhat.gesture(name="Roll")
  
  # furhat.say(text='Greetings traveler! Whould you like to hear a short story?', blocking=True)

  while True:
    result = furhat.listen()
    print(result.message)
    if 'yes' in result.message:
      furhat.say(text='Ok the, sit comfortably and enjoy the story!', blocking=True)
      sleep(0.5)
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
  # attend_p = Process(target=attend, args=(user_id,))
  # attend_p.start()

  check_engagement_p.join()
  read_p.join()
  # attend_p.join()
  