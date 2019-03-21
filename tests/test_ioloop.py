# -*- coding: utf-8 -*-
"""test cases for ioloop
"""
import unittest

from qt4s.connections.ioloop import IOLoopBase


class IOLoopTest(unittest.TestCase):

    def test_singleton(self):
        ioloop1 = IOLoopBase.instance()
        ioloop2 = IOLoopBase.instance()
        self.assertTrue(ioloop1 is ioloop2)

    def test_register(self):

        def cb(data):
            print(data)

        ioloop = IOLoopBase.instance()
        fd = object()  # pseudo fd
        self.assertRaises(ValueError, ioloop.register_fd, fd, None, cb, cb)


if __name__ == "__main__":
    unittest.main(defaultTest="IOLoopTest")

