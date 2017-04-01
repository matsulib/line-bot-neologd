#!/usr/bin/python3
import json
import requests
from collections import Counter
from urllib.parse import quote
from lxml.html import fromstring
from boto.s3.connection import S3Connection
from boto.s3.key import Key

import settings


# URLエンコード
def qquote(s):
    return quote(s.encode())


# num個の概要
def get_abstructs(word, num=10):
    res = requests.get('http://www.google.co.jp/search?ie=UTF-8&num={}&q={}'.format(num, qquote(word)))
    page = fromstring(res.text)
    return [b.text_content() for b in page.cssselect('.st')]


# wikipedia日本語ページが存在するか
def does_exist_in_wiki(title):
    query = 'https://ja.wikipedia.org/w/api.php?action=query&titles={}&format=json'
    return requests.get(query.format(quote(title))).text.find('pageid') >= 0


# wikipedia日本語ページのURL
def get_wikipedia_url(word):
    return 'https://ja.wikipedia.org/wiki/{}'.format(qquote(word))


# 固有名詞を頻度順にn個取得
def count_proper_nouns(text, n=None, ngs=[]):
    res = requests.post(settings.mecab_neologd_url,
                        data = json.dumps({'sentence': text}),
                        headers = {'Content-Type': 'application/json'})

    results = res.json()['results']

    key_genkei    = '原型'
    key_bunrui1 = '品詞細分類1'
    value_bunrui1 = '固有名詞'
    # 除外する固有名詞
    ng_list = ['*', 'ID', '名無しさん', '日', 'blog'] + ngs
    words = [r[key_genkei] for r in results if r[key_bunrui1] == value_bunrui1 and r[key_genkei] not in ng_list]

    return Counter(words).most_common(n)


# 画像検索結果からjpgファイルのURLリスト取得
def get_jpg_urls(word, n=None):
    text = requests.get('https://search.yahoo.co.jp/image/search?p={}'.format(qquote(word))).text
    page = fromstring(text)

    urls = []
    for i in page.cssselect('.tb a'):
        url = i.attrib['href']
        if url.lower().endswith('.jpg'):
            urls.append(url)
        if n and len(urls) == n:
            break

    return urls


# ファイルをS3にアップロード
def upload_to_s3(file_path):
    # connect to S3
    s3 = S3Connection(settings.aws_access_key_id, settings.aws_secret_access_key)
    bucket = s3.get_bucket(settings.aws_bucket_name)
    # upload with metadata and publish
    k = Key(bucket, file_path)
    k.set_contents_from_filename(file_path)
    k.make_public()


# ファイルのダウンロード
def download(url, path):
    res = requests.get(url, stream=True)
    if res.status_code == 200:
        with open(path, 'wb') as file:
            for chunk in res.iter_content(chunk_size=1024):
                file.write(chunk)
