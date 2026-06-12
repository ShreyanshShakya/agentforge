from kombu import Connection, Exchange, Queue

class MessagingQueue:
    def __init__(self, broker_url):
        self.connection = Connection(broker_url)
        self.exchange = Exchange('todo_exchange', type='direct')
        self.todo_queue = Queue('todos', exchange=self.exchange, routing_key='todos')

    def send_message(self, message):
        with self.connection as conn:
            producer = conn.producer(serializer='json')
            producer.publish(message, exchange=self.exchange, routing_key='todos')

    def consume_messages(self, callback):
        with self.connection.Consumer(self.todo_queue) as consumer:
            for message in consumer.itermessages():
                callback(message)
                consumer.ack(message)