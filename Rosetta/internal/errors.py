################################################################################
class RosettaError(Exception):
    '''Rosetta base exception class. Never raised.'''
    pass

class RosettaInterfaceError(RosettaError):
    '''Base error class for Rosetta interfaces.'''
    interface=''
    def __init__( self, msg ):
        super(RosettaInterfaceError, self).__init__(
             'Error in Rosetta {} interface: {}'.format(self.interface, msg))
    pass

class RosettaImportError(RosettaError):
    '''Base error class for Rosetta interfaces.'''
    interface=''
    def __init__( self, msg ):
        super(RosettaImportError, self).__init__(
             'Error importing Rosetta {} interface: {}'.format(self.interface, msg))
    pass

class BasesError(RosettaError):
    '''Error class for locating basis implementations.'''
    interface=''
    pass

class RelationshipsError(RosettaError):
    '''Error class for locating basis implementations.'''
    interface=''
    pass
    
class TranslationError(RosettaError):
    '''Fancy error name.'''
    pass
    
class TranslationPathError(TranslationError):
    '''Exception raised when a suitable translation path is not found'''
    pass

class ReadSettingsError(RosettaError):
    '''Raised for error in reading setting from config.txt'''
    interface=''
    def __init__( self ):
        super(RosettaSettingsError, self).__init__('Error reading config.txt.')
    pass
################################################################################
