import functools
import json
import ssl
import time
import logging
import os
import requests
import smtplib
from threading import Thread

from flask import Flask, request, abort, make_response, jsonify, Response
from flask_restplus import Resource, Api, reqparse, fields


# Config
class Config:
    MAX_ALLOWED_SUBSCRIPTIONS_BY_EMAIL = 5
    ALPHAVANTAGE_REQUEST = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={0}&to_currency=RUB&apikey=' + \
                           os.environ['ALPHAVANTAGE_API_KEY']

    # SMTP
    SMTP_HOST_IP = os.environ['SMTP_HOST_IP']  # smtp.mail.ru
    SMTP_HOST_PORT = os.environ['SMTP_HOST_PORT']  # 465
    SMTP_MY_ADDRESS = os.environ['SMTP_MY_ADDRESS']  # your mail
    SMTP_MY_PASS = os.environ['SMTP_MY_PASS']  # your pass


# Exceptions
class MaxSubscriptionsReachedError(Exception):
    pass


class SubscriptionAlreadyExistsError(Exception):
    pass


# Database
class Subscriber:
    """
    Kind of SqlAlchemy one to many
    to store subscribers info:
    {
        "email(req)": [
            {
                "ticker(req)": str,
                "max_price": float,
                "min_price": float
            },
            ...
        ]
    }
    """
    subscribers = {}

    @staticmethod
    def get_subscribers():
        return Subscriber.subscribers.keys()

    @staticmethod
    def get_user_subscriptions(email):
        return [subscription for subscription in Subscriber.subscribers[email]]

    @staticmethod
    def add_new(email, ticker, max_price, min_price):
        new_ticker_subscription = {
            'ticker': ticker,
            'max_price': max_price,
            'min_price': min_price
        }

        if email in Subscriber.subscribers:
            if len(Subscriber.subscribers[email]) == Config.MAX_ALLOWED_SUBSCRIPTIONS_BY_EMAIL:
                raise MaxSubscriptionsReachedError()
            if ticker in [subscription['ticker'] for subscription in Subscriber.subscribers[email]]:
                raise SubscriptionAlreadyExistsError()

            Subscriber.subscribers[email].append(new_ticker_subscription)
        else:
            Subscriber.subscribers[email] = [new_ticker_subscription]

    @staticmethod
    def delete_subscriber(email):
        Subscriber.subscribers.pop(email, None)

    @staticmethod
    def delete_ticker_subscription(email, ticker):
        if email in Subscriber.subscribers:
            Subscriber.subscribers[email] = [subscription for subscription in Subscriber.subscribers[email]
                                             if subscription['ticker'] != ticker]


app = Flask(__name__)
api = Api(app)


# Watchdog: monitors tickets api and notify subscribers
def send_mail(email, msg):
    logging.info(f'Sending mail to {email} with "{msg}"')
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(Config.SMTP_HOST_IP, Config.SMTP_HOST_PORT, context=context) as server:
        server.login(Config.SMTP_MY_ADDRESS, Config.SMTP_MY_PASS)
        server.sendmail(Config.SMTP_MY_ADDRESS, email, msg)


def check_ticker(email, subscription):
    response = requests.get(Config.ALPHAVANTAGE_REQUEST.format(subscription['ticker']))
    json_result = json.loads(response.text)
    if 'Realtime Currency Exchange Rate' not in json_result:
        send_mail(email, f'{subscription["ticker"]} is incorrect ticker name, we gonna delete it.')
    else:
        current_price = float(json_result['Realtime Currency Exchange Rate']['5. Exchange Rate'])
        if subscription.get('max_price', None) is not None and subscription['max_price'] < current_price:
            msg = f"{subscription['ticker']} exceeded {subscription['max_price']}. Now it's {current_price}"
            send_mail(email, msg)
        if subscription.get('min_price', None) is not None and subscription['min_price'] > current_price:
            msg = f"{subscription['ticker']} decreased {subscription['min_price']}. Now it's {current_price}"
            send_mail(email, msg)
    Subscriber.delete_ticker_subscription(email, subscription['ticker'])


def monitor():
    while True:
        for subscriber_email in Subscriber.get_subscribers():
            threads = []
            user_subs = Subscriber.get_user_subscriptions(subscriber_email)
            logging.info(f"Handle {subscriber_email} with {user_subs} subs")

            for sub in user_subs:
                process = Thread(target=check_ticker, args=[subscriber_email, sub])
                process.start()
                threads.append(process)
            for process in threads:
                process.join()

        time.sleep(10)


notifier = Thread(target=monitor)


@app.before_first_request
def initialize_notifier():
    notifier.start()


# Routes: handle users requests
def validate_param(name, value, value_type, required=False):
    if value is None:
        if required:
            abort(400, f"{name} is required parameter")
    else:
        try:
            value_type(value)
        except ValueError:
            abort(400, f"{name} must be {value_type}")


def delete_subscription_serializer(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Do something with your request here
        validate_param('email', request.args.get('email', None), str, required=True)
        validate_param('ticker', request.args.get('ticker', None), str, required=False)
        return f(*args, **kwargs)

    return decorated_function


def post_subscription_serializer(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Do something with your request here
        validate_param('email', request.json.get('email', None), str, required=True)
        validate_param('ticker', request.json.get('ticker', None), str, required=True)
        validate_param('max_price', request.json.get('max_price', None), float, required=False)
        validate_param('min_price', request.json.get('min_price', None), float, required=False)

        if request.json.get('max_price', None) is None \
                and request.json.get('min_price', None) is None:
            abort(400, "(max_price, min_price) at least one is required")

        return f(*args, **kwargs)

    return decorated_function


# Another way to validate
# post_subscription_args = api.model('Post subscription', {
#     'email': fields.String(required=True),
#     'ticker': fields.String(required=True),
#     'max_price': fields.Float(required=False, min=0),
#     'min_price': fields.Float(required=False, min=0)
# })
# api.expect(post_subscription_args, validate=True)

@api.route('/subscription')
class SubscriptionRoute(Resource):
    @post_subscription_serializer
    def post(self):
        logging.info(request.json)

        max_price = request.json.get('max_price', None)
        max_price = float(max_price) if max_price is not None else None

        min_price = request.json.get('min_price', None)
        min_price = float(min_price) if min_price is not None else None

        try:
            Subscriber.add_new(
                request.json['email'],
                request.json['ticker'],
                max_price,
                min_price
            )
        except MaxSubscriptionsReachedError:
            abort(409, "Max subscriptions reached, u can try to remove them using DELETE request")
        except SubscriptionAlreadyExistsError:
            abort(409, "Subscription already exists")

        return Response(status=201)

    @delete_subscription_serializer
    def delete(self):
        logging.info(request.args)

        email = request.args['email']
        ticker = request.args.get('ticker', None)
        if ticker is not None:
            Subscriber.delete_ticker_subscription(email, ticker)
        else:
            Subscriber.delete_subscriber(email)

        return Response(status=204)


if __name__ == '__main__':
    app.run(debug=True)
