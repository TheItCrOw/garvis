import time


def log_message(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)
