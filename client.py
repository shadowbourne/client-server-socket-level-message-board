#importing libraries.
import socket
import sys
#setting server address and port to those supplied upon the caling of the client.
serv_address = (sys.argv[1], int(sys.argv[2]))

#function that is called in order to send data to the server via first establishing a connection and then sending the data with its length added to the beginning split on the delimiter "|".
def SEND(msg):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(serv_address)
    except ConnectionRefusedError:
        print('ERROR: Server is not available. Client exiting..')
        sys.exit()
    sock.sendall('{}|{}'.format(len(msg), msg).encode())
    return sock

#function to receive data from the client, first receives initial chunk containing message length, splitting on the delimiter '|' and then sets up a loop for remaining data.
def RECV(sock):
    sock.settimeout(10)
    msg = b''
    try:
        part_1 = sock.recv(16)
        length = part_1.split(b'|')[0]
        msg += part_1[len(length)+1:]
        if len(part_1)-len(length)-1 < int(length):
            while len(msg) < int(length):
                chunk = sock.recv(64)
                if not chunk:
                    print('ERROR: Connection to server lost. Client exiting..')
                    sys.exit()
                msg += chunk
        return msg
    except socket.timeout:
        print('ERROR: Server request timed out. Client exiting..')
        sys.exit()
#function called in order to verify that a string is made up of only alphanumeric characters, spaces or "_"s.
def CHECK_ALNUM_UNDERSCORE(string):
    for i in range(len(string)):
        if not (string[i].isalnum() or string[i] == " " or string[i] == "_"):
            return False
    return True

#function called in order to request and then print the most recent 100 messages in a particular board from the server.
def GET_MESSAGES(board_number):
    sock = SEND("GET_MESSAGES|{}".format(board_number))
    reply = RECV(sock)
    if reply:
        return reply.decode()
    else:
        return "No messages in board {}.".format(board_number)

#function called in order to post a message along with its title to a particular board number on the server.
def POST(board_number, message_title, message_content):
    #if statement checking message title does not contain any "|"s, catching the one error that the server cannot check for.
    if not "|" in message_title:
        sock = SEND("POST|"+str(board_number)+"|"+message_title+"|"+message_content)
        return RECV(sock).decode()
    #informing the server of this error in the aim to keep consistency for which cases of errors end up being logged by the server.
    else:
        sock = SEND("POST|"+board_number+"|"+'ERROR:%$^ non alphanumeric input'+"|"+message_content)
        return RECV(sock).decode()

#function called (on startup) in order to get the available boards from the server and then ask for what the user would like to do (GET_MESSAGES, POST or QUIT).
def GET_BOARDS():
    #asking server for available boards.
    sock = SEND('GET_BOARDS')
    message = RECV(sock)
    if message == b'ERROR':
        print("Error: No boards available...")
        sock.close()
        sys.exit()
    sock.close()
    message = message.decode()
    message_no_underscores = ''
    length_of_message = len(message)
    max_board = 0
    max_board_lst = []
    #part of function which turns all "_"s in the received string into spaces.
    for i in range(length_of_message-1):
        if message[i] != '_':
            message_no_underscores += message[i]
        else:
            message_no_underscores += " "
    #part of code dedicated to working out the maximum board number received.

    #function that recursively checks how many characters before and including an index position are digits and returns this number (the maximum board number).
    def IS_BOARD_NUMBER(i, max_board_lst):
        #check if character in index position i is a digit
        if message[i].isdigit():
            # if so check if character in the previous position is also a digit after adding this digit to a list used at end to construct output number.
            max_board_lst += message[i]
            return IS_BOARD_NUMBER(i-1, max_board_lst)
        #if not return this list in reverse joined together on the empty string (which constructs the maximum board number).
        else:
            return "".join(max_board_lst[::-1])
    #for the character closest to the end of the message that is a "." preceeded by a digit, call the function is_board_number in order to get the full number (which is the max_board_number). [the break in the for loop means only the "(0-9)." closest to the end of the message is checked.
    for i in range(length_of_message-1):
        if message[length_of_message-i-1] == "." and message[length_of_message-i-2].isdigit():
            max_board = int(IS_BOARD_NUMBER(length_of_message-i-2, max_board_lst))
            break
    #a set of while loops and functions containing while loops that contain code to allow users to input their desired option, and will allow them to try again at whatever stage they are at if their input is incorrect and this error is caught client side (see print statements for error details).
    while True:
        
        print(message_no_underscores+"\n")
        INPUT = input("Please either:\n- Enter the board number of the board which you would like to view the most recent 100 messages of.\n- Enter POST if you would like to post a message to any of the available boards.\n- Enter QUIT if you would like exit the client.\n:> ")
        #checks if the input is a digit, then if this digit is between 1 and the maximum board number, if so sends a GET_MESSAGES request to the server.
        if INPUT.isdigit():
            if int(INPUT) <= max_board and INPUT != "0":
                reply = GET_MESSAGES(INPUT)
                print(reply)
                reply_split = reply.split(":")
                #if error returned then continue waiting for user input
                if reply_split[0] != "ERROR":
                    break
                    
            else:
                print("ERROR: Sorry, this is not a valid number, please try again:\n")

        
        elif INPUT == "POST":
            def LOOP_FUNCTION():
                while True:
                    board_number = input("- Please enter the board number of the board which you would like to post a message in:\n:>")
                    #checks if the input is a digit, then if this digit is between 1 and the maximum board number, if so allowing the user into the next while loop.
                    if board_number.isdigit():
                        if int(board_number) <= max_board and board_number != "0":
                            while True:
                                message_title = input("- Please enter the title of this message:\n:>")
                                #checks if input is not an empty string, and then that is it made up of only alphanumeric characters, spaces and "_"s, if so allowing the user into the next while loop.
                                if message_title:
                                    if CHECK_ALNUM_UNDERSCORE(message_title):
                                        while True:
                                            print(message_title)
                                            message_content = input("- Please enter the message content:\n:>")
                                            #checks if input is not an empty string, and then that it does not contain "\n" and therefore that it is one line of text, if so sending an appropriate POST request to the server and exiting all while loops by returning from the function.
                                            if message_content:
                                                if not "\n" in message_content:
                                                    reply = POST(board_number, message_title, message_content)
                                                    print(reply)
                                                    reply_split = reply.split(":")
                                                    #if error returned then restart LOOP_FUNCTION
                                                    if reply_split[0] == "ERROR":
                                                        LOOP_FUNCTION()
                                                    else:    
                                                        return
                                                else:
                                                    print("ERROR: Sorry, input must be one line of text, please try again:")
                                            else:
                                                print("ERROR: No message content entered, please try again:")
                                    else:
                                        print("ERROR: Sorry this is not a valid alphanumeric input, please try again:")
                                else:
                                    print("ERROR: No message title entered, please try again:")
                        else:
                            print("ERROR: Sorry this is not a valid number, please try again:")
                    else:
                        print("ERROR: Sorry this is not a valid number, please try again:")
            #part of code which calls to function in order to enter the first the while loop.
            LOOP_FUNCTION()
            break

        #quits the UI and all loops, quitting the program.
        elif INPUT == "QUIT":
            sock.close()
            sys.exit()

        else:
            print("ERROR: Sorry, this is not a valid input, please try again:\n")


#part of code which is run at startup after all setting up has occurred, in order to get the boards from server and then wait for user input (using the loops section of the code above).       
GET_BOARDS()

