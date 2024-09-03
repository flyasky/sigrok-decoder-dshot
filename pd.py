## Modified from rgb_led_ws281x - original license below:
## Copyright (C) 2023: hyp0dermik@gmail.com

##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2016 Vladimir Ermakov <vooon341@gmail.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd
from functools import reduce
from enum import Enum
from dshot.protoDshot import DshotCmd, DshotTelem, BitDshot, DshotSettings, Bit_DshotTelem


class SamplerateError(Exception):
    pass

class State(Enum):
    RESET = 0
    CMD = 1
    TELEM = 2


class State_Dshot(Enum):
    RESET = 0
    START = 1
    RECV = 2


class Ann:
    BIT, COMMAND, THROTTLE, TELEMETRY_REQUEST, CRC, ERRORS, \
    TELEMETRY_BIT, TELEMETRY_GCR, TELEMETRY_PACKET, TELEMETRY_CRC, TELEMETRY_ERPM, TELEMETRY_EDT, TELEMETRTY_ERRORS = \
    range(13)


class Decoder(srd.Decoder):
    api_version = 3
    id = 'dshot'
    name = 'DShot'
    longname = 'DShot RC Hobby Motor Protcol Decoder'
    desc = 'DShot RC Hobby Motor Protcol Decoder'
    license = 'gplv3+'
    inputs = ['logic']
    outputs = []
    tags = ['Display', 'IC']
    channels = (
        {'id': 'din', 'name': 'DIN', 'desc': 'DIN data line'},
    )

    options = (
        {'id': 'dshot_rate', 'desc': 'DShot Rate', 'default': '300','values': ('150', '300', '600', '1200')},
        {'id': 'bidir', 'desc': 'Bidirectional DShot','default': 'True', 'values': ('True', 'False')},
        {'id': 'log', 'desc': 'Write log file','default': 'no', 'values': ('yes', 'no')},
        {'id': 'edt_force', 'desc': 'Force EDT as telem type', 'default': 'no', 'values': ('True', 'False')},
    )
    annotations = (
        ('bit', 'Bit'),
        ('cmd', 'Command'),
        ('throttle', 'Throttle'),
        ('telem_request', 'Telem Requets'),
        ('checksum', 'CRC'),
        ('errors', 'Errors'),
        ('telem_bit', 'Telem Bit'),
        ('telem_gcr', 'Telem GCR'),
        ('telem_packet', 'Telem Packet'),
        ('telem_crc', 'Telem CRC'),
        ('telem_erpm', 'Telem ERPM'),
        ('telem_edt', 'Telem EDT'),
        ('telem_errors', 'Telem Errors'),
    )
    annotation_rows = (
        ('bits', 'Bits', (Ann.BIT,)),
        ('dshot_data', 'DShot Data', (Ann.COMMAND, Ann.THROTTLE, Ann.TELEMETRY_REQUEST, Ann.CRC)),
        ('dshot_errors', 'Dshot Errors', (Ann.ERRORS,)),
        ('telem_bits', 'Telem Bits', (Ann.TELEMETRY_BIT,)),
        ('dshot_telem_gcr', 'Dshot Telem GCR', (Ann.TELEMETRY_GCR,)),
        ('dshot_telem_packet', 'Dshot Telem Packet', (Ann.TELEMETRY_PACKET, Ann.TELEMETRY_CRC,)),
        ('dshot_telem_erpm', 'Dshot Telem ERPM', (Ann.TELEMETRY_ERPM,)),
        ('dshot_telem_edt', 'Dshot Telem', (Ann.TELEMETRY_EDT,)),
        ('dshot_telem_errors', 'Dshot Errors', (Ann.TELEMETRTY_ERRORS,)),
    )


    def __init__(self):
        self.reset()

    def reset(self):
        self.state = State.CMD
        self.state_telem = State_Dshot.START
        self.state_dshot = State_Dshot.START

        self.samplerate = None
        self.inreset = False
        self.currbit_ss = None
        self.currbit_es = None

        self.dshot_cfg = DshotSettings()

        self.debug = False

    def start(self):
        self.dshot_cfg.bidirectional = True if self.options['bidir'] == 'True' else False
        self.dshot_cfg.edt_force = True if self.options['edt_force'] == 'True' else False
        self.dshot_cfg.dshot_kbaud = int(self.options['dshot_rate'])*1000
        self.dshot_cfg.samplerate = self.samplerate
        self.dshot_cfg.update()

        self.out_ann = self.register(srd.OUTPUT_ANN)

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def display_bit(self, bitseq, annot):
        self.put(bitseq.ss, bitseq.es, self.out_ann,
                 [annot, ['%d' % bool(bitseq)]])

    def display_dshot(self, dshot):
        crc_startsample = dshot.results[12].ss

        # Split annotation based on value type
        if dshot.dshot_value == 0:
            self.put(dshot.results[0].ss, dshot.results[10].es, self.out_ann,
                     [Ann.COMMAND, ['DISARMED']])
            if dshot.telem_request:
                self.put(dshot.results[11].ss, dshot.results[11].es, self.out_ann,
                        [Ann.TELEMETRY_REQUEST, ['TR']])
        elif dshot.dshot_value < 48:
            # Command
            self.put(dshot.results[0].ss, crc_startsample, self.out_ann,
                     [Ann.COMMAND, ['%04d' % dshot.dshot_value]])
        else:
            # Throttle
            self.put(dshot.results[0].ss, dshot.results[10].es, self.out_ann,
                     [Ann.THROTTLE, ['%04d' % dshot.dshot_value]])
            if dshot.telem_request:
                self.put(dshot.results[11].ss, dshot.results[11].es, self.out_ann,
                        [Ann.TELEMETRY_REQUEST, ['TR']])

        self.put(crc_startsample, dshot.results[15].es, self.out_ann,
                 [Ann.CRC, ['Calc CRC: ' + ('%04d' % dshot.crc_calc) + ' TXed CRC:' + ('%04d' % dshot.crc_recv)]])
        if not dshot.crc_ok:
            self.put(crc_startsample, dshot.results[15].es, self.out_ann,
                     [Ann.ERRORS, ['CRC INVALID']])

    def display_telem(self, telem):
        crc_startsample = telem.results[12].ss
        if telem.gcr_recv:
            self.put(telem.results[0].ss, telem.results[20].es, self.out_ann,
                     [Ann.TELEMETRY_GCR, [self.bin_quibble(telem.gcr_recv)]])

        if not telem.crc_ok or len(telem.results) != 21 or (telem.crc_recv != telem.crc_calc) or (telem.crc_calc == 0):
            self.put(crc_startsample, telem.results[20].es, self.out_ann,
                     [Ann.TELEMETRTY_ERRORS, ['CRC INVALID or smth else']])

        if telem.packet:
            self.put(telem.results[0].ss, telem.results[15].es, self.out_ann,
                     [Ann.TELEMETRY_PACKET, [self.bin_nibble(telem.packet)]])
        #if telem.crc_calc and telem.crc_recv:
            self.put(telem.results[16].ss, telem.results[20].es, self.out_ann,
                [Ann.TELEMETRY_CRC, ['Calc CRC: ' + ('%04d' % telem.crc_calc) + ' TXed CRC:' + ('%04d' % telem.crc_recv)]])

        # self.put(telem.results[0].ss, telem.results[11].es, self.out_ann,
        #          [Ann.TELEMETRY_ERPM, [str(bin(telem.dshot_value))]])
        if telem.edt:
            self.put(telem.results[0].ss, telem.results[11].es, self.out_ann,
                     [Ann.TELEMETRY_EDT, [telem.edt]])


    def bin_nibble(self, val):
        b = bin(val)[2:]
        new_b = '_'.join([b[::-1][i:i+4][::-1] for i in range(0, len(b), 4)][::-1])
        return ''.join(['0']*(4 - len(b) % 4 if len(b) % 4 != 0 else 0) + [new_b])

    def bin_quibble(self, val):
        b = bin(val)[2:]
        new_b = '_'.join([b[::-1][i:i+5][::-1] for i in range(0, len(b), 5)][::-1])
        return ''.join(['0']*(5 - len(b) % 5 if len(b) % 5 != 0 else 0) + [new_b])

    def decode(self):
        if not self.samplerate:
            raise SamplerateError('Cannot decode without samplerate.')

        dshot_value = DshotCmd(self.dshot_cfg)
        telem_value = DshotTelem(self.dshot_cfg)

        while True:
            match self.state:
                case State.CMD:
                    match self.state_dshot:
                        case State_Dshot.RESET:
                            dshot_value = DshotCmd(self.dshot_cfg)
                            self.state_dshot = State_Dshot.START

                        case State_Dshot.START:
                            if not self.dshot_cfg.bidirectional:
                                pins = self.wait([{0: 'r'}, {0: 'f'}, {'skip': self.dshot_cfg.samples_after_motorcmd}])
                            else:
                                pins = self.wait([{0: 'f'}, {0: 'r'}, {'skip': self.dshot_cfg.samples_after_motorcmd}])
                            #TODO: Increase skip to maximum time for effiency
                            #TODO: Mark any changes in this time as errors?  Option to reduce load?

                            if self.currbit_ss and self.currbit_es and self.matched[2]:
                                # Assume end of packet if have seen start and end of a potential bit but no further change within 3 periods
                                # TODO: Confirm wait period this works with spec

                                args = self.currbit_ss, self.currbit_es, (self.currbit_ss + self.dshot_cfg.samples_pp)
                                curr_bit = BitDshot(*args)
                                dshot_value.add_bit(curr_bit)
                                self.display_bit(curr_bit, Ann.BIT)
                                self.currbit_ss = None
                                self.currbit_es = None

                            # Pass results to decoder
                            result = dshot_value.handle_bits_dshot()
                            if result:
                                self.display_dshot(dshot_value)
                                self.state_dshot = State_Dshot.RESET
                            if result and self.dshot_cfg.bidirectional:
                                self.state = State.TELEM


                            if self.matched[0] and not self.currbit_ss and not self.currbit_es:
                                # Start of bit
                                self.currbit_ss = self.samplenum
                            elif self.matched[1] and self.currbit_ss and not self.currbit_es:
                                # End of bit
                                self.currbit_es = self.samplenum
                            elif self.matched[0] and self.currbit_es and self.currbit_ss:
                                # Have complete bit, can handle bit now
                                args = self.currbit_ss, self.currbit_es, self.samplenum
                                curr_bit = BitDshot(*args)
                                dshot_value.add_bit(curr_bit)
                                self.display_bit(curr_bit,0)

                                self.currbit_ss = self.samplenum
                                self.currbit_es = None
                case State.TELEM:
                    match self.state_telem:
                        case State_Dshot.RESET:
                            telem_value = DshotTelem(self.dshot_cfg)
                            self.state_telem = State_Dshot.START

                        case State_Dshot.START:
                            # First wait for falling edge (idle high)
                            pins = self.wait([{0: 'f'}])
                            # Save start pulse
                            tlm_start = self.samplenum
                            # Switch to receiving state
                            self.state_telem = State_Dshot.RECV
                            # TODO: Check if still low after 1/8 bitlength for error det?
                        case State_Dshot.RECV:

                            # First conditions skips half bit width and matches low
                            # Second condition skips half bit width and matches high
                            pins = self.wait([{0: 'l', 'skip': self.dshot_cfg.telem_baudrate_midpoint},
                                            {0: 'h', 'skip': self.dshot_cfg.telem_baudrate_midpoint}])

                            # Append next bit
                            args = (self.samplenum - self.dshot_cfg.telem_baudrate_midpoint), self.samplenum, (self.samplenum + self.dshot_cfg.telem_baudrate_midpoint)
                            curr_bit = Bit_DshotTelem(*args,
                                            self.matched)
                            self.display_bit(curr_bit, Ann.TELEMETRY_BIT)
                            telem_value.add_bit(curr_bit)

                            # Skip half bitwidth to end of bit
                            pins = self.wait([{'skip': self.dshot_cfg.telem_baudrate_midpoint}])

                            if telem_value.process_telem():
                                self.display_telem(telem_value)
                                # Reset
                                self.state_telem = State_Dshot.RESET
                                # Except Dshot packet next
                                self.state = State.CMD

                            # If not mark as error

    #TODO: What happens if it gets stuck in the wrong state?
