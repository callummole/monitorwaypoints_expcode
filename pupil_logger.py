import zmq
import msgpack
import json
import time
import threading

def start_logging(logfile, host="192.168.0.2", port=50020, timestamper=time.time):
    ctx = zmq.Context()

    # We need to first request the port for the subscriber.
    # A bit of a hassle, but should be quite clear.
    req = ctx.socket(zmq.REQ)
    req.connect("tcp://%s:%i"%(host, port))
    req.send(b'SUB_PORT')
    sub_port = int(req.recv())
    req.close()

    sub = ctx.socket(zmq.SUB)
    sub.connect("tcp://%s:%i"%(host, sub_port))
    sub.setsockopt(zmq.SUBSCRIBE, '')
    def do_log():
        while True:
            try:
                topic, msg = sub.recv_multipart()
            except zmq.ContextTerminated:
                break
            # TODO: We could just "pass through" the msgpack
            # to save some CPU.
            logfile.write(
                json.dumps((topic, timestamper(), msgpack.loads(msg)))
            )
            logfile.write('\n')
    
    thread = threading.Thread(target=do_log)
    def stop_logging():
        ctx.term()
        thread.join()
    thread.start()
    return stop_logging

if __name__ == '__main__':
    import sys
    import time
    import gzip
    f = gzip.open("test.jsons.gz", "w")
    stop = start_logging(f)
    time.sleep(1)
    stop()
