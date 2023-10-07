import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'dcsbios'
    name = 'DCS-BIOS USB'
    longname = 'DCS-BIOS USB'
    desc = 'DCS-BIOS USB Protocol Decoder.'
    license = 'gplv2+'
    tags = ['DCS']
    inputs = ['uart']
    outputs = []
    annotations = (
        ('sync', 'Sync bytes'),
        ('address', 'Address'),
        ('count', 'Count'),
        ('data16', '16 Bit Data'),
        ('data', 'Data'),
    )
    annotation_rows = (
        ('fields', 'Fields', (0, 1, 2, 3)),
        ('data', 'Data', (4,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = 'SYNC'  # Initial state: Wait for sync
        self.sync_byte_count = 0
        self.address = 0
        self.count = 0
        self.data = 0

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def decode(self, ss, es, data):
        ptype, rxtx, pdata = data

        if ptype != 'DATA':
            return

        c = pdata[0]

        if c == 0x55:
            if self.sync_byte_count == 0:
                self.first_sync = ss
            self.sync_byte_count += 1
        else:
            self.sync_byte_count = 0

        if self.sync_byte_count == 4:
            self.state = 'ADDRESS_LOW'
            self.count = 0
            self.address = 0
            self.data = 0
            self.sync_byte_count = 0
            self.put(self.first_sync, es, self.out_ann, [0, ['SYNC']])
            return

        if self.state == 'ADDRESS_LOW':
            self.address_start = ss
            self.address = c
            self.state = 'ADDRESS_HIGH'

        elif self.state == 'ADDRESS_HIGH':
            self.address = (c << 8) | self.address
            if self.address != 0x5555:
                self.state = 'COUNT_LOW'
            else:
                self.state = 'SYNC'
            self.put(self.address_start, es, self.out_ann, [1, ['%04x' % (self.address)]])

        elif self.state == 'COUNT_LOW':
            self.count_start = ss
            self.count = c
            self.state = 'COUNT_HIGH'

        elif self.state == 'COUNT_HIGH':
            self.count = (c << 8) | self.count
            self.state = 'DATA_LOW'
            self.put(self.count_start, es, self.out_ann, [2, ['{}'.format(self.count)]])

        elif self.state == 'DATA_LOW':
            self.data_start = ss
            self.data = c
            self.count -= 1
            self.state = 'DATA_HIGH'
            
            char = chr(c)
            if char.isprintable():
                formatted_byte = char  # Show as ASCII if printable
            else:
                formatted_byte = '[{:02X}]'.format(byte)  # Show as Hex if not printable

            self.put(ss, es, self.out_ann, [4, [formatted_byte]])

        elif self.state == 'DATA_HIGH':
            self.data = (c << 8) | self.data
            self.count -= 1
            self.address += 2
            if self.count == 0:
                self.state = 'ADDRESS_LOW'
            else:
                self.state = 'DATA_LOW'
            self.put(self.data_start, es, self.out_ann, [3, ['%04x' % (self.data)]])

            char = chr(c)
            if char.isprintable():
                formatted_byte = char  # Show as ASCII if printable
            else:
                formatted_byte = '[{:02X}]'.format(byte)  # Show as Hex if not printable

            self.put(ss, es, self.out_ann, [4, [formatted_byte]])
