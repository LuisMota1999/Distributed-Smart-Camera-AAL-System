import uuid
import random


def generate_unique_id() -> int:
    """
    Generate a unique identifier by generating a UUID and selecting 10 random digits.

    :return: An integer representing the unique identifier.
    """
    # Generate a UUID and convert it to a string
    uuid_str = str(uuid.uuid4())

    # Remove the hyphens and select 10 random digits
    digits = ''.join(random.choice(uuid_str.replace('-', '')) for _ in range(10))

    return int(digits)

