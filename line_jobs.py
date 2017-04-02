#!/usr/bin/python3
import os
import random
import re
import requests
import shutil
import string
import time
from rq import Queue
from linebot.models import (
    TextSendMessage, ImageSendMessage
)

import settings
import webutil
import imageutil


# LINE
line_bot_api = settings.line_bot_api


# textに関連するキーワードと画像をsender_idに通知する
def push_keyword_images(message_id, sender_id, text, num=3):
    # 絞り込みワード
    text += ' とは'
    # google検索で概要取得
    abstructs = webutil.get_abstructs(text, 100)
    if len(abstructs) == 0:
        # 概要がなかった
        line_bot_api.push_message(sender_id, error_image_send_message())
        return
    abstruct = ' '.join(abstructs)
    # 日付削除（固有名詞に含まれてしまうので）
    abstruct = remove_date(abstruct)

    # 関連する固有名詞を取得（受信メーッセージ除外）
    word_count = webutil.count_proper_nouns(abstruct, n=num, ngs=re.split(r' |　', text))
    if len(word_count) == 0:
        # 固有名詞がなかった
        line_bot_api.push_message(sender_id, error_image_send_message())
        return

    for wc in word_count:
        push_messages = []
        word = wc[0]
        # Pushテキストの追加
        push_text = word
        if webutil.does_exist_in_wiki(word):
            push_text += '\n- ' + webutil.get_wikipedia_url(word)
        push_messages.append(TextSendMessage(text=push_text))

        try:
            # サムネイル画像を作成
            url = make_thumbnail_url(word)
            # Push画像の追加
            push_messages.append(ImageSendMessage(
                        original_content_url=url['img'],
                        preview_image_url=url['preview_img']))
        except OSError as e:
            # 処理する画像を開けなかった
            # エラー画像を追加
            push_messages.append(error_image_send_message())
        # Push実行
        line_bot_api.push_message(sender_id, push_messages)

    line_bot_api.push_message(sender_id, TextSendMessage(text='おわた [id:{}]'.format(message_id)))


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


# 返信画像を作成しURLを返す
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
            # print('download error: ' + e)
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