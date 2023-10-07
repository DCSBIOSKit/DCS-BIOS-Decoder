import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'dcs_bios_rs485'
    name = 'DCS-BIOS RS485'
    longname = 'DCS-BIOS RS485'
    desc = 'DCS-BIOS RS485 Protocol Decoder.'
    license = 'gplv2+'
    tags = ['DCS']
    inputs = ['uart']
    outputs = []
    annotations = (
        ('address', 'Address'),
        ('msgtype', 'Message Type'),
        ('datalength', 'Data Length'),
        ('data', 'Data'),
        ('checksum', 'Checksum'),
        ('state', 'State'),
        ('gap', 'Gap'),
    )
    annotation_rows = (
        ('fields', 'Fields', (0, 1, 2, 3, 4)),
        ('state', 'State', (5,)),
        ('idle', 'Idle', (6,)),
    )
    
    def __init__(self):
        self.reset()

    def reset(self):
        self.new_message()
        self.state = 'UNINITIALIZED'
        self.last_sample_end = 0

    def new_message(self):
        self.state = 'SYNC'
        self.byte_count = 0
        self.data_length = 0
        self.msgtype = 0
        self.address = 0

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def decode(self, ss, es, data):
        ptype, rxtx, pdata = data

        if ptype != 'DATA':
            return

        byte = pdata[0]
        
        # Calculate time gap in microseconds
        gap = (ss - self.last_sample_end)

        # Check for a 500us+ pause to move to SYNC state
        if gap >= 300:
            self.new_message()

        #if byte == 0xFC:
        #    self.new_message()
        #    return
        
        if gap >= 300 and gap < 5000:
            self.put(ss-gap, ss, self.out_ann, [5, ['SYNC']])
            self.put(ss-gap, ss, self.out_ann, [6, ['{}us'.format(gap)]])

        #if byte == 0xFC:
        #    self.put(ss, es, self.out_ann, [5, ['SYNC']])
        
        # Update the last sample end time
        self.last_sample_end = es

        if self.state == 'SYNC':
            self.state = 'RX_WAIT_ADDRESS'
            self.address = byte
            self.put(ss, es, self.out_ann, [0, ['{}'.format(self.address)]])
            self.put(ss, es, self.out_ann, [5, ['RX_WAIT_ADDRESS']])
            return

        if self.state == 'RX_WAIT_ADDRESS':
            self.state = 'RX_WAIT_MSGTYPE'
            self.msgtype = byte
            self.put(ss, es, self.out_ann, [1, ['{}'.format(self.msgtype)]])
            self.put(ss, es, self.out_ann, [5, ['RX_WAIT_MSGTYPE']])
            return

        if self.state == 'RX_WAIT_MSGTYPE':
            self.state = 'RX_WAIT_DATALENGTH'
            self.data_length = byte
            self.put(ss, es, self.out_ann, [2, ['{}'.format(self.data_length)]])
            self.put(ss, es, self.out_ann, [5, ['RX_WAIT_DATALENGTH']])
            return

        if self.state == 'RX_WAIT_DATALENGTH':
            if self.byte_count == 0:
                self.data_start = ss

            if self.byte_count < self.data_length:
                char = chr(byte)

                if char.isprintable():
                    formatted_byte = char  # Show as ASCII if printable
                else:
                    formatted_byte = '[{:02X}]'.format(byte)  # Show as Hex if not printable

                self.put(ss, es, self.out_ann, [3, [formatted_byte]])

            self.byte_count += 1

            if self.byte_count == self.data_length:
                self.state = 'RX_WAIT_CHECKSUM'
                self.put(self.data_start, es, self.out_ann, [5, ['RX_WAIT_DATA']])
            
            return

        if self.state == 'RX_WAIT_CHECKSUM':
            self.put(ss, es, self.out_ann, [4, ['{}'.format(byte)]])
            self.put(ss, es, self.out_ann, [5, ['RX_WAIT_CHECKSUM']])

            if self.address == 0:
                self.new_message()
            return