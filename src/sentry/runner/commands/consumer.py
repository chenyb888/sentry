from __future__ import absolute_import, print_function

import click
import signal


@click.command()
@click.option('--topic', multiple=True, required=True,
              help='Topic(s) to consume from.')
@click.option('--dead-letter-topic', required=True,
              help='Topic to produce failed messages into.')
@click.option('--consumer-group', default='sentry-consumers',
              help='Consumer group name.')
@click.option('--bootstrap-server', default=['localhost:9092'], multiple=True,
              help='Kafka bootstrap server(s) to use.')
@click.option('--concurrency', default=1,
              help='Number of worker subprocess to run that process messages. If set to 1 they will be processed in the consumer.')
@click.option('--max-batch-size', default=10000,
              help='Max number of messages to batch in memory before committing offsets to Kafka.')
@click.option('--max-batch-time-ms', default=60000,
              help='Max length of time to buffer messages in memory before committing offsets to Kafka.')
@click.option('--auto-offset-reset', default='error', type=click.Choice(['error', 'earliest', 'latest']),
              help='Kafka consumer auto offset reset.')
def consumer(**options):
    from batching_kafka_consumer import BatchingKafkaConsumer
    from sentry.consumer import ConsumerWorker

    # forks off multiprocessing workers if necessary
    worker = ConsumerWorker(concurrency=options['concurrency'])

    from sentry.runner import configure
    configure()

    from django.conf import settings

    known_topics = {x['topic'] for x in settings.KAFKA_TOPICS.values()}
    topics = options['topic']
    for topic in topics:
        if topic not in known_topics:
            raise RuntimeError("topic '%s' is not one of: %s" % (topic, known_topics))

    consumer = BatchingKafkaConsumer(
        topics=options['topic'],
        worker=worker,
        max_batch_size=options['max_batch_size'],
        max_batch_time=options['max_batch_time_ms'],
        bootstrap_servers=options['bootstrap_server'],
        group_id=options['consumer_group'],
        auto_offset_reset=options['auto_offset_reset'],
        dead_letter_topic=options['dead_letter_topic'],
    )

    def handler(signum, frame):
        consumer.signal_shutdown()

    signal.signal(signal.SIGINT, handler)

    consumer.run()
