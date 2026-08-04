"""Test package. Keeps igwatch's logging out of the test output."""

import logging

for _name in ("igwatch", "igwatch.watch", "igwatch.notify", "igwatch.state"):
    logging.getLogger(_name).setLevel(logging.CRITICAL)
