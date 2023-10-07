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
        self.protocol_state = 'SYNC'
        self.protocol_sync_byte_count = 0
        self.protocol_address = 0
        self.protocol_count = 0
        self.protocol_data = 0

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def decode(self, ss, es, data):
        ptype, rxtx, pdata = data

        if ptype != 'DATA':
            return

        byte = pdata[0]


        if byte == 0x55:
            if self.protocol_sync_byte_count == 0:
                self.first_sync = ss
            self.protocol_sync_byte_count += 1
        else:
            self.protocol_sync_byte_count = 0

        if self.protocol_sync_byte_count == 4:
            self.protocol_state = 'ADDRESS_LOW'
            self.protocol_count = 0
            self.protocol_address = 0
            self.protocol_data = 0
            self.protocol_sync_byte_count = 0
            self.put(self.first_sync, es, self.out_ann, [0, ['SYNC']])
            return

        if self.protocol_state == 'ADDRESS_LOW':
            self.protocol_address_start = ss
            self.protocol_address = byte
            self.protocol_state = 'ADDRESS_HIGH'

        elif self.protocol_state == 'ADDRESS_HIGH':
            self.protocol_address = (byte << 8) | self.protocol_address
            if self.protocol_address != 0x5555:
                self.protocol_state = 'COUNT_LOW'
            else:
                self.protocol_state = 'SYNC'
            self.put(self.protocol_address_start, es, self.out_ann, [1, ['%04x' % (self.protocol_address)]])

        elif self.protocol_state == 'COUNT_LOW':
            self.protocol_count_start = ss
            self.protocol_count = byte
            self.protocol_state = 'COUNT_HIGH'

        elif self.protocol_state == 'COUNT_HIGH':
            self.protocol_count = (byte << 8) | self.protocol_count
            self.protocol_state = 'DATA_LOW'
            self.put(self.protocol_count_start, es, self.out_ann, [2, ['{}'.format(self.protocol_count)]])

        elif self.protocol_state == 'DATA_LOW':
            self.protocol_data_start = ss
            self.protocol_data = byte
            self.protocol_count -= 1
            self.protocol_state = 'DATA_HIGH'
            
            char = chr(byte)
            if char.isprintable():
                formatted_byte = char  # Show as ASCII if printable
            else:
                formatted_byte = '[{:02X}]'.format(byte)  # Show as Hex if not printable

            self.put(ss, es, self.out_ann, [4, [formatted_byte]])

        elif self.protocol_state == 'DATA_HIGH':
            self.protocol_data = (byte << 8) | self.protocol_data
            self.protocol_count -= 1
            self.protocol_address += 2
            if self.protocol_count == 0:
                self.protocol_state = 'ADDRESS_LOW'
            else:
                self.protocol_state = 'DATA_LOW'
            self.put(self.protocol_data_start, es, self.out_ann, [3, ['%04x' % (self.protocol_data)]])

            char = chr(byte)
            if char.isprintable():
                formatted_byte = char  # Show as ASCII if printable
            else:
                formatted_byte = '[{:02X}]'.format(byte)  # Show as Hex if not printable

            self.put(ss, es, self.out_ann, [4, [formatted_byte]])
