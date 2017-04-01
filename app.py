#!/usr/bin/python3
import json
import os
import random
import re
import requests
import shutil
import string
import time
from flask import Flask, request, abort
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
)

import settings
import webutil
import imageutil

# LINE
line_bot_api = settings.line_bot_api
handler = settings.handler

# AWS
aws_access_key_id = settings.aws_access_key_id
aws_secret_access_key = settings.aws_secret_access_key
aws_bucket_base = settings.aws_bucket_base

app = Flask(__name__)


@app.route('/callback', methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info('Request body: ' + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 受信メッセージ
    req = event.message.text.replace('\n', ' ')
    # 絞り込みワード
    req += ' とは'
    # google検索で概要取得
    abstructs = webutil.get_abstructs(req, 100)
    if len(abstructs) == 0:
        # 概要がなかった
        line_bot_api.reply_message(event.reply_token, error_image_send_message())
    abstruct = ' '.join(abstructs)
    # 日付削除（固有名詞に含まれてしまうので）
    abstruct = remove_date(abstruct)

    res = []
    # 関連する固有名詞を取得（受信メーッセージ除外）
    word_count = webutil.count_proper_nouns(abstruct, n=1, ngs=re.split(r' |　', req))
    if len(word_count) == 0:
        # 固有名詞がなかった
        line_bot_api.reply_message(event.reply_token, error_image_send_message())
        return
    word = word_count[0][0]

    # 返信テキストの追加
    res_text = word
    if webutil.does_exist_in_wiki(word):
        res_text += '\n- ' + webutil.get_wikipedia_url(word)
    res.append(TextSendMessage(text=res_text))

    url = make_thumbnail_url(word)

    # 返信画像の追加
    res.append(ImageSendMessage(
                    original_content_url=url['img'],
                    preview_image_url=url['preview_img']))

    line_bot_api.reply_message(event.reply_token, res)


# エラー画像
def error_image_send_message():
    return ImageSendMessage(
                original_content_url=settings.error_img_url,
                preview_image_url=settings.error_img_url)


# ランダム文字列生成
def random_string(n=16):
    return ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(n)])


# 文字列から日付を除く
def remove_date(s):
    pattern = r'[0-9]{2,4}年|[0-9]{1,2}月|[0-9]{1,2}日'
    match = re.split(pattern, s)
    if match:
        s = ' '.join(match)
    return s


# 返信画像のURL作成
def make_thumbnail_url(word):
    # 作業ディレクトリ作成
    dir_name = time.strftime('%Y%m%d%H%M%S') + random_string()
    workdir = 'tmp/{}'.format(dir_name)
    os.mkdir(workdir)
    # 画像をダウンロード
    i, img_num = 0, 8
    for url in webutil.get_jpg_urls(word):
        try:
            webutil.download(url, '{}/{}.jpg'.format(workdir, i))
        except (ConnectionResetError, requests.exceptions.SSLError) as e:
            app.logger.info('download error: ' + e)
            continue
        i += 1
        if i == img_num:
            break
    # サムネイル作成
    img_name = 'thumbnail'
    imageutil.make_thumbnail(workdir, img_name, 240, img_num)
    # S3にアップロード
    upload_file = '{}/{}.jpg'.format(workdir, img_name)
    webutil.upload_to_s3(upload_file)
    os.remove(upload_file)  # サムネイル削除（プレビュー作成で邪魔にならないように）
    # サムネイルプレビュー作成
    preview_img_name = 'preview_thumbnail'
    imageutil.make_thumbnail(workdir, preview_img_name, 120, 4)
    preview_upload_file = '{}/{}.jpg'.format(workdir, preview_img_name)
    webutil.upload_to_s3(preview_upload_file)
    # 作業ディレクトリ削除
    shutil.rmtree(workdir)

    url = {'img': '{}/{}'.format(settings.aws_bucket_base, upload_file),
           'preview_img': '{}/{}'.format(settings.aws_bucket_base, preview_upload_file)}

    return url


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5001'))
    host = os.getenv('HOST', 'localhost')

    app.run(host=host, port=port, debug=True)

