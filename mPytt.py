import paho.mqtt.client as mqtt
import json
import base64
import argparse
import signal
import sys
import os
import time
import threading
from pygments import highlight, lexers, formatters

""" Colors """
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

""" Global variables """
client = None
save_file = None
message_file = None

""" Args """
parser = argparse.ArgumentParser()
parser.add_argument("host", help="Hostname to connect")
parser.add_argument("-p", "--port", help="You can specify the port of the server")
parser.add_argument("--publish", action="store_true")
parser.add_argument("-t", "--topic", help="topic to subscribe, # if not specified", default="#")
parser.add_argument("-k", "--key", help="You can specify the part of the payload you want to see by specifying the key", nargs='+')
parser.add_argument("-d", "--decode", help="You can decode some data by specifying the key", nargs='+')
parser.add_argument("-r", "--raw", help="raw output", action="store_true")
parser.add_argument("-s", "--save", help="save raw output in a file, the file will be create automatically", action="store_true")
parser.add_argument("-m", "--message", help="message to publish")
parser.add_argument("--payload", help="payload to send to the server")
parser.add_argument("-f", "--file", help="payload from file")
parser.add_argument("-l", "--loop", help="specify the interval between each message - seconds", type=int)


args = parser.parse_args()

""" Handle control-C to quit function """
def signal_handler(signal, frame):
    global message_file
    global save_file
    if isinstance(client, mqtt.Client):
        # disconnect the client if connected
        client.disconnect()
    if save_file is not None:
        # close the file if open
        save_file.close()
    if message_file is not None:
        # close the file if open
        message_file.close()
    print('\n------------------------')
    print("Exiting program...")
    print('------------------------')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

""" Argument management """
host = args.host
topic = args.topic
key_data = list()
encoded_data = list()
port = None

if args.port:
    port = args.port

if args.key:
    for d in args.key:
        key_data.append(d)

if args.decode:
    encoded_data = args.decode
    for d in args.decode:
        key_data.append(d)

""" Banner function """
def print_banner():
    print(f"{bcolors.OKBLUE}           ____        _   _   {bcolors.ENDC}")
    print(f"{bcolors.OKBLUE} _ __ ___ |  _ \ _   _| |_| |_ {bcolors.ENDC}")
    print(f"{bcolors.OKBLUE}| '_ ` _ \| |_) | | | | __| __|{bcolors.ENDC}")
    print(f"{bcolors.OKBLUE}| | | | | |  __/| |_| | |_| |_ {bcolors.ENDC}")
    print(f"{bcolors.OKBLUE}|_| |_| |_|_|    \__, |\__|\__|{bcolors.ENDC}")
    print(f"{bcolors.OKBLUE}                 |___/         {bcolors.ENDC}")
    print("-------------------------------")
    print(f"|  Made by {bcolors.BOLD}@vnch31 & @justine-b{bcolors.ENDC} |")
    print("-------------------------------")


""" File functions """
def create_save_file():
    global save_file
    h = time.time()
    name = f'mpytt{h}.txt'
    try:
        save_file = open(name, "w+")
    except IOError as e:
        print (e)
    print(f'{bcolors.OKGREEN}[+] File {name} created {bcolors.ENDC}')

def save_to_file(payload, writer):
    payload = str(payload)
    try:
        writer.write(payload)
        writer.write("\n")
    except IOError as e:
        print (e)

def send_from_file(client, reader):
    reader.seek(0)
    payload = reader.read()
    print(f"{bcolors.OKGREEN}[+] Sending payload : {bcolors.ENDC}")
    print(payload)
    client.publish(topic, payload)


""" Processing functions """
def clean_data(payload, new_payload, selected, encoded):
    if encoded:
        for k,v in payload.items():        
            if isinstance(v, dict):
                clean_data(v, new_payload)
            else:
                if k in selected:
                    if k in encoded:
                        try:
                            new_value = base64.b64decode(v)
                            new_value = new_value.decode('utf-8')
                            new_payload[k] = new_value
                        except:           
                            print(f"{bcolors.FAIL}[-]Unable to decode {k} value : non base64 data{bcolors.ENDC}")
                            new_payload[k] = v
                    else:
                        new_payload[k] = v
    else:
        for k,v in payload.items():        
            if isinstance(v, dict):
                clean_data(v, new_payload)
            else:
                if k in selected:
                    new_payload[k] = v


