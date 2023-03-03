import tweepy
import urllib.parse
import json, requests, random, datetime, time, pytz
import sys, os
from dateutil.parser import parse as date_parse
sys.path.append(os.getcwd()) # 工作目录
from browser.bitbrowser import *
# from browser.adspower import *
from config import *
from formatdata import *

class OAuth2ForTwitterUtil(BitBrowserUtil):
    """身份验证,获取refresh_token备用
    """
    def __init__(self, browser_id):
        super(OAuth2ForTwitterUtil, self).__init__(browser_id)

    def create_refresh_token(self, account):
        data = json.load(open(refresh_tokens_file,'r',encoding="utf-8"))
        oauth2_user_handler = tweepy.OAuth2UserHandler(
            client_id=client_id,
            redirect_uri=redirect_uri,
            # 只有在使用机密客户时，才需要client_secret
            # client_secret="data['client_secret']",
            # 加offline.access会生成refresh_token
            scope=[
                "offline.access",
                "tweet.read",
                "tweet.write",
                "users.read",
                "follows.read",
                "follows.write",
                "like.read",
                "like.write",
                "list.read",
                "list.write"],
        )
        auth_url = oauth2_user_handler.get_authorization_url()
        self.driver.get(auth_url)
        try:
            # 不知为啥click()不生效，用send_keys(Keys.ENTER)代替
            WebDriverWait(self.driver,10).until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/main/div/div/div[2]/div/div/div[1]/div[3]/div"))).send_keys(Keys.ENTER)
            time.sleep(5)
            response_url = self.driver.current_url
            # print(response_url)
        except Exception as e:
            print(e)
        result = oauth2_user_handler.fetch_token(response_url)
        if 'error' in result:
            print(result['error_description'])
            return
        new_refresh_token = {account: result['refresh_token']}
        with open(refresh_tokens_file, 'r') as f:
            data = json.load(f)
            refresh_token = {**data, **new_refresh_token}
            data.update(refresh_token)
        with open(refresh_tokens_file, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
class TwitterUtil():

    def __init__(self, account, ua, proxy):
        """获取授权,调用twitter api
        提示: tweepy通过access_token而不是通过refresh_token内部处理成access_token来初始化。access_token有效期2小时,不可能过期了再通过用户授权的方式来请求,效率低.另外refresh_token不会过期,
        所以还是需要存refresh_token.twitter奇怪的点是通过refresh_token获取access_token时refresh_token也会变,所以存储的refreshtoken得跟着修改,google的refresh_token就不会变
        通过refresh_token获得access_token和新的refresh_token是用twitter的api实现的不是tweepy的库实现的
        """
        data = json.load(open(refresh_tokens_file,'r',encoding="utf-8"))
        # tweepy目前没有方法通过refresh_token来刷新access_token。
        # 通过refresh_token跟twitter API端点交互，获取新的refresh_token和access_token。
        url = 'https://api.twitter.com/2/oauth2/token'
        headers ={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": ua
            }
        playlod = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": data[account], 
            "client_id": client_id
        })
        proxies = {"http": proxy, "https": proxy}
        response = requests.post(url=url, headers=headers, data=playlod, proxies=proxies)
        # byte.decode('UTF-8')将byte转换成str，json.load将str转换成dict
        result = json.loads((response.content).decode('UTF-8'))
        if 'error' in result:
            print(result['error_description'])
            return
        new_refresh_token = {account: result['refresh_token']}
        with open(refresh_tokens_file, 'r') as f:
            data = json.load(f)
            refresh_token = {**data, **new_refresh_token}
            data.update(refresh_token)
        with open(refresh_tokens_file, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # 使用新的 access_token 进行 API 调用
        self.client = tweepy.Client(bearer_token=result['access_token'])
        # 设置代理
        self.client.session.proxies = proxies
        self.account = account

    def get_account(self):
        """获取验证账户的信息
        """
        account_info = self.client.get_me(user_auth=False)
        account_id = account_info.data.id
        account_username = account_info.data.username
        account = {'account_id':account_id, 'account_username':account_username}
        return account

    def get_user_id_from_username(self, username):
        """通过用户名获取用户唯一id
        """
        data = self.client.get_user(username=username)
        # 获取用户的twitter id
        user_id = data.data.id
        return user_id

    def get_user_followers(self, user_id, num=None):
        """获取用户的关注者

        Attributes:
            user_id:用户id
            num:获取用户跟随者的数量。默认None,获取所有的跟随者
        """
        if num is not None and type(num) != int:
            print('数量必须是整数')
            return
        followers = []
        args = {
            "id": user_id,
            "max_results": 100 #一页最大返回数量。1-1000，默认100
        }
        for page in tweepy.Paginator(self.client.get_users_followers, **args):
            if not page.data:
                print('此用户没有关注别人')
                break
            if num != None:
                if len(followers) >= num:
                    break
            for user in page.data:
                if num != None:
                    if len(followers) >= num:
                        break
                user_id = user.id
                user_name = user.username
                followers.append({'user_id':user_id, 'user_name':user_name})
        # print(followers)
        # print(len(followers))
        return followers

    def get_user_followings(self, user_id, num=None):
        """获取用户关注的人

        Attributes:
            user_id:用户id
            num:获取用户跟随的人的数量。默认None,获取所有的跟随的人
        """
        if num is not None and type(num) != int:
            print('数量必须是整数')
            return
        followings = []
        for page in tweepy.Paginator(self.client.get_users_following, id=user_id):
            if not page.data:
                print('此用户没有关注者')
                break
            if num != None:
                if len(followings) >= num:
                    break
            for user in page.data:
                if num != None:
                    if len(followings) >= num:
                        break
                user_id = user.id
                user_name = user.username
                followings.append({'user_id':user_id, 'user_name':user_name})
        # print(followings)
        # print(len(followings))
        return followings
    
    def follow(self, user_id):
        """关注别人
        """
        self.client.follow_user(user_id, user_auth=False)
       
    def unfollow(self, user_id):
        """取消关注别人
        """
        self.client.unfollow_user(user_id, user_auth=False)

    def create_tweet(self):
        """创建推文
        """
        # 获取推文话术
        with open(tweet_texts_file) as f:
            tweet_texts = f.read().splitlines()
        tweet_text = random.choice(tweet_texts)
        self.client.create_tweet(text=tweet_text, user_auth=False)
        print('推文已发')

    def reply(self, tweet_id, tem_reply_text='', is_use_reply_file=True):
        """评论推文。

         Attributes:
            tweet_id: 回复的推文id
            tem_reply_text: 临时回复内容。比如需要@几个好友；互关贴回复#互关标签等。
            is_use_reply_file:是否使用回复话术文件。平时养号没有啥特殊要求，从文件中随机选取一条回复即可
        """
        if type(tem_reply_text) != str:
            print("回复话术或文件路径必须是字符串")
            return
        if is_use_reply_file == True:
            with open(reply_texts_file) as f:
                reply_texts = f.read().splitlines()
                random_reply_text = random.choice(reply_texts)
            if len(tem_reply_text) != 0:
                reply_text = random_reply_text + '\n' + tem_reply_text
            else:
                reply_text = random_reply_text
        else:
            if len(tem_reply_text) != 0:
                reply_text = tem_reply_text
            else:
                print('请输入回复话术')
            
        self.client.create_tweet(in_reply_to_tweet_id=tweet_id, text=reply_text, user_auth=False)

    def delete_tweet(self, tweet_id):
        """删除推文
        """
        self.client.delete_tweet(id=tweet_id, user_auth=False)

    def like(self, tweet_id):
        """喜欢推文
        """
        self.client.like(tweet_id, user_auth=False)
    
    def unlike(self, tweet_id):
        """取消喜欢推文
        """
        self.client.unlike(tweet_id, user_auth=False)

    def retweet(self, tweet_id):
        """转发推文
        """
        self.client.retweet(tweet_id, user_auth=False)
    
    def unretweet(self, tweet_id):
        """取消转发推文
        """
        self.client.unretweet(source_tweet_id=tweet_id, user_auth=False)

    def parse_time(self, start_time, end_time):
        """将时间解析为twitter要求的iso时间。注意:tweepy接口时间为utc时间。为了方便此函数传递的时间为utc+8时间
        
        Attributes:
            start_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。开始日期,返回此日期之后的推文
            end_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。结束日期,返回此日期之前的推文。默认值None,表示当前时间
        """
        try:
            tz = pytz.timezone('Asia/Shanghai')
            # 构造开始时间
            if start_time is None: # 如果start_time为None，则代表从无限早时间开始查询。
                start_time_iso = date_parse('1977-01-01 00:00:00').strftime("%Y-%m-%dT%H:%M:%SZ")
            elif type(start_time) == int: # 如果start_time为整数，则代表从start_time天前开始查询。
                start_time_iso = (datetime.datetime.utcnow() - datetime.timedelta(days=start_time)).strftime("%Y-%m-%dT%H:%M:%SZ")
            else: # 如果start_time为时间类型，则代表从此时间结束查询。
                start_time_utc8 = tz.localize(date_parse(start_time))  # 将字符串解析为datetime对象，并将其设置为UTC+8时间
                start_time_utc = start_time_utc8.astimezone(pytz.utc)  # 将UTC+8时间转换为UTC时间
                start_time_iso = start_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
                        
            # 构造结束时
            if end_time is None: # 如果end_time为None，则代表当前时间结束查询。
                end_time_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            elif type(end_time) == int: # 如果end_time为整数，则代表从start_time天前结束查询。
                end_time_iso = (datetime.datetime.utcnow() - datetime.timedelta(days=end_time)).strftime("%Y-%m-%dT%H:%M:%SZ")
            else: # 如果end_time为时间类型，则代表从此时间结束查询。
                end_time_utc8 = tz.localize(date_parse(end_time))  # 将字符串解析为datetime对象，并将其设置为UTC+8时间
                end_time_utc = end_time_utc8.astimezone(pytz.utc)  # 将UTC+8时间转换为UTC时间
                end_time_iso = end_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # 开始时间必须比结束时间要早
            if start_time_iso >= end_time_iso:
                print('开始时间必须小于结束时间')
                return
            return start_time_iso, end_time_iso
        except Exception as e:
            print('错误信息',e,'\n时间只允许整数类型或者YYYY-MM-DD HH:mm:ss类型')
            return

    def get_home_timeline(self, start_time, end_time=None):
        """允许您检索您和您关注的用户发布的最新推文和转推的集合。此端点最多返回最后 3200 条推文。

        Attributes:
            start_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。开始日期,返回此日期之后的推文
            end_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。结束日期,返回此日期之前的推文。默认值None,表示当前时间
        
        return:
            tweets: 推文信息,包含id、text、author_id、author_username、follows_count、llike_count
        """
        tweets = []
        start_time_iso, end_time_iso = self.parse_time(start_time, end_time)
        args = {
            'start_time': start_time_iso,
            'end_time': end_time_iso,
            'expansions': ['author_id'],
            'tweet_fields': ['author_id', 'created_at', 'public_metrics', 'entities', 'conversation_id'],
            'user_fields': ['public_metrics', 'entities', 'username'],
            'user_auth': False
        }
        for page in tweepy.Paginator(self.client.get_home_timeline, **args):
            if not page.data:
                break
            for tweet in page.data:
                tweet_id = tweet.id
                tweet_author_id = tweet.author_id
                tweet_text = tweet.text
                for user in page.includes['users']:
                    if user.id == tweet_author_id:
                        tweet_author_username = user.username
                        tweets.append({'tweet_id': tweet_id, 'tweet_author_id': tweet_author_id, 'tweet_author_username': tweet_author_username, 'tweet_text': tweet_text})
        # print(tweets)
        return tweets
        
    def get_user_tweets(self, username, start_time, end_time=None):
        """允许您检索指定的单个用户组成的推文。最多返回最近的 3200 条推文。

        Attributes:
            username: 用户名
            start_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。开始日期,返回此日期之后的推文
            end_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。结束日期,返回此日期之前的推文。默认值None,表示当前时间
        return:
            tweets: 推文信息
        """
        tweets = []
        start_time_iso, end_time_iso = self.parse_time(start_time, end_time)
        user_id = self.get_user_id_from_username(username)
        args = {
            'id': user_id,
            'start_time': start_time_iso,
            'end_time': end_time_iso,
            'max_results': 50, #一页最大返回数量。5-100，默认10
            'expansions': ['author_id'],
            'tweet_fields': ['author_id', 'created_at', 'public_metrics', 'entities', 'conversation_id'],
            'user_auth': False
        }
        for page in tweepy.Paginator(self.client.get_users_tweets, **args):
            if not page.data:
                break
            for tweet in page.data:
                tweet_id = tweet.id
                tweet_author_id = tweet.author_id
                tweet_text = tweet.text
                tweets.append({'tweet_id': tweet_id, 'tweet_author_id': tweet_author_id, 'tweet_text': tweet_text})
        # print(tweets)
        return tweets

    def get_tweet(self, tweet_id):
        """检索指定推文信息

        Attributes:
            tweet_id: 推文id
        return:
            tweets: 推文信息
        """
        tweets = []
        args = {
            'id': tweet_id,
            'expansions': ['author_id'],
            'tweet_fields': ['author_id', 'created_at', 'public_metrics', 'entities', 'conversation_id'],
            'user_fields': ['username', 'created_at'],
            'user_auth': False
        }
        response = self.client.get_tweet(**args)
        tweet_author_id = response.data.author_id
        tweet_text = response.data.text
        # 推文提及的人
        tweet_mentions_id = []
        if 'mentions' in response.data.entities.keys():
            for mention in response.data.entities['mentions']:
                mention_id = mention['id']
                tweet_mentions_id.append(mention_id)
        for user in response.includes['users']:
            tweet_author_username = user.username
        tweet = {
            'tweet_id': tweet_id,
            'tweet_author_id': tweet_author_id,
            'tweet_author_username': tweet_author_username,
            'tweet_mentions_id': tweet_mentions_id,
            'tweet_text': tweet_text
            }
        # print(tweet)
        return tweet

    def get_tweet_replyers(self, tweet_id, replyer_amount=10, my_twitter_data=None):
        """检索指定推文的评论者

        Attributes:
            tweet_id: 推文id
            replyer_amount: 获取的评论者数量
            my_twitter_data: 所有的账号信息。用于排除评论者中自己的小号
        return:
            tweets: 评论者信息
        """
        replyers = []
        tweet = self.get_tweet(tweet_id)
        tweet_author_username = tweet['tweet_author_username']
        args = {
            'query': f'conversation_id:{tweet_id}',
            'max_results': 50, #一页最大返回数量。10-100，默认10
            'expansions': ['author_id', 'in_reply_to_user_id', 'referenced_tweets.id'],
            'tweet_fields': ['author_id', 'created_at', 'public_metrics', 'entities', 'conversation_id', 'in_reply_to_user_id', 'referenced_tweets'],
            'user_fields': ['username', 'created_at'],
            'user_auth': False
        }
        for page in tweepy.Paginator(self.client.search_recent_tweets, **args):
            # print(page)
            if len(replyers) >= replyer_amount:
                break
            if 'users' in page.includes:
                for replyer in page.includes['users']:
                    if len(replyers) >= replyer_amount:
                        break
                    # 排除推文作者、根据my_twitter_data决定是否排除自己的小号
                    replyer_id = replyer.id
                    replyer_username = replyer.username
                    if my_twitter_data is None:
                        if replyer_username != tweet_author_username and replyer_username != self.account:
                            replyers.append({'replyer_id': replyer_id, 'replyer_username': replyer_username})
                    else:
                        if replyer_username != tweet_author_username and (replyer_username not in my_twitter_data):
                            replyers.append({'replyer_id': replyer_id, 'replyer_username': replyer_username})
            else:
                print('此推文没有评论')
        # print(replyers)
        return replyers

    def search_recent_tweets(self, query, start_time, end_time=None, search_amount=20, follows_count=1000, like_count=50):
        """返回过去 n 天内与搜索查询匹配的推文,最多7天

        Attributes:
            query: 搜索条件
            start_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。开始日期,返回此日期之后的推文
            end_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。结束日期,返回此日期之前的推文。默认值None,表示当前时间
            search_amount: 获取的推文数量, 获取太多没意义，反应也太慢
            follows_count: 推文作者的关注者数量
            like_count: 推文的喜欢数量
        return:
            twitters: 推文信息,包含id、text、author_id、author_username、follows_count、llike_count
        """
        tweets = []
        start_time_iso, end_time_iso = self.parse_time(start_time, end_time)
        # 开始时间必须在过去7天以内
        seven_time_iso = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if start_time_iso < seven_time_iso:
            print('最多查询过去7天的推文')
            return
        # 结束时间必须至少比请求时间早 10 秒
        current_time = (datetime.datetime.utcnow().replace(microsecond=0) - datetime.timedelta(seconds=10)) # replace(microsecond=0) 去掉毫秒信息
        end_time = date_parse(end_time_iso).replace(tzinfo=None) # replace(tzinfo=None)去掉时区信息
        if end_time > current_time:
            time_diff_seconds = int((end_time - current_time).total_seconds())
            end_time_iso = (date_parse(end_time_iso) - datetime.timedelta(seconds=time_diff_seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')

        # expansions: author_id,referenced_tweets.id,referenced_tweets.id.author_id,entities.mentions.username,attachments.poll_ids,attachments.media_keys,in_reply_to_user_id,geo.place_id
        # tweet_fields: attachments,author_id,context_annotations,conversation_id,created_at,entities,geo,id,in_reply_to_user_id,lang,non_public_metrics,organic_metrics,possibly_sensitive,promoted_metrics,public_metrics,referenced_tweets,reply_settings,source,text,withheld
        # entities是推文提到的实体，里面可能包含urls（推文提到的url）、mentions（推文提到的用户）
        # user_fields: created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,withheld
        args = {
            'query': query,
            'max_results': 50, # 一页最大返回数量。10-100，默认10
            'start_time': start_time_iso,
            'end_time': end_time_iso,
            'expansions': ['author_id'],
            'tweet_fields': ['author_id', 'created_at', 'public_metrics', 'entities', 'conversation_id'],
            'user_fields': ['public_metrics', 'entities', 'username'],
            'user_auth': False
        }
        for page in tweepy.Paginator(self.client.search_recent_tweets, **args):
            # print(page)
            if len(tweets) >= search_amount:
                break
        # page.data包括默认的id（twitter的id）、text（twitter内容）和author_id（发推文的作者id）、created_at(发推文的时间)、public_metrics（推文点赞数量、转推数量、回复数量、引用数量等信息）
        # page.includes['users']包括默认的id（发推文的作者id）、username（发推文的作者用户名）、name（发推文的作者昵称）和public_metrics（作者的关注者、被关注者、发布的推文数量等信息）
            if not page.data:
                break
            for tweet in page.data:
                # print(tweet)
                if len(tweets) >= search_amount:
                    break
                tweet_id = tweet.id
                # 推文的对话线程id，用于获取回复推文信息。当发布推文以响应推文（称为回复）或回复时，现在每个回复都有一个定义的 conversation_id，它与开始对话的原始推文的推文 ID 相匹配。https://developer.twitter.com/en/docs/twitter-api/conversation-id
                tweet_conversation_id = tweet.conversation_id
                tweet_text = tweet.text
                tweet_author_id = tweet.author_id
                # print(tweet_author_id)
                # print(tweet.public_metrics)
                tweet_like_count = tweet.public_metrics['like_count']
                tweet_mentions_id = []
                if 'mentions' in tweet.entities.keys():
                    for mention in tweet.entities['mentions']:
                        mention_id = mention['id']
                        tweet_mentions_id.append(mention_id)
                for author in page.includes['users']:
                    if author.id == tweet_author_id:
                        # print(author.public_metrics)
                        tweet_author_username = author.username
                        tweet_author_followers_count = author.public_metrics['followers_count']
                        if tweet_author_followers_count >= follows_count and tweet_like_count >= like_count:
                            tweets.append({
                                'tweet_id':tweet_id,
                                'tweet_text':tweet_text,
                                'tweet_like_count':tweet_like_count,
                                'tweet_author_id':tweet_author_id,
                                'tweet_author_username': tweet_author_username,
                                'tweet_author_followers_count':tweet_author_followers_count,
                                'tweet_mentions_id': tweet_mentions_id,
                                'tweet_conversation_id': tweet_conversation_id})
        # print(tweets)
        return tweets

    def giveaway(self, query, start_time, end_time=None, search_amount=20, follows_count=1000, like_count=50, tag_amount=3, is_use_reply_file=True, is_like=True, is_retweet=True, is_reply=True):
        """养号、抽奖

        根据指定搜索条件，搜索出指定时间内，推文作者满足一定关注量、推文满足一定点赞数的指定数量的推文。从中选择指定数量条推文进行关注、点赞、转推、评论（随机评论话术）操作，每条推文操作间隔指定时间。

        Attributes:
            query: 搜索条件
            start_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。开始日期,返回此日期之后的推文
            end_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。结束日期,返回此日期之前的推文。默认值None,表示当前时间
            search_amount:获取的推文数量，获取太多没意义，反应也太慢
            follows_count: 推文作者的关注者数量
            like_count: 推文的喜欢数量
            tag_amount: 要标记的朋友数量
            is_use_reply_file: 是否使用回复文件里的话术
            is_like: 是否点赞
            is_retweet: 是否转推
            is_reply: 是否回复
        """
        try:
            # 获取验证账户的追随者
            account = self.get_account()
            account_id = account['account_id']
            all_followers = self.get_user_followers(account_id, num=tag_amount)
            if len(all_followers) < tag_amount:
                print('账户',account['account_username'],'关注者不够')
                return
            # 获取推文query, start_time, end_time=None, search_amount=20, follows_count=1000, like_count=50
            tweets = self.search_recent_tweets(query=query, start_time=start_time, end_time=end_time, search_amount=search_amount, follows_count=follows_count, like_count=like_count)
            # 随机选择一条推文
            tweet = random.choice(tweets)
            # print(tweet)
            # 关注推文作者
            self.follow(tweet['tweet_author_id'])
            time.sleep(1)
            # 关注推文提到的实体
            if tweet['tweet_mentions_id'] != []:
                for mention_id in tweet['tweet_mentions_id']:
                    # 作者不要重复关注
                    if mention_id != tweet['tweet_author_id']:
                        self.follow(mention_id)
                        time.sleep(1)
            if is_like == True:
                # 喜欢
                self.like(tweet['tweet_id'])
                time.sleep(1)
            if is_retweet == True:
                # 转推
                self.retweet(tweet['tweet_id'])
                time.sleep(1)
            if is_reply == True:
                # 评论并@tag_amount个朋友
                follows = ''
                if len(all_followers) > 0:
                    for follower in all_followers:
                        follows = '@'+follower['user_name'] + ' ' + follows
                self.reply(tweet['tweet_id'], tem_reply_text=follows, is_use_reply_file=is_use_reply_file)
            print('已三连')
        except Exception as e:
            print(e)  

    def giveaway_from_fix_tweet(self, tweet_id, tag_amount=3, is_use_reply_file=True, is_like=True, is_retweet=True, is_reply=True):
        """指定推文抽奖

        Attributes:
            tweet_id: 操作的推文id
            tag_amount: 要标记的朋友数量
            is_use_reply_file: 是否使用回复文件里的话术
            is_like: 是否点赞
            is_retweet: 是否转推
            is_reply: 是否回复
        """
        try:
            # 获取验证账户的追随者
            account = self.get_account()
            account_id = account['account_id']
            all_followers = self.get_user_followers(account_id, num=tag_amount)
            if len(all_followers) < tag_amount:
                print('账户',account['account_username'],'关注者不够')
                return
            # 获取推文信息
            tweet = self.get_tweet(tweet_id)
            # 关注推文作者
            self.follow(tweet['tweet_author_id'])
            time.sleep(1)
            # 关注推文提到的实体
            if tweet['tweet_mentions_id'] != []:
                for mention_id in tweet['tweet_mentions_id']:
                    # 作者不要重复关注
                    if mention_id != tweet['tweet_author_id']:
                        self.follow(mention_id)
                        time.sleep(1)
            if is_like == True:
                # 喜欢
                self.like(tweet_id)
                time.sleep(1)
            if is_retweet == True:
                # 转推
                self.retweet(tweet_id)
                time.sleep(1)
            if is_reply == True:
                # 评论并@tag_amount个朋友
                follows = ''
                if len(all_followers) > 0:
                    for follower in all_followers:
                        follows = '@'+follower['user_name'] + ' ' + follows
                self.reply(tweet_id, tem_reply_text=follows, is_use_reply_file=is_use_reply_file)
            print('已三连')
        except Exception as e:
            print(e)  

    def set_follow_info(self, query, start_time, end_time=None, follows_count=1000, like_count=50, search_amount=20, to_follow_amount=10, my_twitter_data=None, tem_reply_text='诚信互关，有关必回\n#互关 #互粉  #互fo', is_use_reply_file=True):
        """去互关贴下发互关信息

        根据'互关'搜索条件，搜索出指定时间内，推文作者满足一定关注量、推文满足一定点赞数的指定数量的推文。从中选择一条推文进行转推、评论、关注评论者的操作。
        
        自己的小号不互关

        Attributes:
            query: 搜索条件
            start_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。开始日期,返回此日期之后的推文
            end_time: 格式:YYYY-MM-DD HH:mm:ss 例:2023-02-25 13:00:00。结束日期,返回此日期之前的推文。默认值None,表示当前时间
            follows_count: 推文作者的关注者数量
            like_count: 推文的喜欢数量
            search_amount:获取的推文数量，获取太多没意义，反应也太慢
            to_follow_amount: 要关注的人的数量(一次别关注太多,避免封控)，从推文的评论者中获取到的。实际获取到的数量<=这个数值(推文评论者太少的话就是小于这个数值)。
            my_twitter_data: 所有的账号信息。用于排除评论者中自己的小号
            tem_reply_text: 回复话术（部分）
            is_use_reply_file: 是否使用回复文件里的话术
        """
        try:
            # 通过query随机获取互关推文
            tweets = self.search_recent_tweets(query=query, start_time=start_time, end_time=None, search_amount=search_amount, follows_count=follows_count, like_count=like_count)
            # print(tweets)
            # 随机选择一条推文
            tweet = random.choice(tweets)
            # print(tweet)
            # 关注推文作者
            self.follow(tweet['tweet_author_id'])
            time.sleep(1)
            # 关注推文提到的实体（作者@的人）
            if tweet['tweet_mentions_id'] != []:
                for mention_id in tweet['tweet_mentions_id']:
                    # 作者不要重复关注
                    if mention_id != tweet['tweet_author_id']:
                        self.follow(mention_id)
                        time.sleep(1)
            # 关注推文评论者
            replyers = self.get_tweet_replyers(tweet['tweet_id'], replyer_amount=to_follow_amount, my_twitter_data=my_twitter_data)
            # print(replyers)
            if len(replyers) != 0:
                for replyer in replyers:
                    self.follow(replyer['replyer_id'])
                    time.sleep(1)
            # 转发此推文
            self.retweet(tweet['tweet_id'])
            time.sleep(1)
            # 回复此推文
            self.reply(tweet['tweet_id'], tem_reply_text=tem_reply_text, is_use_reply_file=is_use_reply_file)
            print('已关注、已转推、已发布互关信息')
        except Exception as e:
            print(e)

    def follow_back(self, my_twitter_data=None, once_follow_num=10):
        '''回关
        Attributes:
            my_twitter_data: 所有的账号信息。用于排除评论者中自己的小号
            once_follow_num: 关注几个人
        '''
        # 获取验证账户
        account = self.get_account()
        account_id = account['account_id']
        # 获取关注验证账户的人
        all_followers = self.get_user_followers(account_id)
        # print(all_followers)
        # 获取验证账户关注的人
        all_followings = self.get_user_followings(account_id)
        # print(all_followings)
        # 比较关注此账户的人和此账户关注的人。排除重复的人（彼此关注过了），关注此账户的人集合里剩下的人就是需要去关注的。
        # 将字典转换为元组，只保留字典中的"id"键
        followers_ids = set(tuple(follower["user_name"] for follower in all_followers))
        followings_ids = set(tuple(following["user_name"] for following in all_followings))
        # 执行集合操作
        intersection = followers_ids & followings_ids
        # 如果小号不互关的话，将自己的twitter账号全部添加进集合
        if my_twitter_data is not None:
            intersection |= set(my_twitter_data)
        # 排除重复的人（彼此关注过了），关注此账户的人集合里剩下的人就是需要去关注的
        need_followers = [follower for follower in all_followers if follower["user_name"] not in intersection]
        # print(need_followers)
        # 回关。设置最大关注数量，如果未关注的人太多，可能会被封控。这个可以慢慢回关
        num = len(need_followers)
        if num >= once_follow_num:
            for i in range(once_follow_num):
                need_follower = need_followers[i]
                self.follow(need_follower['user_id'])
                time.sleep(1)
            print('已回关',once_follow_num,'个账户')
        elif num > 0 and num < once_follow_num:
            for need_follow in need_followers:
                self.follow(need_follow['user_id'])
                time.sleep(1)
            print('已全部回关')
        elif num == 0:
            print('已全部回关')

if __name__ == '__main__':

    # 1、组装数据
    # 1,1代表第1个账号。2,2代表第二个账号。以此类推...
    # 1,20代表第1-20个账号。3,10代表第3-10个账号。以此类推...
    # 默认用比特浏览器。如果用ads浏览器需要把s_bitbrowser值改为False
    data = my_format_data(start_num=1, end_num=20, is_bitbrowser=True)
    # print(data)
    
    # 所有twitter账号
    my_twitter_data = my_twitter_data()
    # print(my_twitter_data)


    # # 2、程序第一次需要跟用户交互，来获取权限。会自动打开指纹浏览器（指纹app需要先打开），点击授权，只需要交互1次。自动将refresh_token保存备用。
    # # 将获取到的refresh_token保存在`twitter_credential_tokens.json`文件中。以后运行程序就不需要再跟用户交互了。程序自动使用refresh_token刷新accress_token来调用twitter api，并将自动更新文件中的refresh_token。
    # for d in data:   
    #     # 验证
    #     oauth2 = OAuth2ForTwitterUtil(d['browser_id']) 
    #     oauth2.create_refresh_token(d['twitter_username'])
    # exit()
        


    # 3、调用twitter api 处理业务
    for d in data:
        # print(d)
        # 实例化TwitterUtil
        twitter = TwitterUtil(d['twitter_username'], d['user_agent'], d['proxy'])

        # # 通过用户名获取用户id
        # user_id = twitter.get_user_id_from_username('gaohongxiang')
        # print(user_id)

        # # 获取用户的关注者、用户关注的人
        # twitter.get_user_followers(user_id)
        # twitter.get_user_followings(user_id)

        # # 关注别人
        # twitter.follow(user_id)

        # # 点赞转发评论
        # twitter.like('1555521594424004608')
        # twitter.retweet('1555521594424004608')
        # 参数tweet_id, tem_reply_text='', is_use_reply_file=True
        # twitter.reply('1555521594424004608', 'good')

        # # 发布推文。从推文文件中随机选取1条发布
        # twitter.create_tweet()

        # # 指定推文抽奖
        # # 参数：tweet_id, tag_amount=3, is_use_reply_file=True, is_like=True, is_retweet=True, is_reply=True
        # twitter.giveaway_from_fix_tweet(tweet_id='1628969073488048128', tag_amount=0, is_use_reply_file=True, is_like=True, is_retweet=True, is_reply=True)

        # # 随机获取符合一定条件的推文关注点赞转推评论
        # # 参数：query, start_time, end_time=None, search_amount=20, follows_count=1000, like_count=50, tag_amount=3, is_use_reply_file=True, is_like=True, is_retweet=True, is_reply=True
        # twitter.giveaway(query='(follow OR like OR rt OR tag OR retweet OR 关注 OR 喜欢 OR 转推) (#nft OR #gamefi) has:hashtags -is:retweet -is:reply -is:quote', start_time=1, end_time=None, search_amount=10, follows_count=100, like_count=50, tag_amount=0, is_use_reply_file=True, is_like=True, is_retweet=True, is_reply=True)

        # # 随机获取互关贴，留言、关注作者及评论者
        # # 参数：query, start_time, end_time=None, follows_count=1000, like_count=50, search_amount=20, to_follow_amount=10, my_twitter_data=None, tem_reply_text='诚信互关，有关必回\n#互关 #互粉  #互fo', is_use_reply_file=True
        # twitter.set_follow_info(query='(互关 OR 涨粉 OR 互粉) (#互关 OR #互粉 OR #有关必回) has:hashtags -is:retweet -is:reply -is:quote', start_time=1, end_time=None, follows_count=1000, like_count=10, search_amount=10, to_follow_amount=10, my_twitter_data=my_twitter_data, tem_reply_text='诚信互关，有关必回\n#互关 #互粉  #互fo', is_use_reply_file=False)

        # # 获取自己的关注者，没有关注的回关
        # # 参数：my_twitter_data=None, once_follow_num=10
        # twitter.follow_back(my_twitter_data=my_twitter_data, once_follow_num=10)

        # 日常养号：发布推文|随机获取符合一定条件的推文关注点赞转推评论|随机获取互关贴，留言，回关
        lucky = random.choice([1, 2, 3])
        if lucky == 1:
            twitter.create_tweet()
        elif lucky == 2:
            # query, start_time, end_time=None, search_amount=20, follows_count=1000, like_count=50, tag_amount=3, is_use_reply_file=True, is_like=True, is_retweet=True, is_reply=True
            twitter.giveaway(query='(follow OR like OR rt OR tag OR retweet OR 关注 OR 喜欢 OR 转推) (#nft OR #gamefi) has:hashtags -is:retweet -is:reply -is:quote', start_time=1, end_time=None, search_amount=10, follows_count=100, like_count=50, tag_amount=0, is_use_reply_file=True, is_like=True, is_retweet=True, is_reply=True)
        elif lucky == 3:
            # 1、获取自己的关注者，关注。2、随机找到互关贴，发互关消息。
            # query, start_time, end_time=None, follows_count=1000, like_count=50, search_amount=20, to_follow_amount=10, my_twitter_data=None, tem_reply_text='诚信互关，有关必回\n#互关 #互粉  #互fo', is_use_reply_file=True
            twitter.set_follow_info(query='(互关 OR 涨粉 OR 互粉) (#互关 OR #互粉 OR #有关必回) has:hashtags -is:retweet -is:reply -is:quote', start_time=1, end_time=None, follows_count=1000, like_count=10, search_amount=10, to_follow_amount=10, my_twitter_data=my_twitter_data, tem_reply_text='诚信互关，有关必回\n#互关 #互粉  #互fo', is_use_reply_file=False)
            # my_twitter_data=None, once_follow_num=10
            twitter.follow_back(my_twitter_data=my_twitter_data, once_follow_num=10)
        if len(data) > 1:
            interval_time = 60
            time.sleep(random.randrange(interval_time, interval_time+10))
        



