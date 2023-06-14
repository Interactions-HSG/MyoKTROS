# -*- coding: utf-8 -*-
import aenum


class KTMode(aenum.Enum):
    __slot__ = "name"
    STANDARD_MODE = 0
    TEACH_MODE = 1
