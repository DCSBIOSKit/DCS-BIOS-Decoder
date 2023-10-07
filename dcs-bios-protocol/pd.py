import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'dcsbios'
    name = 'DCS-BIOS Protocol'
    longname = 'DCS-BIOS Protocol'
    desc = 'DCS-BIOS protocol decoder.'
    license = 'gplv2+'
    tags = ['DCS']
    inputs = ['uart']
    outputs = []
    annotations = (
        ('sync', 'Sync bytes'),
        ('address', 'Address'),
        ('count', 'Count'),
        ('data', 'Data'),
    )
    annotation_rows = (
        ('fields', 'Fields', (0, 1, 2, 3)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = 0  # Initial state: Wait for sync
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
            self.sync_byte_count += 1
        else:
            self.sync_byte_count = 0

        if self.sync_byte_count == 4:
            self.state = 1  # Transition to address_low state
            self.count = 0
            self.address = 0
            self.data = 0
            self.sync_byte_count = 0
            self.put(ss, es, self.out_ann, [0, ['SYNC']])
            return

        if self.state == 1:  # DCSBIOS_STATE_ADDRESS_LOW
            self.address = c
            self.state = 2
            self.put(ss, es, self.out_ann, [1, ['Address low: %02x' % c]])

        elif self.state == 2:  # DCSBIOS_STATE_ADDRESS_HIGH
            self.address = (c << 8) | self.address
            if self.address != 0x5555:
                self.state = 3  # Transition to count_low state
            else:
                self.state = 0  # Transition back to wait_for_sync state
            self.put(ss, es, self.out_ann, [1, ['Address high: %02x, Full address: %04x' % (c, self.address)]])

        elif self.state == 3:  # DCSBIOS_STATE_COUNT_LOW
            self.count = c
            self.state = 4
            self.put(ss, es, self.out_ann, [2, ['Count low: %02x' % c]])

        elif self.state == 4:  # DCSBIOS_STATE_COUNT_HIGH
            self.count = (c << 8) | self.count
            self.state = 5  # Transition to data_low state
            self.put(ss, es, self.out_ann, [2, ['Count high: %02x, Full count: %04x' % (c, self.count)]])

        elif self.state == 5:  # DCSBIOS_STATE_DATA_LOW
            self.data = c
            self.count -= 1
            self.state = 6
            self.put(ss, es, self.out_ann, [3, ['Data low: %02x' % c]])

        elif self.state == 6:  # DCSBIOS_STATE_DATA_HIGH
            self.data = (c << 8) | self.data
            self.count -= 1
            self.address += 2
            if self.count == 0:
                self.state = 1  # Transition back to address_low state
            else:
                self.state = 5  # Transition back to data_low state
            self.put(ss, es, self.out_ann, [3, ['Data high: %02x, Full data: %04x' % (c, self.data)]])
