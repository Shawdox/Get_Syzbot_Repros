#!/usr/bin/env python3


from bs4 import BeautifulSoup
import os
import requests
import re
import multiprocessing
import time
import datetime
import colorit
import json



os.environ["http_proxy"] = "http://127.0.0.1:8001"
os.environ["https_proxy"] = "http://127.0.0.1:8001"
lengths = {}
totalnum = 0
'''
Query https://syzkaller.appspot.com/upstream for all bugs against upstream kernel and have "C" and "syz" reproducers
Save reproducers to text files
'''

def INFO_PRINT(prefix = 'INFO:', info = ''):
    prefix = colorit.color("[*] " + prefix, colorit.Colors.green)
    print(prefix, info)

def ERR_PRINT(prefix = 'ERROR:', info = ''):
    prefix = colorit.color("[*] " + prefix, colorit.Colors.red)
    print(prefix, info)

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = re.sub(rb'[^\w-]', b'-', value).strip().lower()
    return value

class Cache: # id is link
    def __init__(self, dataDir, manifest):
        self.dataDir = dataDir.encode()
        if not os.path.exists(self.dataDir):
            os.mkdir(self.dataDir)
            assert os.path.exists(self.dataDir)
        self.manifest = manifest
        if os.path.exists(self.manifest):
            data = open(self.manifest, 'rb').read()
        else:
            data = b''
        self.entries = {}
        for i in re.finditer(rb'<entry>\s*?<link>(.+?)</link>\s*?<time>(.+?)</time>\s*?<path>(.+?)</path>\s*</entry>', data, re.MULTILINE):
            link, time, path = i.groups()
            self.entries[link] = [time, path]
        print(b"Cache size: %d" % len(self.entries))

    def now(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M').encode('ascii')
        
    def add(self, link, time, data):
        if type(link) != bytes:
            link = link.encode()
        if type(time) != bytes:
            time = time.encode()
        if type(data) != bytes:
            data = data.encode()
        # if link exists, overwrite file
        if link in self.entries:
            ent = self.entries[link]
            ent[0] = time
            open(ent[1], 'wb').write(data)
        else: # create new file and add to manifest
            fileName = slugify(link)
            filePath = os.path.join(self.dataDir, fileName)
            while os.path.isfile(filePath):    
                filePath += b'a'
            self.entries[link] = [time, fileName]
            open(filePath, 'wb').write(data)
            f = open(self.manifest, 'ab')
            f.write(b'<entry>\n<link>%s</link>\n<time>%s</time>\n<path>%s</path>\n</entry>' % (link, time, fileName))
            f.close()
                
    def has(self, link):
        if type(link) != bytes:
            link = link.encode()
        return link in self.entries

    def getData(self, link):
        if type(link) != bytes:
            link = link.encode()
        fileName = self.entries[link][1]
        filePath = os.path.join(self.dataDir, fileName)
        return open(filePath, 'rb').read()

cache = Cache('cache', 'cache.txt')
domain = "https://syzkaller.appspot.com"

def fetch_data(url):
    if cache.has(url):
        #print(f"Find {url} in cache")
        return cache.getData(url)

    #print(f"Requesting {url}")
    time.sleep(1)
    #data = requests.get(url, verify=False).content
    data = requests.get(url).content
    print(f"Got {url}")
    cache.add(url, cache.now(), data)
    return data

def get_reproducers(bugs):
    for idx, bug in enumerate(bugs):
        page = fetch_data(domain + bug)
        soup = BeautifulSoup(page, 'html.parser')
        # parse last table in page that has class "list_table"
        try:
            table = soup.find_all('table', class_="list_table")[-1]
        except IndexError:
            print("No reproducers for bug : ",bug)
            return
        # find a that has text "syz", only one
        a = table.find_all('a', string="syz")
        for entry in a:
            try:
                # get the href of the link
                link = entry.get('href')
                page = fetch_data(domain + link)
                page = page.decode('utf-8')
                file_str = 'C:\\Users\\Shaw\\Desktop\\repoducers\\syz\\'+link.split('=')[-1]
                with open(file_str,'w') as f:
                    f.write(page)
                num = 0
                for line in page.split('\n'):
                    if not line.startswith('#') and line.strip():
                        num += 1
                INFO_PRINT(f'[{idx+1}/{len(bugs)}]Get a syz repro: ',f'sequence length {num}')
                print(f'See: {file_str}')
                lengths[str(domain) + link] = num
            except Exception as err:
                ERR_PRINT(info=err)
                continue
        if (idx+1)%200 == 0:
            with open('./repro_lengths.json','w') as f:
                json.dump(lengths, f)  
    with open('./repro_lengths.json','w') as f:
        json.dump(lengths, f)  
                

def get_bugs(url):
    bugs = []
    page = fetch_data(url)
    soup = BeautifulSoup(page, 'html.parser')
    # parse table rows
    rows = soup.find_all('tr')
    for row in rows:
        # print row with class as "title" and first "stat"
        title = row.find_all('td', class_="title")
        stat = row.find_all('td', class_="stat")
        # if title and stat exist
        if title and stat:
            # check if stat[0] contains "C" in "td"
            if "C" in stat[0] or "syz" in stat[0]:
                # print(title[0].find('a').get('href'))
                bugs.append(title[0].find('a').get('href'))
    return bugs

def main():
    # Query the page
    urls = [
        'https://syzkaller.appspot.com/upstream',
        'https://syzkaller.appspot.com/linux-5.15',
        'https://syzkaller.appspot.com/linux-6.1'
    ]
    for url in urls:
        bugs = get_bugs(url)
        get_reproducers(bugs)
        bugs = get_bugs(url + '/fixed')
        get_reproducers(bugs)
    
    
    with open('./repro_lengths.json','w') as f:
        json.dump(lengths, f)       
    

if __name__ == "__main__":
    main()