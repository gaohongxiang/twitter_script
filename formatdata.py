import pandas as pd
import os,sys
sys.path.append(os.getcwd()) # 工作目录
from config import *
from utils.utils import try_except_code

# 组装数据
@try_except_code
def my_format_data(start_num, end_num, is_bitbrowser=True):
    """组装数据
        
    Attributes:
        start_num:开始账号
        end_num:结束账号
        is_bitbrowser:是否为比特浏览器数据 True:比特浏览器 False:ads浏览器
    """
    if int(start_num) <= 0 or int(end_num) <= 0:
        print('账号必须大于0')
        return
    if int(start_num) > int(end_num):
        print('开始账号必须小于或等于结束账号')
        return
    # 浏览器数据
    if is_bitbrowser == True:
        all_browser = pd.read_excel(bitbrowser_file)
        all_browser = all_browser.sort_values(by='序号', ascending=True) # 按序号升序排列
        all_browser = all_browser.reset_index(drop=True) # 放弃原来datafarm序号
        all_browser = all_browser[['序号', 'ID', 'User Agent']]
        all_browser = all_browser.rename(columns={'序号': 'index_id', 'ID': 'browser_id', 'User Agent': 'user_agent'})
    else:
        all_browser = pd.read_excel(adspower_file)
        all_browser = all_browser.sort_values(by='acc_id', ascending=True) # 按acc_id升序排列
        all_browser = all_browser.reset_index(drop=True) # 放弃原来datafarm序号
        all_browser = all_browser[['acc_id', 'id', 'ua']]
        all_browser = all_browser.rename(columns={'acc_id': 'index_id', 'id': 'browser_id', 'ua': 'user_agent'})
    # ip数据
    all_ip = pd.read_csv(ip_file, sep=':', engine='python')
    all_ip['proxy'] = "socks5://" + all_ip['proxy_username'] +":" + all_ip['proxy_password'] +"@" + all_ip['proxy_ip'] +":" + all_ip['proxy_port'].map(str)
    # twitter数据 
    all_twitter = pd.read_csv(twitter_file, sep='|', engine='python')
    
    data = pd.merge(left=all_browser,right=all_ip,left_index=True,right_index=True,how='inner')
    data = pd.merge(left=data,right=all_twitter,left_index=True,right_index=True,how='inner')

    data = data.iloc[int(start_num)-1:int(end_num),:].reset_index(drop=True)
    data = data.to_dict('records')
    return data

@try_except_code
def my_twitter_data():
    """所有twitter账号数据。数组
    """
    all_twitter = pd.read_csv(twitter_file, sep='|', engine='python')
    # 将DataFrame数据转换为数组
    my_twitter_data = all_twitter['twitter_username'].tolist()
    return my_twitter_data

if __name__ == '__main__':

    my_format_data = my_format_data(1, 20, is_bitbrowser=True)
    print(my_format_data)

    my_twitter_data = my_twitter_data()
    print(my_twitter_data)
