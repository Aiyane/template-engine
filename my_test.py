#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# my_test.py
"""
模块功能: 测试模板
"""
__author__ = 'Aiyane'
import os
from templite import Templite

loc = os.getcwd()
with open(loc+"\\model.html", "r", encoding="utf8") as fin:
    html = fin.read()

people1 = { "name": "张三", "age": "18", "major": "计算机" }
people2 = { "name": "李四", "age": "19", "major": "金融" }
people3 = { "name": "王五", "age": "20", "major": "法律" }

many_people = [
    people1,
    people2,
    people3
]

tem = Templite(html)
txt = tem.render({
    "many_people": many_people
})

with open(loc+"\\res.html", "w", encoding="utf8") as f:
    f.write(txt)
