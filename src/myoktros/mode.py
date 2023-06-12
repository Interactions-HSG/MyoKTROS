# -*- coding: utf-8 -*-
import aenum


class Mode(aenum.Enum):
    __slot__ = "name"
    STANDARD_MODE = 0
    TEACH_MODE = 1
