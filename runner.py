from __future__ import annotations
from dotenv import load_dotenv
from agent import build_agent


load_dotenv(".env", override=True)
agent = build_agent()

