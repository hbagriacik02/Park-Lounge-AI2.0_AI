import time

def wait_connection_time(wait_time, interval=1, counter=0):
    while counter < wait_time:
        #print("Service waiting camera setup ...")
        time.sleep(interval)
        counter += interval