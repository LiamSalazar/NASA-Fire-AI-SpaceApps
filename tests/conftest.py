"""Tests never reach a live provider and run windows one at a time.

Scientific stages stay on NVIDIA with no Anthropic key; a test that needs
concurrency sets it itself.
"""

import os

# Set before nasa_fire_ai.config loads .env, which never overrides a set variable.
os.environ["SCIENCE_PROVIDER"] = "nvidia"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["SCIENCE_WINDOW_CONCURRENCY"] = "1"
