#!/usr/bin/python3
import os
from linebot import (
    LineBotApi, WebhookHandler
)


# LINE
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# AWS
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_bucket_name = os.getenv('AWS_BUCKET_NAME')
aws_s3_base = os.getenv('AWS_S3_BASE')
aws_bucket_base = '{}/{}'.format(aws_s3_base, aws_bucket_name)

# mecab
mecab_neologd_url = os.getenv('MECAB_NEOLOGD_URL')

# エラー画像
error_img_url = os.getenv('ERROR_IMAGE_URL')