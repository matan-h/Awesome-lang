import sys
import os
from ._utils import builtin_vars

mapping = {
            8: float('inf'),
            0: 0, # The void
            1: -1,
            3: os.getpid(),
            7: sys.maxsize, # Crypto/Arch infinity
            2: 10**22 # Approx stars
        }
for k, v in mapping.items():
    builtin_vars.set("~"+str(k),v)