#!/usr/bin/env python

import pika, sys, os


def initialize_channel():
    (username, password) = (os.environ.get('RABBIT_USERNAME'), os.environ.get('RABBIT_PASSWORD'))
    vhost_name = os.environ.get('RABBIT_VHOST')
    credentials = pika.PlainCredentials(username, password)
    conn_parameters = pika.ConnectionParameters('localhost', virtual_host=vhost_name, 
        credentials=credentials)
    conn_broker = pika.BlockingConnection(conn_parameters)
    return conn_broker.channel()


LOG_RECEIVER_QUEUE = ( 'email_log_queue' )
EXCHANGE_NAME = 'email_exchange'
FILENAME = 'email_log_file.txt'
my_file = None


def email_log_receiver_callback( channel, method, header, message ):
    channel.basic_ack( delivery_tag = method.delivery_tag )
    if msg == 'quit':
        channel.basic_cancel(consumer_tag='logs')
        channel.stop_consuming()
        my_file.close()
    else:
        my_file.write( message )


def initialize_email_receiver(channel):
    channel.exchange_declare(EXCHANGE_NAME, durable = True, passive=False, auto_delete = False,
        exchange_type='topic')
    channel.queue_declare(queue=LOG_RECEIVER_QUEUE)
    channel.queue_bind(queue=LOG_RECEIVER_QUEUE, exchange=EXCHANGE_NAME, routing_key='*.log')
    channel.basic_consume(email_log_receiver_callback, consumer_tag='logs', 
        queue=LOG_RECEIVER_QUEUE)


if __name__ == '__main__':
    channel = initialize_channel()
    initialize_email_receiver(channel)
    my_file = open(FILENAME, 'a')
    channel.start_consuming()
