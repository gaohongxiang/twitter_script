"""
adspower api : http://apidoc.adspower.net/localapi/local-api-v1.html
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import pandas as pd
import numpy as np
import requests,os,sys,time,math,json
sys.path.append(os.getcwd()) # 工作目录
from config import *
from formatdata import *

def create_or_update_browser(browser_os='mac', is_create=True, browser_id=''):
    """创建或者修改浏览器信息
        
    Attributes:
        browser_os: 基于什么系统生成或修改浏览器。最好跟自己主机一致。 mac | windows
        is_create: 是否为创建 True创建 | False修改
        browser_id: 浏览器id。is_create为False时设置。默认空
    """
    # 操作系统
    if browser_os in ['mac','macos']:
        browser_os = ['All macOS']
    elif browser_os in ['win','windows']:
        browser_os = ['All Windows']
    
    body = {
        'group_id': '0', # 添加到对应分组的ID，未分配分组则可以传0
        'user_proxy_config': { # 账号代理配置
            "proxy_soft":"no_proxy", # 先不设置代理。可在修改代理接口去设置
        },
        'fingerprint_config': { # 账号指纹配置
            'browser_kernel_config': { # version:内核版本
                "version": "latest", # ”92“为92版内核、”99“为99版内核、”latest“为智能匹配；
                "type":"chrome", # 浏览器类型，chrome | firefox
            },
            'random_ua': { # 支持指定类型、系统、版本设置ua。若同时传入了自定义ua，则优先使用自定义的ua。
                'ua_system_version': browser_os, # 非必填，不填默认在所有系统中随机，支持 Android, iOS, Windows, Mac OS X , Linux。
                'ua_version': [], # 非必填，支持当前主流版本，不填默认在所有版本中随机 100 101 ...。
            },
            'ua': '', # user-agent用户信息，默认不传使用随机ua库，自定义需要确保ua格式与内容符合标准
            'automatic_timezone': 0, # 1 基于IP自动生成对应的时区(默认)；0 指定时区'
            'timezone': 'Asia/Shanghai', # 上海
            'webrtc': 'proxy', # proxy 替换,使用代理IP覆盖真实IP,代理场景使用 | local真实,网站会获取真实IP | disabled禁用(默认),网站会拿不到IP
            'location':	'ask',	# 网站请求获取您当前地理位置时的选择.询问ask(默认)，与普通浏览器的提示一样 | 允许allow，始终允许网站获取位置 | 禁止block，始终禁止网站获取位置
            'location_switch': 1, # 1 基于IP自动生成对应的位置(默认) | 0 指定位置	
            'longitude': '', # 指定位置的经度，指定位置时必填，范围是-180到180，支持小数点后六位	
            'latitude': '',	# 指定位置的纬度，指定位置时必填，范围是-90到90，支持小数点后六位	
            'accuracy': '',	# 指定位置的精度(米) ，指定位置时必填，范围10-5000，整数	
            'language': ["en-US","en","zh-CN","zh"], # 浏览器的语言(默认["en-US","en"])，支持传多个语言，格式为字符串数组	
            'language_switch': 0, # 基于IP国家设置语言，0：关闭 | 1：启用
        }
    }
    if is_create == False:
        if browser_id == '':
            print('请传入browser_id')
            return
        data = json.loads(body)
        data['user_id'] = browser_id
        body = json.dumps(data)
    url = f"{adspower_url}/api/v1/user/create" if is_create == True else f"{adspower_url}/api/v1/user/update"
    response = requests.post(url=url, json=body).json()
    if response['code'] != 0:
        tips = '创建浏览器信息失败:' if is_create == True else '修改浏览器信息失败:'
        print(tips, response["msg"])
        return
    print(response)
    time.sleep(1) # api速率限制。添加等待

def update_proxy(browser_id, index_id, proxy_ip, proxy_port, proxy_username, proxy_password):
    """修改浏览器代理
    Attributes:
        browser_id: 浏览器id
        index_id: 序号
        proxy_ip: 代理主机
        proxy_port: 代理端口
        proxy_username: 代理账号
        proxy_password: 代理密码
    """
    data = {
        'user_id': browser_id,
        'user_proxy_config': {
            "proxy_soft":"other",
            "proxy_type":"socks5",
            "proxy_host":proxy_ip,
            "proxy_port":proxy_port,
            "proxy_user":proxy_username,
            "proxy_password":proxy_password
        }
    }
    response = requests.post(url=f"{adspower_url}/api/v1/user/update", json=data).json()
    if response['code'] != 0:
        print('修改代理失败', response["msg"]) 
        return
    print('第',index_id,'个账号修改代理成功')
    time.sleep(1) # api速率限制。添加等待

class AdsPowerUtil():
    """selenium操作adspower指纹浏览器
    """

    def __init__(self, browser_id):
        """启动浏览器(webdriver为adspower自带的,不必单独下载)

        Attributes:
            browser_id:adspower浏览器id
        """
        self.browser_id = browser_id
        # 打开浏览器
        self.driver = self.open()
        # 全屏
        self.driver.maximize_window()
        # 关闭其他窗口
        self.close_other_windows()

    def open(self):
        response = requests.get(f"{adspower_url}/api/v1/browser/start?user_id={self.browser_id}").json()
        if response["code"] != 0:
            print("please check browser_id", response["msg"])
            return
        # 启动浏览器后在返回值中拿到对应的Webdriver的路径response["data"]["webdriver"]
        chrome_driver = Service(str(response["data"]["webdriver"]))
        # selenium启动的chrome浏览器是一个空白的浏览器。chromeOptions是一个配置chrome启动属性的类，用来配置参数。
        chrome_options = webdriver.ChromeOptions()
        # adspower提供的debug接口,用于执行selenium自动化
        chrome_options.add_experimental_option("debuggerAddress", response["data"]["ws"]["selenium"])
        driver = webdriver.Chrome(service=chrome_driver, options=chrome_options)
        return driver

    def close_other_windows(self):
        """关闭无关窗口，只留当前窗口
        理论上下面代码会保留当前窗口，句柄没错。但是实际窗口却没有达到预期。不清楚具体原因。后续再研究。目前能做到的就是只保留一个窗口
        """
        current_handle = self.driver.current_window_handle
        all_handles = self.driver.window_handles
        for handle in all_handles:
            self.driver.switch_to.window(handle)
            if handle != current_handle:
                self.driver.close()
        self.driver.switch_to.window(current_handle)     

    def quit(self):
        """关闭浏览器
        """
        response = requests.get(f"{adspower_url}/api/v1/browser/stop?user_id={self.browser_id}")
        if response['code'] != 0:
            print('关闭失败', response['msg'])

if __name__ == '__main__':

    # # 创建浏览器
    # for i in range(10):
    #     # 参数：browser_os='mac', is_create=True, browser_id=''
    #     create_or_update_browser(browser_os='mac', is_create=True, browser_id='')
    # exit()


    data = my_format_data(start_num=1, end_num=3, is_bitbrowser=False)


    # 修改代理ip（socks5）
    for d in data:
        # 参数：browser_id, proxy_ip, proxy_port, proxy_username, proxy_password
        update_proxy(browser_id=d['browser_id'], index_id=d['index_id'], proxy_ip=d['proxy_ip'], proxy_port=d['proxy_port'], proxy_username=d['proxy_username'], proxy_password=d['proxy_password'])
    exit()



    # for d in data:
    #     print(d)
    #     adspower = AdsPowerUtil(d['browser_id'])

