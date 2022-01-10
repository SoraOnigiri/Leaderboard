# settings.py
import os
from os.path import join, dirname
from dotenv import load_dotenv

path = join(dirname(__file__), "..")
dotenv_path = join(path, ".env")
load_dotenv(dotenv_path)
