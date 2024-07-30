import unittest
from protoDshot.dshot_bits import *
from protoDshot.protocols_motor import *


class MyTestCase(unittest.TestCase):
    def setUp(self):
        cfg = DshotSettings()
        cfg.bidirectional = True
        cfg.edt_force = False
        cfg.dshot_kbaud = 300 * 1000
        cfg.samplerate = 4e6  # 4mhz
        cfg.update()

        self.telem_value = DshotTelem(cfg)

    def test_xor(self):
        self.assertEqual(self.telem_value.bits_xor_next(0b1110100100110001001), 0b1001110110101001101, "xor with next")
        self.assertNotEqual(self.telem_value.bits_xor_next(0b11101001001100010010), 0b1001110110101001101, "xor with next")

    def test_gcr(self):
        self.assertEqual(self.telem_value.bits_gcr(0b10110),0x6)
        with self.assertRaises(KeyError):
            self.telem_value.bits_gcr(0b110)





        # self.telem_value.bits = 0b1110100100110001000
        # telem_value.process_telem()
        # self.assertNotEqual(telem_value.xor, 0b1001110110101001101)

    def test_something(self):
        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
