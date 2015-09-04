#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Usage: downloader.py youtube_url
"""
import sys
import comtypes.client as cc
import requests
import bs4
from bs4 import BeautifulSoup
import urlparse
import re
from os import path

proxies = {
  "http": "http://127.0.0.1:8087",
  "https": "http://127.0.0.1:8087",
}


IdmModule = cc.GetModule(['{ECF21EAB-3AA8-4355-82BE-F777990001DD}', 1, 0])
idm = cc.CreateObject('IDMan.CIDMLinkTransmitter', None, None, IdmModule.ICIDMLinkTransmitter2)

def show(s):
    """
    For showing stuff in Windows console
    """
    if isinstance(s, unicode):
        print s.encode('gbk', 'replace')
    elif isinstance(s, str):
        print unicode(s, 'utf-8').encode('gbk', 'replace')
    elif isinstance(s, bs4.element.Tag):
        show(unicode(s))
    else:
        print s


def printl():
    print '----------------------------------------------------------'

def ValidPath(s):
    if not s:
        return s
    p = re.compile(r'[\\/:\*\?<>\|]', re.U)
    return p.sub('_', s)

def SendToIdm(title, mp4_url, localpath=None):
    print '-------> Sending to IDM:', title
    localfn = title+'.mp4'
    
    localpath = ValidPath(localpath)
    localfn = ValidPath(localfn)
    idm.SendLinkToIDM(mp4_url, '', '', '', '', '', localpath, localfn, 2)

class PlaylistParser:
    def __init__(self, url):
        self.url = url
        self.resp = requests.get(url, proxies=proxies, verify=False)
        self.soup = BeautifulSoup(self.resp.content, from_encoding='utf-8')

    def GetPlaylistTitle(self):
        pl_title = unicode(self.soup.select('#pl-header > div.pl-header-content > h1')[0].string).strip()
        return pl_title

    def GetVideoNumber(self):
        nvideos_ele = self.soup.select('#pl-header > div.pl-header-content > ul > li')[1]
        nvideos = int(nvideos_ele.string.split()[0])
        return nvideos

    def GetVideoUrl(self, item):
        a = item.select('.pl-video-title > a')[0]
        return urlparse.urljoin('https://www.youtube.com/', a['href'])

    def Parse(self):
        pl_title = self.GetPlaylistTitle()
        nvideos = self.GetVideoNumber()

        pltable = self.soup.select('#pl-load-more-destination > tr')
        assert len(pltable)==nvideos, 'Number of videos got from table not equal as shown. %d vs %d' % (nvideos, len(pltable))

        video_urls = [self.GetVideoUrl(item) for item in pltable]

        printl()
        print 'URL: [%s] parse done.' % self.url
        print 'Playlist: >> %s <<' % pl_title
        print 'Got %d videos.' % len(video_urls)
        
        return pl_title, video_urls


class KvGrabber:
    def __init__(self, video_url):
        self.video_url = video_url
        self.resp = requests.get('http://keepvid.com', params={'url': video_url}, proxies=proxies)
        self.soup = BeautifulSoup(self.resp.content, from_encoding='utf-8')

    @staticmethod
    def GetLine(beg):
        curs = beg
        line = u''
        while True:
            line += unicode(curs)
            curs = curs.next_sibling
            if curs.name == 'br':
                break
        return BeautifulSoup(line, 'html.parser').get_text()

    def GetTitle(self):
        title = unicode(self.soup.select('#info > a.n')[0].string).strip()
        assert title, 'Got wront title.'
        return title

    def GetMaxQuality(self):
        dl = self.soup.find(id='dl')
        dl_list = dl.find_all('a', recursive=False)
        valid_mp4 = {}
        for a in dl_list:
            line = self.GetLine(a)
            if u'» Download MP4 «' in line and u'(Video Only)' not in line:
                p = re.compile(r'.+ (\d+)p.*', re.U)
                q = int(p.match(line).group(1))
                valid_mp4[q] = a['href']

        max_q = max(valid_mp4.keys())
        max_mp4_url = valid_mp4[max_q]
        assert max_mp4_url, 'Error in getting max quality mp4 url.'
        return max_q, max_mp4_url

    def GetDownloadUrl(self):
        max_q, max_mp4_url = self.GetMaxQuality()
        video_title = self.GetTitle()
        
        printl()
        print 'Parse:', self.video_url
        print 'Title >> %s << :' % video_title
        print 'Mp4(%dp):' % max_q, max_mp4_url
        return video_title, max_mp4_url

def Download(url, save_path=None):
    if '/playlist?' in url:
        pl_title, y2b_vid_urls = PlaylistParser(url).Parse()
    elif '/watch?' in url:
        pl_title, y2b_vid_urls = None, [url]
    else:
        raise Exception('Wrong youtube url: %s' % url)

    faillist = []
    for vid_url in y2b_vid_urls:
        try:
            title, mp4_url = KvGrabber(vid_url).GetDownloadUrl()
            if pl_title:
                localpath = path.join(u'E:\\Download', pl_title)
            else:
                localpath = None
            SendToIdm(title, mp4_url, localpath)
        except Exception, e:
            print '=====!!Error:', vid_url
            faillist.append(vid_url+'\n')

    printl()
    print 'All done.'

    failfn = 'fail.txt'
    if len(faillist) != 0:
        with open(failfn, 'w') as f:
            f.writelines(faillist)
        print '%d failed, save to %s' % (len(faillist), failfn)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Usage: %s youtube_url' % sys.argv[0]
        sys.exit(-1)

    Download(sys.argv[1])
