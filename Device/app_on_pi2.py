from flask import Flask, render_template, jsonify, request, make_response, abort
from flask_cors import CORS
from flask_cors import cross_origin
import random
import json
import time
import numpy as np
import sqlite3
from sqlite3 import Error
import RPi.GPIO as GPIO
from adafruit_motorkit import MotorKit

CONTROL_PIN = 17
PWM_FREQ = 50
STEP = 15
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(CONTROL_PIN,GPIO.OUT)
r1 = 24
r2 = 23
m = 4
l2 = 27
l1 = 22 
GPIO.setup(r1,GPIO.IN)
GPIO.setup(r2,GPIO.IN)
GPIO.setup(m,GPIO.IN)
GPIO.setup(l1,GPIO.IN)
GPIO.setup(l2,GPIO.IN)

pwm = GPIO.PWM(CONTROL_PIN,PWM_FREQ)
pwm.start(0)

kit = MotorKit()

center = 80

def angle_to_duty_cycle(angle,turn=False):
    duty_cycle = 2.5 + angle/18.0
    pwm.ChangeDutyCycle(duty_cycle)
    if turn:
        time.sleep(1)
    else:
        time.sleep(0.1)
    return duty_cycle

def motor(left_speed,right_speed,s_time=0.01):
    kit.motor1.throttle = right_speed
    kit.motor2.throttle = -left_speed
    time.sleep(s_time)
    kit.motor1.throttle = 0
    kit.motor2.throttle = 0

def forward():
    motor(0.75,0.75,0.15)
    while True:
        #r, l, on_corner = detect_lines()
        if (GPIO.input(r1)==1) or (GPIO.input(l1)==1):
            motor(0,0)
            time.sleep(0.2)
            return True
            motor(-0.5,-0.5)
            if (GPIO.input(r1)==1) or (GPIO.input(l1)==1): 
                kit.motor1.throttle = 0
                kit.motor2.throttle = 0
                return True

        if GPIO.input(l2)==0 and GPIO.input(r2)==0:
            motor(0.75,0.75)

        
        if GPIO.input(l2)==1 and GPIO.input(r2)==0:
            motor(0,1,0.02)
            
         
        if GPIO.input(l2)==0 and GPIO.input(r2)==1:
            motor(1,0,0.02)
            

        # if GPIO.input(l1)==1 and GPIO.input(l2)==0:
        #     motor(0.5,1)

        # if GPIO.input(r1)==1 and GPIO.input(r2)==0:
        #     motor(1,0.5)

def turn_left():
    motor(0.75,0.75,0.08)
    time.sleep(0.1)
    motor(-1,1,1.6)
    time.sleep(0.1)
    if GPIO.input(r2)==1:
        motor(0.75,0.25,0.1)
    if GPIO.input(l2)==1:
        motor(0.25,0.75,0.1)
    if GPIO.input(r1)==1:
        motor(1,0,0.1)
    if GPIO.input(l1)==1:
        motor(0,1,0.1)

    return True

def turn_right():
    motor(0.75,0.75,0.08)
    time.sleep(0.1)
    motor(1,-1,1.7)
    time.sleep(0.1)
    if GPIO.input(r2)==1:
        motor(0.75,0.25,0.1)
    if GPIO.input(l2)==1:
        motor(0.25,0.75,0.1)
    if GPIO.input(r1)==1:
        motor(1,0,0.1)
    if GPIO.input(l1)==1:
        motor(0,1,0.1)
    return True


def turn_around():
    motor(0.5,0.5)
    time.sleep(0.1)
    motor(-1,1,4)
    time.sleep(0.1)
    if GPIO.input(r2)==1:
        motor(0.75,0.25,0.1)
    if GPIO.input(l2)==1:
        motor(0.25,0.75,0.1)
    if GPIO.input(r1)==1:
        motor(1,-0.2,0.3)
    if GPIO.input(l1)==1:
        motor(-0.2,1,0.3)

    return True

def car_stop():
    kit.motor1.throttle = 0
    kit.motor2.throttle = 0
    # GPIO.cleanup()



app = Flask(__name__)
CORS(app)

@app.route('/stop', methods=['GET'])
def stop():
    car_stop()
    return jsonify("OK")


