import cv2
import mediapipe as mp
import pyautogui
import math
import time
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--debug', action='store_true', help='Show camera window')
args = parser.parse_args()

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.6)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

FOCUS_COOLDOWN  = 0.5
SCROLL_AMOUNT   = 1
SCROLL_INTERVAL = 0.08

tracking   = True
last_focus = 0
last_scroll = 0


def is_right_hand(lm):
    return lm[2].x > lm[0].x


def finger_up(lm, tip_id, mcp_id):
    wrist = lm[0]
    return (math.hypot(lm[tip_id].x - wrist.x, lm[tip_id].y - wrist.y) >
            math.hypot(lm[mcp_id].x - wrist.x, lm[mcp_id].y - wrist.y))


def is_fist(lm):
    return not any(finger_up(lm, tip, mcp) for tip, mcp in [(8,5),(12,9),(16,13),(20,17)])


def switch_workspace(direction):
    key = 'super+Prior' if direction == 'prev' else 'super+Next'
    subprocess.Popen(['xdotool', 'key', key])


def focus_window(direction):
    result = subprocess.run(['bspc', 'node', '-f', direction])
    if result.returncode != 0:
        ws = 'next' if direction in ('east', 'south') else 'prev'
        switch_workspace(ws)


def index_direction(lm):
    dx = lm[8].x - lm[5].x
    dy = lm[8].y - lm[5].y
    if max(abs(dx), abs(dy)) < 0.05:
        return None
    if abs(dx) > abs(dy):
        return 'east' if dx > 0 else 'west'
    else:
        return 'south' if dy > 0 else 'north'


while True:
    success, img = cap.read()
    if not success:
        continue

    img = cv2.flip(img, 1)
    h, w = img.shape[:2]
    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    right_label = left_label = ""

    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)
            lm = hand.landmark

            if not is_right_hand(lm):
                if is_fist(lm):
                    tracking = False
                    right_label = "STOPPED"
                else:
                    tracking = True
                    if tracking:
                        direction = index_direction(lm)
                        now = time.time()
                        if direction and now - last_focus > FOCUS_COOLDOWN:
                            focus_window(direction)
                            last_focus = now
                        arrows = {'west': '←', 'east': '→', 'north': '↑', 'south': '↓'}
                        right_label = f"FOCUS {arrows.get(direction, '')}" if direction else "POINT TO FOCUS"

            else:
                direction = index_direction(lm)
                now = time.time()
                if direction == 'north' and now - last_scroll > SCROLL_INTERVAL:
                    pyautogui.scroll(SCROLL_AMOUNT)
                    last_scroll = now
                    left_label = "SCROLL UP"
                elif direction == 'south' and now - last_scroll > SCROLL_INTERVAL:
                    pyautogui.scroll(-SCROLL_AMOUNT)
                    last_scroll = now
                    left_label = "SCROLL DOWN"
                else:
                    left_label = "SCROLL READY"

    status_color = (0, 220, 0) if tracking else (0, 0, 255)
    cv2.putText(img, "TRACKING" if tracking else "STOPPED", (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
    if right_label and right_label != "STOPPED":
        cv2.putText(img, right_label, (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 160, 0), 2)
    if left_label:
        cv2.putText(img, left_label, (10, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 160), 2)

    if args.debug:
        cv2.imshow("Gesture Control", img)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    else:
        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()
