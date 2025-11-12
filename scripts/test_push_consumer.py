#!/usr/bin/env python3
"""
Test script to publish a sample push notification event to RabbitMQ.
This is useful for testing that the Push Service consumer is working correctly.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import uuid
from urllib.parse import urlparse

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import pika
import config


def publish_test_event(
    user_id: int = 123,
    event_id: str = None,
    template_code: str = None,
    inline_payload: dict = None
):
    """Publish a test push event to RabbitMQ."""
    
    if not event_id:
        event_id = str(uuid.uuid4())
    
    # Build the event payload
    event = {
        "event_id": event_id,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Add either template or inline payload
    if template_code:
        event["template_code"] = template_code
        event["variables"] = {
            "name": "User",
            "platform": "iOS",
            "link": "https://example.com"
        }
        event["language"] = "en"
    elif inline_payload:
        event["payload"] = inline_payload
    else:
        # Default inline payload
        event["payload"] = {
            "title": "Test Notification",
            "body": "This is a test push notification from the Push Service",
            "data": {
                "link": "https://example.com/test"
            }
        }
    
    print(f"Publishing test event: {json.dumps(event, indent=2)}")
    
    try:
        # Parse RabbitMQ URL properly using urllib
        parsed_url = urlparse(config.RABBITMQ_URL)
        
        # Extract credentials
        if parsed_url.username and parsed_url.password:
            credentials = pika.PlainCredentials(parsed_url.username, parsed_url.password)
        else:
            credentials = pika.PlainCredentials('guest', 'guest')
        
        # Extract host and port
        host = parsed_url.hostname
        port = parsed_url.port or 5672  # Default RabbitMQ port
        
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=host, port=port, credentials=credentials)
        )
        channel = connection.channel()

        # Try a passive declare first to verify the queue exists without changing its arguments.
        # Passive declare will raise a broker error if the queue exists but with incompatible arguments
        # (e.g. different x-dead-letter-exchange). In that case we reopen a fresh channel and
        # publish without declaring to avoid PRECONDITION_FAILED.
        try:
            channel.queue_declare(queue=config.PUSH_QUEUE, passive=True)
        except pika.exceptions.ChannelClosedByBroker as e:
            # Channel was closed by broker due to argument mismatch (406) or not found (404).
            print(f"⚠️ Passive queue check failed (may be mismatched args): {e}. Proceeding to publish without declaring the queue.")
            # Recreate connection/channel if the channel was closed
            if connection.is_closed:
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=host, port=port, credentials=credentials)
                )
            channel = connection.channel()
        except Exception as e:
            # Any other error shouldn't block publishing; warn and continue
            print(f"⚠️ Unexpected error during passive queue check: {e}. Proceeding to publish.")

        # Publish message (don't attempt to declare queue with potentially different args)
        channel.basic_publish(
            exchange='',
            routing_key=config.PUSH_QUEUE,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )
        
        print(f"✅ Message published to {config.PUSH_QUEUE}")
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to publish message: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser(description="Publish a test push event to RabbitMQ")
    ap.add_argument("--user-id", type=int, default=123, help="User ID for the notification")
    ap.add_argument("--event-id", default=None, help="Event ID (auto-generated if not provided)")
    ap.add_argument("--template", default=None, help="Template code (e.g., 'welcome_v1')")
    ap.add_argument("--message", default="Test notification", help="Message body for inline payload")
    ap.add_argument("--title", default="Test Notification", help="Message title for inline payload")
    
    args = ap.parse_args()
    
    inline = {
        "title": args.title,
        "body": args.message,
        "data": {"link": "https://example.com/test"}
    } if not args.template else None
    
    success = publish_test_event(
        user_id=args.user_id,
        event_id=args.event_id,
        template_code=args.template,
        inline_payload=inline
    )
    
    sys.exit(0 if success else 1)
