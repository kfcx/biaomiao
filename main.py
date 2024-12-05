# -*- coding: utf-8 -*-
# @Time    : 2024/12/5
# @Author  : Naihe
# @File    : 白描.py
# @Software: PyCharm
import configparser
import requests
import uuid
import hashlib
import time
import json


filename = 'config.ini'
config = configparser.ConfigParser()
config.read(filename)


class BaimiaoOCR:
    def __init__(self, default_config):
        for key, value in default_config.items():
            setattr(self, key, value)

        self.url = "https://web.baimiaoapp.com"
        self.headers = {
            "Host": "web.baimiaoapp.com",
            "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'X-AUTH-TOKEN': self.login_token,
            'X-AUTH-UUID': self.uuid,
            'Origin': 'https://web.baimiaoapp.com',
            'Referer': 'https://web.baimiaoapp.com/',
        }

    def login(self):
        self.uuid = str(uuid.uuid4())
        config.set('default', "uuid", self.uuid)
        self.headers["X-AUTH-UUID"] = self.uuid

        login_headers = self.headers.copy()
        login_headers['X-AUTH-TOKEN'] = ''
        login_headers['X-AUTH-UUID'] = self.uuid

        login_type = "mobile" if self.username.isdigit() else "email"

        data = {
            'username': self.username,
            'password': self.password,
            'type': login_type
        }

        response = requests.post(f"{self.url}/api/user/login", headers=login_headers, json=data)
        if response.ok:
            result = response.json()
            if result.get('data', {}).get('token'):
                self.login_token = result['data']['token']
                config.set('default', "login_token", self.login_token)
                self.headers["X-AUTH-TOKEN"] = self.login_token
            else:
                raise Exception(json.dumps(result, ensure_ascii=False))
        else:
            raise Exception(f"Http Request Error\nHttp Status: {response.status_code}\n{response.text}")

    def recognize(self, base64_image):
        if not self.uuid or not self.login_token:
            self.login()
            self.write_config()

        self.headers['X-AUTH-UUID'] = self.uuid
        self.headers['X-AUTH-TOKEN'] = self.login_token

        # Fetch announcement (can be ignored)
        # requests.get(f"{self.url}/api/user/announcement", headers=self.headers)

        # Anonymous login
        response = requests.post(f"{self.url}/api/user/login/anonymous", headers=self.headers)
        if response.ok:
            result = response.json()
            if result.get('data', {}).get('token') is not None:
                self.login_token = result['data']['token']
                if not self.login_token:
                    self.login()
                self.headers["X-AUTH-TOKEN"] = self.login_token
            else:
                raise Exception(json.dumps(result, ensure_ascii=False))
        else:
            raise Exception(f"Http Request Error\nHttp Status: {response.status_code}\n{response.text}")

        # Get permission
        data = {'mode': 'single'}
        response = requests.post(f"{self.url}/api/perm/single", headers=self.headers, json=data)
        if response.ok:
            result = response.json()
            if result.get('data', {}).get('engine'):
                engine = result['data']['engine']
                token = result['data']['token']
            else:
                raise Exception("已经达到今日识别上限，请前往白描手机端开通会员或明天再试")
        else:
            raise Exception(f"Http Request Error\nHttp Status: {response.status_code}\n{response.text}")

        # Compute hash
        image_data_url = f"data:image/png;base64,{base64_image}"
        hash_value = hashlib.sha1(image_data_url.encode('utf-8')).hexdigest()

        # Start OCR process
        data = {
            "batchId": "",
            "total": 1,
            "token": token,
            "hash": hash_value,
            "name": "pot_screenshot_cut.png",
            "size": 0,
            "dataUrl": image_data_url,
            "result": {},
            "status": "processing",
            "isSuccess": False
        }
        response = requests.post(f"{self.url}/api/ocr/image/{engine}", headers=self.headers, json=data)
        if response.ok:
            result = response.json()
            if result.get('data', {}).get('jobStatusId'):
                job_status_id = result['data']['jobStatusId']
            else:
                raise Exception(json.dumps(result, ensure_ascii=False))
        else:
            raise Exception(f"Http Request Error\nHttp Status: {response.status_code}\n{response.text}")

        # Polling for result
        while True:
            time.sleep(0.1)
            params = {'jobStatusId': job_status_id}
            response = requests.get(f"{self.url}/api/ocr/image/{engine}/status", headers=self.headers, params=params)
            if response.ok:
                result = response.json()
                if not result.get('data', {}).get('isEnded'):
                    continue
                else:
                    words_result = result['data']['ydResp']['words_result']
                    text = "\n".join([item['words'] for item in words_result])
                    return text
            else:
                raise Exception(f"Http Request Error\nHttp Status: {response.status_code}\n{response.text}")

    def write_config(self):
        with open(filename, 'w') as file:
            config.write(file)

def main():
    default_config = dict(config.items('default'))
    ocr = BaimiaoOCR(default_config)
    data = "base64_image"
    recognized_text = ocr.recognize(data)
    print(recognized_text)


if __name__ == '__main__':
    main()


