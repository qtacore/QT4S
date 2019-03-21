# -*- coding: utf-8 -*-
"""network area dectector
"""

import os

from qt4s.network.base import INetworkAreaDetector, NetworkArea
from testbase.conf import settings
from testbase.util import get_attribute_from_string


class DefaultNetworkAreaDetector(INetworkAreaDetector):
    """default network area detector using settings
    """

    def detect(self):
        user_dir = os.path.expanduser("~")
        netarea_file = os.path.join(user_dir, ".qt4s", "netarea")
        if os.path.exists(netarea_file):
            with open(netarea_file) as fd:
                netarea_paths = fd.read().split()
                names = set()
                for netarea_path in netarea_paths:
                    netarea = get_attribute_from_string(netarea_path)
                    names.update(netarea.names)
                return NetworkArea(*names)
        return NetworkArea("LAN")


def detect():
    qt4s_network_area_detectors = settings.QT4S_NETWORK_AREA_DETECTORS
    for detector_name in qt4s_network_area_detectors:
        detector = get_attribute_from_string(detector_name)
        network_area = detector.detect()
        if network_area:
            break
    else:
        detector = DefaultNetworkAreaDetector()
        network_area = detector.detect()
    area_names = network_area.names.copy()
    area_names.add("LAN")
    return NetworkArea(*area_names)


CURRENT = detect()
