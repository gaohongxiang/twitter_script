"""
bitbrowser api : https://doc.bitbrowser.cn/api-jie-kou-wen-dang/liu-lan-qi-jie-kou
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
import requests,os,sys,time,math,json
sys.path.append(os.getcwd()) # 工作目录
from config import *
from formatdata import *
from utils import try_except_code

@try_except_code
def create_or_update_browser(browser_os='mac', browser_id=''):
    """创建或者修改浏览器窗口

    Attributes:
        browser_os:操作系统,影响ua值。最好跟本机操作系统相同。
        browser_id:bitbrowser浏览器id。此参数空值时代表创建浏览器。有值时代表修改浏览器信息
    returns:
        browser_id:浏览器id
    """
    # 操作系统
    if browser_os in ['mac','macos']:
        browser_os = 'MacIntel'
    elif browser_os in ['win','windows']:
        browser_os = 'Win32'

    body = {  
        'id': browser_id, # 有值时为修改，无值是添加
        'platform': 'https://www.google.com',  # 账号平台
        'platformIcon': 'other',  # 取账号平台的 hostname 或者设置为other
        'workbench': 'localServer', # 浏览器窗口工作台页面。chuhai2345(默认)|localServer|disable
        'proxyMethod': 2,  # 代理类型 1平台 2自定义
        # 'agentId': '', # proxyMethod为1时，平台代理IP的id
        # 自定义代理类型 ['noproxy', 'http', 'https', 'socks5', '911s5']
        'proxyType': 'noproxy', # 先不设置代理。可在修改代理接口去设置
        "browserFingerPrint": {
            'coreVersion': '104',  # 内核版本，默认104，可选92
            'ostype': 'PC',  # 操作系统平台 PC | Android | IOS
            'version': '', # 浏览器版本，建议92以上，不填则会从92以上版本随机
            'os': browser_os,  # 为navigator.platform值 Win32 | Linux i686 | Linux armv7l | MacIntel
            'userAgent': '', # ua，不填则自动生成
            'isIpCreateTimeZone': False,  # 基于IP生成对应的时区
            'timeZone': 'GMT+08:00',  # 时区，isIpCreateTimeZone 为false时，参考附录中的时区列表
            'position': '1',  # 网站请求获取您当前位置时，是否允许 0询问|1允许|2禁止。
            'isIpCreatePosition': True,  # 是否基于IP生成对应的地理位置
            'lat': '',  # 经度 isIpCreatePosition 为false时设置
            'lng': '',  # 纬度 isIpCreatePosition 为false时设置
            'precisionData': '',  # 精度米 isIpCreatePosition 为false时设置
            'isIpCreateLanguage': False,  # 是否基于IP生成对应国家的浏览器语言                                                                             
            'languages': 'zh-CN',  # isIpCreateLanguage 为false时设置，值参考附录
            'isIpCreateDisplayLanguage': False,  # 是否基于IP生成对应国家的浏览器界面语言
            'displayLanguages': '',  # isIpCreateDisplayLanguage 为false时设置，默认为空，即跟随系统，值参考附录
            'WebRTC': 0, # 0替换(默认)|1允许|2禁止。开启WebRTC，将公网ip替换为代理ip，同时掩盖本地ip
        }
    }

    response = requests.post(f"{bitbrowser_url}/browser/updat", json=body)
    response.raise_for_status()
    response = response.json()
    browser_id = response['data']['id']
    print('创建或修改浏览器成功,浏览器id为:', browser_id)

@try_except_code
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
    body = {
        'ids': [browser_id],
        'ipCheckService': '', # IP查询渠道，默认ip-api
        'proxyMethod': 2,  # 代理类型 1平台 2自定义
        'proxyType': 'socks5',
        'host': proxy_ip,  # 代理主机
        'port': proxy_port,  # 代理端口
        'proxyUserName': proxy_username, # 代理账号
        'proxyPassword': proxy_password, # 代理密码
        'isIpv6': False, # 默认false
    }
    response = requests.post(f"{bitbrowser_url}/browser/proxy/update", json=body)
    response.raise_for_status()
    print('第',index_id,'个账号修改代理成功')

class BitBrowserUtil():
    """selenium操作adspower指纹浏览器
    """

    @try_except_code
    def __init__(self, browser_id):
        """启动浏览器(webdriver为自带的,不必单独下载)

        Attributes:
            browser_id:bitbrowser浏览器id
        """
        self.browser_id = browser_id
        # 打开浏览器
        self.driver = self.open()
        # 全屏
        self.driver.maximize_window()
        # 关闭其他窗口
        self.close_other_windows()

    @try_except_code
    def open(self):
        body = {'id': self.browser_id}
        response = requests.post(f"{bitbrowser_url}/browser/open", json=body)
        response.raise_for_status()
        response = response.json()
        # 启动浏览器后在返回值中拿到对应的driver的路径
        chrome_driver = Service(str(response["data"]["driver"]))
        # selenium启动的chrome浏览器是一个空白的浏览器。chromeOptions是一个配置chrome启动属性的类，用来配置参数。
        chrome_options = webdriver.ChromeOptions()
        # adspower提供的debug接口,用于执行selenium自动化
        chrome_options.add_experimental_option("debuggerAddress", response["data"]["http"])
        driver = webdriver.Chrome(service=chrome_driver, options=chrome_options)
        return driver
        
    @try_except_code
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

    @try_except_code
    def quit(self):
        """关闭浏览器
        """
        body = {'id': self.browser_id}
        response = requests.post(f"{bitbrowser_url}/browser/close", json=body)
        response.raise_for_status()

if __name__ == '__main__':

    # # 创建浏览器
    # for i in range(20):
    #     create_or_update_browser(browser_os='mac', browser_id='')
    # exit()



    data = my_format_data(start_num=1, end_num=20, is_bitbrowser=True)
    # print(data)



    # # 修改代理ip（socks5）
    # for d in data:
    #     # 参数：browser_id, index_id, proxy_ip, proxy_port, proxy_username, proxy_password)
    #     update_proxy(browser_id=d['browser_id'], index_id=d['index_id'], proxy_ip=d['proxy_ip'], proxy_port=d['proxy_port'], proxy_username=d['proxy_username'], proxy_password=d['proxy_password'])
    # exit()



    # for d in data:
    #     bitbrowser = BitBrowserUtil(d['browser_id'])
