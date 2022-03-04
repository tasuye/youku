import re, requests, time, subprocess, json, base64
from hashlib import md5
import requests
import bs4
import pymysql

class YouKu:
    def __init__(self, cookie):
        self.cookie = cookie
        self.host = 'localhost'
        self.user = 'root'
        self.password =''

    def youku_sign(self, t, data, token):
        appKey = '24679788'     # 固定值
        '''token值在cookie中'''
        sign = token + '&' + t + '&' + appKey + '&' + data
        md = md5()
        md.update(sign.encode('UTF-8'))
        sign = md.hexdigest()
        return sign

    def utid(self):
        cna = re.compile("cna=(.*?);")
        _m_h5_tk = re.compile("_m_h5_tk=(.*?)_.*?;")
        token = _m_h5_tk.findall(self.cookie+";")
        utid_ = cna.findall(self.cookie+";")
        return {"utid": utid_[0], "token": token[0]}

    # 若直接在首页小窗口上复制的视频网址，是重定向的网址。
    def redirect(self, url):
        headers = {
            "referer": "https://www.youku.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        }
        resp = requests.get(url=url, headers=headers)
        return resp.url

    def page_parser(self, url):
        # headers内容可随意修改
        headers = {
            "authority": "v.youku.com",
            "method": "GET",
            "path": url.replace("https://v.youku.com/",""),
            "scheme": "https",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "max-age=0",
            "cookie": self.cookie,
            "referer": "https://www.youku.com/",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        }
        resp = requests.get(url=url, headers=headers)
        html = resp.content.decode("utf-8")
       
        videoId = re.compile("videoId: '(.*?)'")
        showid = re.compile("showid: '(.*?)'")
        currentEncodeVid = re.compile("currentEncodeVid: '(.*?)'")
        videoId = videoId.findall(html, re.S | re.M | re.I)
        current_showid = showid.findall(html, re.S | re.M | re.I)
        vid = currentEncodeVid.findall(html, re.S | re.M | re.I)
        return {"current_showid": current_showid[0], "videoId": videoId[0], "vid": vid[0]}

    def get_emb(self, videoId):
        emb = base64.b64encode(("%swww.youku.com/" % videoId).encode('utf-8')).decode('utf-8')
        return emb

    # 这个函数用来获取元素的第一个值
    def takeOne(self, elem):
        return float(elem[0])

    def m3u8_url(self, t, params_data, sign):
        url = "https://acs.youku.com/h5/mtop.youku.play.ups.appinfo.get/1.1/"

        params = {
            "jsv": "2.5.8",
            "appKey": "24679788",
            "t": t,
            "sign": sign,
            "api": "mtop.youku.play.ups.appinfo.get",
            "v": "1.1",
            "timeout": "20000",
            "YKPid": "20160317PLF000211",
            "YKLoginRequest": "true",
            "AntiFlood": "true",
            "AntiCreep": "true",
            "type": "jsonp",
            "dataType": "jsonp",
            "callback": "mtopjsonp1",
            "data": params_data,
        }

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Cookie": self.cookie,
            "Host": "acs.youku.com",
            "Referer": "https://v.youku.com/v_show/id_XMzY2Mzg0NTE2OA==.html",
            
            "Sec-Fetch-Dest": "script",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        }

        resp = requests.get(url=url, params=params, headers=headers)
        result =resp.text
        # print(result)
        data = json.loads(result[12:-1])
        # print(data)
        ret = data["ret"]
        video_lists = []
        if ret == ["SUCCESS::调用成功"]:
            stream = data["data"]["data"]["stream"]
            title = data["data"]["data"]["video"]["title"]
            fileid= data["data"]["data"]["video"]["encodeid"]
            img= data["data"]["data"]["video"]["logo"]
            print("解析成功:")
            for video in stream:
                m3u8_url = video["m3u8_url"]
                width = video["width"]
                height = video["height"]
                size = video["size"]
                size = '{:.1f}'.format(float(size) / 1048576)
                video_lists.append([size, width, height, title, m3u8_url])
                # print(f">>>  {title} 分辨率:{width}x{height} 视频大小:{size}M \tm3u8播放地址:{m3u8_url}")
            # print(self.play(video_lists[-1][4]) )
            # print(video_lists[-1][4])

            video_lists.sort(key=self.takeOne)
            print(video_lists[-1][4])
            # 取出M3U8的真实地址

            m3u8=requests.get(video_lists[-1][4]).text
            # 读取M3U8文件
            
            self.savem3u8(fileid,m3u8)  
                #   调用 savem3u8函数将m3u8写入本地
           
            sql="""insert into youku(name,videoid,img)values ('%s', '%s', '%s')""" % (title,fileid,img)
            self.savesql(sql) 
            # 基本信息写入数据库，这一步可以忽略

        elif ret == ["FAIL_SYS_ILLEGAL_ACCESS::非法请求"]:
            print("请求参数错误")
        elif ret == ["FAIL_SYS_TOKEN_EXOIRED::令牌过期"]:
            print("Cookie过期")
        else:
            print(ret[0])

    def savem3u8(self,fileid,m3u8):
        # 写入M3U8

        with open('./m3u8/'+fileid+'.m3u8',"a+") as fo:
            # 写入 "./m3u8/"目录
            fo.write(m3u8)
            fo.close
            print("m3u8写入成功")
    def savemimg(self,fileid,jpg):
        # 写入jpg

        with open(fileid+'.jpg',"a+") as fo:
            fo.write(jpg)
            fo.close
            print("写入成功")
    
    def savesql(self,sql):
        # 数据库写入函数
  
        conndb = pymysql.connect(host=self.host, user=self.user, password=self.password, database='report')
        #获取游标
        conn=conndb.cursor()  
        try:
            # 执行sql语句
            conn.execute(sql)
            # 提交到数据库执行
            conndb.commit()
        except:
            # 如果发生错误则回滚
            conndb.rollback()
        conndb.close()
        print("数据插入成功") 



    def play(self, x):
        text = 'ffplay -protocol_whitelist "file,http,https,rtp,udp,tcp,tls" -loglevel quiet -i "%s"' % x
        subprocess.call(text, shell=True)

    def start(self,youkuurl):
        while True:
            try:
                t = str(int(time.time() * 1000))
                user_info = self.utid()
                userid = user_info["utid"]
                # url = input("\n\n请将优酷视频播放链接粘贴到这:\n")
                # url='https://v.youku.com/v_show/id_XNTA0Mzc2MjI0MA==.html?spm=a2hcb.12701310.app.5~5!3~5!3~5~5~5!10~5~5~5~A&s=531aefbfbd351cefbfbd'
                # url = self.redirect(url)
                url = self.redirect(youkuurl)
                page_info = self.page_parser(url)
                emb = self.get_emb(page_info["videoId"])
                params_data = r'''{"steal_params":"{\"ccode\":\"0502\",\"client_ip\":\"192.168.1.1\",\"utid\":\"%s\",\"client_ts\":%s,\"version\":\"2.1.69\",\"ckey\":\"DIl58SLFxFNndSV1GFNnMQVYkx1PP5tKe1siZu/86PR1u/Wh1Ptd+WOZsHHWxysSfAOhNJpdVWsdVJNsfJ8Sxd8WKVvNfAS8aS8fAOzYARzPyPc3JvtnPHjTdKfESTdnuTW6ZPvk2pNDh4uFzotgdMEFkzQ5wZVXl2Pf1/Y6hLK0OnCNxBj3+nb0v72gZ6b0td+WOZsHHWxysSo/0y9D2K42SaB8Y/+aD2K42SaB8Y/+ahU+WOZsHcrxysooUeND\"}","biz_params":"{\"vid\":\"%s\",\"play_ability\":16782592,\"current_showid\":\"%s\",\"preferClarity\":99,\"extag\":\"EXT-X-PRIVINF\",\"master_m3u8\":1,\"media_type\":\"standard,subtitle\",\"app_ver\":\"2.1.69\",\"h265\":1}","ad_params":"{\"vs\":\"1.0\",\"pver\":\"2.1.69\",\"sver\":\"2.0\",\"site\":1,\"aw\":\"w\",\"fu\":0,\"d\":\"0\",\"bt\":\"pc\",\"os\":\"win\",\"osv\":\"10\",\"dq\":\"auto\",\"atm\":\"\",\"partnerid\":\"null\",\"wintype\":\"interior\",\"isvert\":0,\"vip\":1,\"emb\":\"%s\",\"p\":1,\"rst\":\"mp4\",\"needbf\":2,\"avs\":\"1.0\"}"}'''% (userid, t[:10], page_info["vid"], page_info["current_showid"], emb)
                sign = self.youku_sign(t, params_data, user_info["token"])
                self.m3u8_url(t, params_data, sign)
                
                break  #这里加break 是放置读取数据的时候一直循环
            except Exception as e:
                print('error:',e , "或可能cookie设置错误")
                break

