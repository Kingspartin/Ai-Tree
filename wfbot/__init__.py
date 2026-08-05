"""wfbot - an automated warframe.market trading assistant.

The package automates the market side of Warframe trading: pulling order books
and price history from warframe.market, ranking profitable opportunities, and
keeping your own listings competitively priced.

It deliberately does not automate the Warframe game client. Item and platinum
transfer only ever happens in-game between two present players, and driving the
client with synthetic input violates Digital Extremes' EULA.
"""

__version__ = "0.1.0"

USER_AGENT = f"wfbot/{__version__} (+https://github.com/kingspartin/ai-tree)"
