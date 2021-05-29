
import re

class ConfigData:
    def __init__(self, data):
        self._data = data
    
    def __setattribute__(self, name, val):
        if name == '_data':
            object.__setattribute__(self, '_data', val)
        else:
            data = object.__getattribute__(self, name)
            data[name] = val
    
    def __getattribute__(self, name):
        data = object.__getattribute__(self, '_data')
        if name == 'data':
            return data
        if name in data:
            return data[name]
        return None

class Config:

    def __init__(self, filename):
        data = {}
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if (not line) or line.startswith('#'):
                    continue

                (key, val) = line.split('=', maxsplit=1)
                key = key.strip()
                val = val.strip()
                if key.endswith('[]'):
                    key = key[:-2]
                    if not key in data:
                        data[key] = []
                    data[key].append(val)
                else:
                    data[key] = val
        self.data = data
        self.v = ConfigData(data)

    def enabled(self, key):
        if key not in self.data:
            return False
        val = self.data[key]
        if (val is None) or (val == '') or (val == '0'):
            return False
        return True

    def int(self, key, defval = None):
        if key not in self.data:
            return defval
        return int(self.data[key])
