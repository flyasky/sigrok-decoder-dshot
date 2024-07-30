import unittest
from protoDshot.dshot_bits import *
from protoDshot.protocols_motor import *


class MyTestCase(unittest.TestCase):
    def test_xor(self):
        cfg = DshotSettings()
        cfg.bidirectional = True
        cfg.edt_force =  False
        cfg.dshot_kbaud = 300 * 1000
        cfg.samplerate = 4e6 #4mhz
        cfg.update()

        telem_value = DshotTelem(cfg)


        telem_value.bits = 0b1110100100110001001
        telem_value.process_telem()
        self.assertEqual(telem_value.xor,0b1001110110101001101)

    def test_something(self):
        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