@app.route('/init', methods=['GET'])
# 初始化資料庫
def init():
    conn = sqlite3.connect('iot5.db')
    c = conn.cursor()

    # 清除表格
    c.execute('''drop table if exists device;''')
    # 建立表格
    c.execute('''create table device
       (ID    INTEGER    PRIMARY KEY    AUTOINCREMENT,
        X     INTEGER                   NOT NULL,
        Y     INTEGER                   NOT NULL,
        DX    INTEGER                   NOT NULL,
        DY    INTEGER                   NOT NULL);''')
    # 新增初始位置
    c.execute("insert into device (X,Y,DX,DY) values (0,0,1,0);")

    conn.commit()
    conn.close()
    return jsonify("OK")


def updateDevice(X, Y, DX, DY):
    conn = sqlite3.connect('iot5.db')
    c = conn.cursor()

    c.execute(" UPDATE device SET X=?, Y=?, DX=?, DY=? WHERE ID = 1;",
              (X, Y, DX, DY))

    conn.commit()
    conn.close()


@app.route('/reset', methods=['GET'])
# 重設rpi目前的位置為(0,0)
# 需要有global var去紀錄
def reset():
    updateDevice(0, 0, 1, 0)
    return jsonify("OK")


@app.route('/location', methods=['GET'])
# 取得rpi目前的位置
# 需要有global var去紀錄
def location():
    conn = sqlite3.connect('iot5.db')
    c = conn.cursor()
    c.execute(" SELECT X,Y,DX,DY FROM device WHERE ID = 1;")
    obj = c.fetchone()
    conn.close()
    # obj = {"X": random.randint(0, 4), "Y": random.randint(0, 2)}
    return jsonify({"X": obj[0], "Y": obj[1], "DX": obj[2], "DY": obj[3]})


@app.route('/map', methods=['POST'])
# 發送路由到rpi上
# F: 往前一單位
# R: 右轉
# L: 左轉
# B: 迴轉
def map():
    cmd = request.data.decode("utf-8")
    car_gogogo(cmd)
    return "done!"


def car_gogogo(cmd):
    conn = sqlite3.connect('iot5.db')
    c = conn.cursor()
    c.execute(" SELECT X,Y,DX,DY FROM device WHERE ID = 1;")
    obj = c.fetchone()
    conn.close()
    pos = np.array([obj[0], obj[1]])
    dir = np.array([obj[2], obj[3]])

    for c in cmd:
        if c == 'F':
            # TODO: 呼叫車車向前
            print('## F ##1')
            forward()
            print('## F ##2')
            pos += dir
        elif c == 'R':
            # TODO: 呼叫車車右轉
            print('## R ##1')
            turn_right()
            print('## R ##2')
            c, s = np.cos(np.radians(-90)), np.sin(np.radians(-90))
            rotation_matrix = np.array(((c, -s), (s, c)))
            dir = np.round(dir.dot(rotation_matrix)).astype(int)
        elif c == 'L':
            # TODO: 呼叫車車左轉
            print('## L ##1')
            turn_left()
            print('## L ##2')
            c, s = np.cos(np.radians(90)), np.sin(np.radians(90))
            rotation_matrix = np.array(((c, -s), (s, c)))
            dir = np.round(dir.dot(rotation_matrix)).astype(int)
        elif c == 'B':
            # TODO: 呼叫車車迴轉
            print('## B ##1')
            turn_around()
            print('## B ##2')
            dir *= -1
        updateDevice(pos[0].item(), pos[1].item(), dir[0].item(), dir[1].item())


# if __name__ == "__main__":
#     try:
#         forward()
#         turn_around()
#         car_stop()
#     except:
#         car_stop()

    # car_gogogo('FRFBFRFFRFLFRF')
    # print('## 1')
    # forward()
    # print('## 2')
    # turn_right()
    # print('## 3')
    # forward()
    # print('## 4')
    # turn_around()
    # print('## 5')
    # forward()
    # print('## 6')
    # turn_right()
    # print('## 7')
    # forward()
    # print('## 8')
    # forward()
    # print('## 9')



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)


'''
if __name__=='__main__':

    try:
        state = forward()
        time.sleep(0.1)
        # turn_around()
        # time.sleep(0.1)
        # forward()
    except:
        kit.motor1.throttle = 0
        GPIO.cleanup()
'''
