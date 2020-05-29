#import modules
import socket
import sys
import threading
import os
from datetime import datetime
#changes directory to correct directory
os.chdir(os.path.realpath(__file__).strip('server.py'))
#check if boards are defined and if not print error and exit

boards = list(os.walk('board'))[0][1]
max_board_number = len(boards)
if max_board_number == 0:
    print('ERROR: No message boards defined.')
    sys.exit()
#try to bind server to given address and port and begin listening, if busy port print error and exit
serv_address= (sys.argv[1], int(sys.argv[2]))
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(serv_address)
except OSError as e:
    if str(e) != '[WinError 10048] Only one usage of each socket address (protocol/network address/port) is normally permitted':
        raise
    else:
        print('ERROR: Unavailable/busy port.')
        sys.exit()
sock.listen(5)

#function to send data, with delimited length of message added before message so that receiver knows how much data to expect
def SEND(msg):
    connection.sendall('{}|{}'.format(len(msg), msg).encode())
    
#function to receive data from the client, first receives initial chunk containing message length, splitting on the delimiter '|' and then sets up a loop for remaining data
def RECV(connection):
    msg = b''
    part_1 = connection.recv(16)
    length = part_1.split(b'|')[0]
    msg += part_1[len(length)+1:]
    if len(part_1)-len(length)-1 < int(length):
        while len(msg) < int(length):
            chunk = connection.recv(64)
            if not chunk:
                print('ERROR: Connection to client lost mid transmission.')
                SEND('ERROR: Connection lost mid transmission, please try again.')
                LOG(datetime.now(), 'UNDEFINED_COMMAND: CONNECTION LOST MID TRANSMISSION', 'Error')
                sys.exit()
            msg += chunk
    return [datetime.now(), msg]

#function called to append logging info to log file
def LOG(time_of_message, command_type, outcome):
    log = open('server.log', 'a')
    log.write(str(client_address[0])+':'+str(client_address[1])+'\t'+str(time_of_message).split('.')[0]+'\t'+command_type+'\t'+outcome+'\n')
    log.close()
    
#function called in order to verify that a string is made up of only alphanumeric characters, spaces or "_"s
def CHECK_ALNUM_UNDERSCORE(string):
    string = string.decode()
    for i in range(len(string)):
        if not (string[i].isalnum() or string[i] == " " or string[i] == "_"):
            return False
    return True

#function called to convert all spaces in a string into '_'s
def SPACE_TO_UNDERSCORE(string):
    if type(string) == bytes:
        string = string.decode()
    new_string_list = []
    for i in range(len(string)):
        if string[i] == " ":
            new_string_list += "_"
        else:
            new_string_list += string[i]
    return "".join(new_string_list)

#function called to convert all '_'s in a string into spaces
def UNDERSCORE_TO_SPACE(string):
    if type(string) == bytes:
        string = string.decode()
    new_string_list = []
    for i in range(len(string)):
        if string[i] == "_":
            new_string_list += " "
        else:
            new_string_list += string[i]
    return "".join(new_string_list)
#function called when a GET_BOARDS request is received. This function will output a numbered list of the subfolders in the board directory as a string.
def GET_BOARDS(time_of_message):
    boards = list(os.walk('board'))[0][1]
    max_board_number = len(boards)
    if max_board_number == 0:
        print('ERROR: No message boards defined.')
        LOG(time_of_message, 'GET_BOARDS', 'Error')
        SEND('ERROR')
        sys.exit()
    numbered_boards = ""
    for i in range(len(boards)):
        numbered_boards += "{}. ".format(i+1)+str(boards[i])+" "
    LOG(time_of_message, 'GET_BOARDS', 'OK')
    return numbered_boards
#function called when a POST request is recieved from the client. This function will verify inputs are in the correct format, 
#returning an error message if not, and if so will create a message file in the corresponding message board folder.
#for details on the various if error statements, consult their associated else print statements
def POST(board_number, message_title, message_content, time_of_message):
    if board_number.isdigit():
        if int(board_number) <= max_board_number and int(board_number) > 0:
            if message_title:
                if CHECK_ALNUM_UNDERSCORE(message_title):
                    message_title = SPACE_TO_UNDERSCORE(message_title)
                    if message_content:
                        if not "\n" in message_content.decode():
                            #part of function to get all the individual desired parts of the file name to be created
                            board_title = boards[int(board_number)-1]
                            split_time = str(time_of_message).split(" ")
                            date_only = split_time[0]
                            time_only = split_time[1].split(".")[0]
                            concatenated_date = ''.join(date_only.split("-"))
                            concatenated_time = ''.join(time_only.split(":"))
                            #the creation of this file name
                            file_name = concatenated_date+'-'+concatenated_time+'-'+message_title
                            path_to_open = os.path.join("board", board_title, file_name)
                            file = open(path_to_open, "w")
                            file.write(message_content.decode())
                            file.close()
                            SEND('SUCCESS: Your message has been successfully posted.')
                            LOG(time_of_message, 'POST', 'OK')
                            return
                        else:
                            SEND('ERROR: Message content must be all on one line.')
                    else:
                        SEND('ERROR: No message content given.')
                else:
                    SEND('ERROR: Board title contains a character that is not alphanumeric or " " or "_".')
            else:
                SEND('ERROR: No board title given.')
        else:
            SEND('ERROR: Specified board number does not exist.')
    else:
        SEND('ERROR: Board number must be a positive number.')
    LOG(time_of_message, 'POST', 'Error')

