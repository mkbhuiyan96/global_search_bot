import os
import logging

root_logger_set = False

def setup_logger(logger_name, filename):
    global root_logger_set

    if not os.path.exists('logs'):
        os.makedirs('logs')

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(os.path.join('logs', filename))
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if not root_logger_set:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        logging.getLogger().addHandler(stream_handler)
        root_logger_set = True
    return logger
