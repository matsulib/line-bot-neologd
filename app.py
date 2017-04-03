#!/usr/bin/python3
import os
from rq import Queue
from flask import (
    Flask, request, abort
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage
)

import settings
from rq_worker import conn
from line_jobs import push_keyword_images


# LINE
line_bot_api = settings.line_bot_api
handler = settings.handler


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
    # とりあえず返信
    line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text='ちょっと待ってね [id:{}]'.format(event.message.id)))

    # 処理をキューに登録して非同期で実行
    q = Queue(connection=conn)
    q.enqueue(push_keyword_images, event.message.id, event.source.sender_id, event.message.text, 3)


@handler.default()
def default(event):
    # 笑顔の絵文字を返信
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text='\U0001f604'))


if __name__ == '__main__':
    port = int(os.getenv('PORT', '5001'))
    host = os.getenv('HOST', 'localhost')

    app.run(host=host, port=port, threaded=True, debug=True)