#function called when a GET_MESSAGES request is received from the client. This function will verify inputs are in the correct format, 
#returning an error message if not, and if so will return the most recent 100 messages within the desired message board folder
#as a list with their corresponding message titles and timestamps displayed in front
def GET_MESSAGES(board_number, time_of_message):
    boards = list(os.walk('board'))[0][1]
    max_board_number = len(boards)
    if board_number.isdigit():
        if int(board_number) <= max_board_number and int(board_number) > 0:
            boards = list(os.walk('board'))[0][1]
            board_title = boards[int(board_number)-1]
            path_to_walk = os.path.join('board', board_title)
            message_names_in_folder = list(os.walk(path_to_walk))[0][2]
            all_messages = ''
            number_of_messages = len(message_names_in_folder)
            number_of_old_messages = 0
            if number_of_messages > 100:
                number_of_old_messages = number_of_messages-100
                number_of_messages = 100
            for i in range(number_of_messages):
                #part of function to get all the individual desired parts of the message to be sent
                path_to_open = os.path.join("board", board_title, message_names_in_folder[number_of_old_messages+i])
                message_file = open(path_to_open)
                message = message_file.read()
                split_date_time_name = message_names_in_folder[number_of_old_messages+i].split('-')
                date = split_date_time_name[0][:4]+'-'+split_date_time_name[0][4:6]+'-'+split_date_time_name[0][6:]
                time = split_date_time_name[1][:2]+':'+split_date_time_name[1][2:4]+':'+split_date_time_name[1][4:]
                name = split_date_time_name[2]
                name = UNDERSCORE_TO_SPACE(name)
                #the appending of this message to a string with all previous messages already processed
                all_messages += date+' '+time+" '"+name+"' : '"+message+"'\n"
            SEND(all_messages)
            LOG(time_of_message, 'GET_MESSAGES', 'OK')
            return
        else:
            SEND('ERROR: Specified board number does not exist.')
    else:
        SEND('ERROR: Board number must be a positive number.')
    LOG(time_of_message, 'GET_MESSAGES', 'Error')

#the thread function called whenever a client attempts to make a connection with the server. This function will recieve the clients request input and call other functions to respond accordingly.
def THRD(connection, client_address):
    [time_of_message, msg] = RECV(connection)
    #part of function that splits the received string (bytes) into the request type (msg[0]) and up to 3 parameters on the delimiter '|'
    msg = msg.split(b'|', 3)
    
    if msg[0] == b'GET_BOARDS':
        if len(msg) == 1:
            SEND(GET_BOARDS(time_of_message))
        else:
            SEND('ERROR: Wrong number of parameters. GET_BOARDS requires no parameters')
            LOG(time_of_message, 'GET_BOARDS', 'Error')
        
    elif msg[0] == b'GET_MESSAGES':
        if len(msg) == 2:
            GET_MESSAGES(msg[1], time_of_message)
        else:
            SEND('ERROR: Wrong number of parameters. GET_MESSAGES requires a single parameter, the message board number (e.g. "GET_MESSAGES|a")')
            LOG(time_of_message, 'GET_MESSAGES', 'Error')
    
    elif msg[0] == b'POST':
        if len(msg) == 4:
            POST(msg[1], msg[2], msg[3], time_of_message)
        else:
            SEND('ERROR: Wrong number of parameters. POST requires 3 parameters, board number, message title and message content all seperated by a | (e.g. "POST|a|b|c"')
            LOG(time_of_message, 'POST', 'Error')
    else:
        SEND('ERROR: Undefined command')
        LOG(time_of_message, 'UNDEFINED_COMMAND: ("{}")'.format(msg[0].decode()), 'Error')
    
    connection.close()


#The part of the code that is run in a loop after setup of all functions and libraries is completed.
#this loop will constantly wait for new clients to attempt to connect and send a request, and will call the threading function to deal with these requests.
#once the individual request has been dealt with, the connection and thread will be closed.
while True:

    connection, client_address = sock.accept()        
    thread = threading.Thread(target=THRD, args=(connection, client_address, ))
    thread.start()
    
    