""" MQTT callbacks functions """
            
def on_connect(client, userdata, flags, rc):
    """ Function that is called when the client is connected to the server """
    client.subscribe(topic)

def on_subscribe(client, userdata, mid, granted_qos):
    if mid != 0:
        print(f"{bcolors.OKGREEN}[+] Subscribe to {topic} successfull{bcolors.ENDC}")
    else:
        print(f"{bcolors.FAIL}[-] Error on subscribing {topic}{bcolors.ENDC}")
        print(f"{bcolors.FAIL}[-] Exiting programm....{bcolors.ENDC}")
        exit(1)

def on_message(client, userdata, msg):
    """ Function that is called when the client receive a message """
    if not args.raw:
        print(f"{bcolors.OKGREEN}[+]Topic : {bcolors.ENDC}"+f"{msg.topic}")
    new_msg = msg.payload.decode('utf-8')
    if args.raw:
        print(new_msg)
        return
    try:
        payload = json.loads(new_msg)
    except json.JSONDecodeError as e:
        print(f'{bcolors.FAIL}{e}{bcolors.FAIL}')
        print(f'{bcolors.FAIL} Data received not in JSON change options if not JSON{bcolors.ENDC}')
    if len(key_data) > 0:
        new_payload = dict()
        clean_data(payload, new_payload, key_data, encoded_data)
        if new_payload:
            colorful_json = highlight(json.dumps(new_payload, indent=4), lexers.JsonLexer(), formatters.TerminalFormatter())
            print(colorful_json)
            if args.save:
                save_to_file(new_payload, save_file)
        else:
            if not args.raw:
                print(f"{bcolors.FAIL}[-]No data found for key : {key_data}{bcolors.ENDC}")
    # if data key not specified
    else:
        colorful_json = highlight(json.dumps(payload, indent=4), lexers.JsonLexer(), formatters.TerminalFormatter())
        print(colorful_json)        
        if args.save:
            save_to_file(new_msg, save_file)

def on_publish(client, userdata, message):
    print(f"{bcolors.OKGREEN}[+] Message published on topic : {message.topic}{bcolors.ENDC}")

""" Main functionnality """

def subscribe():
    if not args.raw:
        print_banner()
    if args.save:
        create_save_file()
    client = mqtt.Client("Subscriber")
    # define callbacks function
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe

    # connection to server
    if port:
        client.connect(host=host, port=port)
    else:
        client.connect(host=host)

    client.loop_forever()

def publish():
    # global var
    global message_file
    if not args.raw:
        print_banner()
    client = mqtt.Client("Publisher")

    # define callbacks function
    client.on_publish = on_publish

    # connection to server
    if port:
        client.connect(host=host, port=port)
    else:
        client.connect(host=host)
    if args.payload or args.file:
        if args.file:
            # open the message file
            try:
                message_file = open(args.file)
                if args.loop:
                    # the file will be closed with CTRL^C handler function
                    while True:
                        send_from_file(client, message_file)
                        time.sleep(args.loop)
                else:
                    send_from_file(client, message_file)
                # close the message file 
                message_file.close()
            except IOError as e:
                print(f"{bcolors.FAIL}[-] An error occured with the file :  \n {e}{bcolors.ENDC}")
        else:
            if args.loop:
                while True:
                    client.publish(topic, args.payload)
                    time.sleep(args.loop)
            else:
                client.publish(topic, args.payload)
    else:
        print(f"{bcolors.FAIL}[-]Error, you must specify a payload --payload or a file -f --file{bcolors.ENDC}")



""" Main """

def main():
    if args.publish:
        publish()
    else:
        subscribe()

if __name__ == "__main__":
    main()
    
