'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-04 13:09:48
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-04 13:14:41
FilePath: \test\test_flask.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)  # 禁用重载器