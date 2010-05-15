'''
Created on 15.04.2010

@author: cmk
'''

class ControlFileError (ValueError):
    pass

class PackageError (ValueError):
    pass

class HookError (OSError):
    pass