if __name__ == '__main__':
    print("优酷M3U8下载")
    cookie ='isg=BBwcrde9kg-DLmbvIb--eDAX7zzOlcC_ao6KYfYdKofrQbzLHqdFT3XzoSm5UvgX; l=eBjZuu2PLPQLs0xLBOfalurza779IIdYYuPzaNbMiOCPO_1M5C25W6mYh18HCn1VhsGXR3yW0rT7BeYBcIDPz9qe87cKIADmn; tfstk=cogCBRx4FY3awM7PwXOw8bYxyfzVZgbQ_BwiO08ai73vFJHCizX4h3g-ZOhbu51..; P_F=1; __aysvstp=227; __ayvstp=227; __arcms=dchild-3-00; __arpvid=1646293249300P1ZhHR-1646293249356; __arycid=dchild-3-00; __ayft=1646036911647; __aypstp=92; __ayscnt=1; __aysid=1646036911647AjJ; __ayspstp=92; x5sec=7b22617365727665722d686579693b32223a226336633166306130663634326434303732353065643333303566373063613835434d4867675a45474550484c6b6f4f696e2f332b6b51456f416a43436766444f2b502f2f2f2f3842227d; xlly_s=1; _m_h5_tk=61121b5853331939836a30c53109f009_1646297914269; _m_h5_tk_enc=8f476524b0a280e92c86a85880e7912a; P_ck_ctl=4F659BDCC1C9BAB34F00E2C765FDC72D; cna=HHijGrcl6nwCASeqOw66HLJi; UM_distinctid=17f4360bf18230-09d70cdf7c1b22-3d62684b-13c680-17f4360bf1a111c; modalFrequency={"UUID":"10"}; P_gck=NA%7CtU4aOyIWmRLgXgmehP%2FY8Q%3D%3D%7CNA%7C1646041539445; P_pck_rm=tIGK%2F18y1e5dd01681f291ZB8VbR35Xjtu0DiCvLWsCAqrZOWyuEYUc5bCDmMu16%2FhSrN%2FOGUQj%2FzciY3UwzkKUUmoRP9IVyH%2BRQvkq7avGKsh8%2BmqUuBfONxnVmv%2F8vjZf8IsLtzN%2BLkXnUZGj73pMND7qgRbLwcQrU6g%3D%3D%5FV2; disrd=39045; __ysuid=164603691164513O'
    # cookie 通过web浏览获取，如果是VIP节目，请先登录VIP账号后再获取cookie。 具体方式：F12 开发者工具， 选择network ，选择 document  ，点击最前面的一个，复制cookie即可
    youku = YouKu(cookie)
    # youku.start()
    
    headers = {
            "referer": "https://www.youku.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        }
    '''
    优酷的页面为JS渲染，获取页面内容比较麻烦，这里我们通过查看源码的方式，把要抓取的内容复制到本地创建HTML文件，以方面接下来爬取内容列表。
    '''
    get_response = requests.get('http://localhost/youku.html', headers=headers).content      
    content = bs4.BeautifulSoup(get_response, 'lxml');
    # 解析结果    
    soup=content.select("div.anthology-content>div.pic-text-item")
    for i in soup:
        youku.start(i.find('a')['href'])
        # 调用youkustart 获取 m3u8,获取以后通过ffmpeg.py文件合成视频。 也可以将ffmpeg.py导入到这里执行，现在分开执行的原因主要是，在获取m3u8的过程中经常因为优酷的安全机制而中断，所以为了完整的获取m3u8，就分开执行了。

    
  