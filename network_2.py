'''
Created on Oct 12, 2016
@author: mwitt_000
'''
import queue
import threading


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.queue = queue.Queue(maxsize);
        self.mtu = None

    ##get packet from the queue interface
    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None

    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, block=False):
        self.queue.put(pkt, block)

## Implements a network layer packet (different from the RDT packet
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.

# ---------------------------------------------------------------------------------------------- #
# TODO modify class to implement segmentation and reconstruction
# using flag and offset?

class NetworkPacket:
    ## packet encoding lengths
    dst_addr_S_length = 5

    # initialize flag and offset
    flag_S_length = 1
    offset_S_length = 2

    ##@param dst_addr: address of the destination host
    # @param data_S: packet payload

    # add new variables to constructor
    def __init__(self, dst_addr, data_S, flag = 0, offset = 0):
        self.dst_addr = dst_addr
        self.data_S = data_S
        self.flag = flag
        self.offset = offset

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst_addr).zfill(self.dst_addr_S_length)
        # add offset and flag values to the byte string if the packet needs to be seperated
        if(self.flag != 0):
            # fill with zeroes before the flag value
            byte_S += str(self.flag).zfill(self.flag_S_length)
            byte_S += str(self.offset).zfill(self.offset_S_length)
        byte_S += self.data_S
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod

    def from_byte_S(self, mtu, byte_S):
        dst_addr = int(byte_S[0 : NetworkPacket.dst_addr_S_length])
        data_S = byte_S[NetworkPacket.dst_addr_S_length : ]

        # initialize fragmented flag and offset to 0 to begin
        frag = 0
        off_set = 0
        #initialize an empty fragmented packet
        fragmented_pkt = []

        # if the packet has flag and offset and is greater than mtu
        if(NetworkPacket.flag_S_length + NetworkPacket.offset_S_length + len(data_S[off_set:]) > mtu):
            # set as fragmented
            frag = 1
            # while there is data past the offset keep fragmenting otherwise set the next offset
            while(len(data_S[off_set:]) != 0):
                # test var
                total_len = len(data_S[off_set:]) + NetworkPacket.flag_S_length + NetworkPacket.offset_S_length

                if(len(data_S[off_set:]) + NetworkPacket.flag_S_length + NetworkPacket.offset_S_length < mtu or len(data_S[off_set:]) + NetworkPacket.flag_S_length + NetworkPacket.offset_S_length == mtu):
                    frag = 0
                # set next offset and remove frag flag and previous offset
                next_offset = off_set + mtu - self.flag_S_length - self.offset_S_length
                fragmented_pkt.append(self(dst_addr, data_S[off_set:next_offset], frag, off_set))
                off_set = next_offset
            return fragmented_pkt
        
        # else return normally using new flags
        else:
            return self(dst_addr, data_S, frag, off_set)

    # ------------------------------------------------------------------------------------------------ #


## Implements a network host for receiving and transmitting data
class Host:

    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False #for thread termination

    ## called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)

    ## create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer

    # --------------------------------------------------------------------------------------------------------- #
    # TODO Split packet in two

    def udt_send(self, dst_addr, data_S):
        #if packet size is larger than mtu
        if(len(data_S) > self.out_intf_L[0].mtu):
            
            # subtract dist_addr from mtu to get actual allowed length
            l = self.out_intf_L[0].mtu - 5
            # create 2 packets
            p1 = NetworkPacket(dst_addr, data_S[0:l])
            p2 = NetworkPacket(dst_addr, data_S[l:])

            self.out_intf_L[0].put(p1.to_byte_S()) #send packets always enqueued successfully
            print('%s: sending packet "%s" out interface with mtu=%d' % (self, p1, self.out_intf_L[0].mtu))
            self.out_intf_L[0].put(p2.to_byte_S()) #send packets always enqueued successfully
            # will not enumerate second packet with 'self'
            print('%s: sending packet "%s" out interface with mtu=%d' % (self, p2, self.out_intf_L[0].mtu))
        
        # otherwise send normally
        else:
            p = NetworkPacket(dst_addr, data_S)
            self.out_intf_L[0].put(p.to_byte_S())  # send packets always enqueued successfully
            print('%s: sending packet "%s" out interface with mtu=%d' % (self, p, self.out_intf_L[0].mtu))

    # --------------------------------------------------------------------------------------------------------- #


    # now need to recieve the fragmented packets
    fragmented_pkt = []
    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.in_intf_L[0].get()
        if pkt_S is not None:
            # if its just one packet, not fragmented
            if(pkt_S[NetworkPacket.dst_addr_S_length] == '1'):
                self.fragmented_pkt.append(pkt_S[NetworkPacket.dst_addr_S_length + NetworkPacket.flag_S_length + NetworkPacket.offset_S_length:])
            # else join the incoming packets
            else:
                self.fragmented_pkt.append(pkt_S[NetworkPacket.dst_addr_S_length:])
                print('%s: --recieved-- packet "%s"' % (self, ''.join(self.fragmented_pkt)))
                self.fragmented_pkt.clear()

            print('%s: --recieved-- packet "%s"' % (self, pkt_S))

    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return



## Implements a multi-interface router described in class
class Router:

    ##@param name: friendly router name for debugging
    # @param intf_count: the number of input and output interfaces
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_count, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]

    ## called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    ## look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):

        '''
        '''

        # set mtu to 30
        self.out_intf_L[0].mtu = 30


        for i in range(len(self.in_intf_L)):
            pkt_S = None
            try:
                #get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                #if packet exists make a forwarding decision
                if pkt_S is not None:

                    # add new vars

                    p = NetworkPacket.from_byte_S(self.out_intf_L[0].mtu, pkt_S) #parse a packet out
                    # HERE you will need to implement a lookup into the
                    # forwarding table to find the appropriate outgoing interface
                    # for now we assume the outgoing interface is also i
                    
                    for x in p:
                        self.out_intf_L[i].put(x.to_byte_S(), True)
                        print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                        % (self, x.to_byte_S(), i, i, self.out_intf_L[i].mtu))

            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass

    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return
