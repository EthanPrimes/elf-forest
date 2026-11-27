"""
Display game objects and classes.
"""
import classes
import random
import subprocess
import sys
from time import sleep

def deactivate_cursor():
    subprocess.run(["printf", "\033[?25l"])

def reactivate_cursor():
    subprocess.run(["echo", "\033[?25h"])

def map_to_string(map: classes.Map):
    """
    Turns a map object into a string.
    """
    return None


if __name__ == "__main__":
    CHARS = ["\033[92mT\033[0m", "Y", "_", " ", "\033[91mM\033[0m"]
    N = 8
    map =[[random.choice(CHARS) for _ in range(N)] for _ in range(N)]
    try:
        deactivate_cursor()
        while True:
            subprocess.run(["clear; clear"], shell=True)
            map_string = "\n".join(["".join(row) for row in map])
            print(map_string)
            map[random.randint(0, N - 1)][random.randint(0, N - 1)] = random.choice(CHARS)
            sleep(1)
    finally:
        reactivate_cursor()
