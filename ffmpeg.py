
import ffmpy
import os
'''
合并M3U8为MP4文件，可接着youku.py使用
'''
def m3u8tomp4(m3file):
    m3file=m3file
    ffmpy.FFmpeg(
    inputs={'./m3u8/'+m3file+'.m3u8':['-allowed_extensions','ALL', '-protocol_whitelist','file,http,crypto,tcp']},
    outputs={'./mp4/'+m3file+'.mp4': ['-c', 'copy']}).run()
'''
合并TS视频，通过读取M3U8文件，自动获取TS列表，同时ffmpeg合并为MP4文件。
'''
def storylist(i):
    # 简单过滤下空字符
    if i:
        # print(i)
        m3u8tomp4(i)
        # 调用ts合并函数
    else:
        print("空字符")
rootdir = './m3u8'
list = os.listdir(rootdir)  # 列出文件夹下所有的目录与文件
for i in list:
    name=i.split('.')[0] # 使用 ”.“分割文件名   
    storylist(name)
    

        

 
