import os
import logging

def setup_logger(filename):
    if not os.path.exists('logs'):
        os.makedirs('logs')

    logging.basicConfig(filename=os.path.join('logs', filename),
                        filemode='a',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)