from socket import *
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8

total_pings = 0
num_failed = 0
rtt_times = []



def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0
    while count < countTo:
        thisVal = string[count+1] * 256 + string[count]
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2
        
    if countTo < len(string):
        csum = csum + string[len(string) - 1]
        csum = csum & 0xffffffff
        
    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def statistics():
    global total_pings
    global num_failed
    global rtt_times
    if len(rtt_times):
        min_rtt = min(rtt_times)
        max_rtt = max(rtt_times)
        avg_rtt = sum(rtt_times)/len(rtt_times)
    else: 
        min_rtt = 0
        max_rtt = 0
        avg_rtt = 0
    loss = (num_failed/total_pings)*100
    print("")
    print("Min: "+str(min_rtt*1000)+" ms")
    print("Avg: "+str(avg_rtt*1000)+" ms")
    print("Max: "+str(max_rtt*1000)+" ms")
    print("Packet loss: " + str(loss)+"%")
    return




def receiveOnePing(mySocket, ID, timeout, destAddr):
    global total_pings
    global num_failed
    global rtt_times
    timeLeft = timeout
    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        #print(whatReady[0])
        if whatReady[0] == []: # Timeout
            num_failed+=1
            return "Request timed out."
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)
        #Fill in start
        #Fetch the ICMP header from the IP packet
        header = struct.unpack_from("bbHHhd", recPacket,20)
        rtt = header[5]
        rtt = (startedSelect - rtt) + howLongInSelect
        rtt_times.append(rtt)
        total_pings += 1
        return(str(rtt*1000) +" ms")

        #Fill in end

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            num_failed+= 1
            return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    # Note that the numbers in parentheses are not values, but sizes in bits
    myChecksum = 0

    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)
    
    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data
    
    mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")
    
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF # Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay

def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    dest = gethostbyname(host)
    print("Pinging host: " + host + " at: " + dest + " using Python:")
    print("")

    # Send ping requests to a server separated by approximately one second
    while 1 :
        delay = doOnePing(dest, timeout)
        print(delay)
        time.sleep(1)# one second
    return delay

if __name__ == "__main__":
    try:
        host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
        ping(host)
    except KeyboardInterrupt:
        statistics()
        sys.exit()