from flask import Flask, render_template, jsonify, request, make_response, abort
from flask_cors import CORS
from flask_cors import cross_origin
import random
import json
import time
import numpy as np
import sqlite3
from sqlite3 import Error

app = Flask(__name__)
CORS(app)


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
    conn = sqlite3.connect('iot5.db')
    c = conn.cursor()
    c.execute(" SELECT X,Y,DX,DY FROM device WHERE ID = 1;")
    obj = c.fetchone()
    conn.close()
    pos = np.array([obj[0], obj[1]])
    dir = np.array([obj[2], obj[3]])

    str = request.data.decode("utf-8")
    for c in str:
        if c == 'F':
            time.sleep(1.5)
            # TODO: 呼叫車車向前
            pos += dir
        elif c == 'R':
            time.sleep(1.5)
            # TODO: 呼叫車車右轉
            c, s = np.cos(np.radians(-90)), np.sin(np.radians(-90))
            rotation_matrix = np.array(((c, -s), (s, c)))
            dir = np.round(dir.dot(rotation_matrix)).astype(int)
        elif c == 'L':
            time.sleep(1.5)
            # TODO: 呼叫車車左轉
            c, s = np.cos(np.radians(90)), np.sin(np.radians(90))
            rotation_matrix = np.array(((c, -s), (s, c)))
            dir = np.round(dir.dot(rotation_matrix)).astype(int)
        elif c == 'B':
            time.sleep(1.5)
            # TODO: 呼叫車車迴轉
            dir *= -1
        updateDevice(pos[0].item(), pos[1].item(), dir[0].item(), dir[1].item())
    return "done!"


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
