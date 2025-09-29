from socket import gethostbyname, gethostname

# check for internet
internet_connection = False
def check_internet_status():
    global internet_connection
    my_ip = gethostbyname(gethostname())
    internet_connection = False
    if my_ip != "127.0.0.1":
        internet_connection = True
    return internet_connection