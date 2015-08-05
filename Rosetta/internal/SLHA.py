from collections import OrderedDict, MutableMapping
from operator import itemgetter
import sys
import re

class CaseInsensitiveOrderedDict(MutableMapping):
    
    def __init__(self, data=None, **kwargs):
        self._data = OrderedDict()
        if data is None:
            data = {}
        self.update(data, **kwargs)
    
    def __setitem__(self, key, value):
        self._data[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._data[key.lower()][1]

    def __delitem__(self, key):
        del self._data[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalue in self._data.values())

    def __len__(self):
        return len(self._data)
    
        
class Block(OrderedDict):
    '''    
    Container class for SLHA block with a single counter. A subclass of 
    `collections.OrderedDict`with a restriction on integer keys and a modified 
    __repr__(). Block can't be initialised with any positional arguments but 
    rather with the 'data' keyword argument. It can optionally be named using 
    the 'name' keyword argument. The__str__ function are also defined to output 
    the contained data in an SLHA formatted block.
    '''

    def __checkkey__(self, key):
        '''Forces key to be of integer type.'''
        if type(key) is not self.keytype: 
            raise TypeError("Key: '{}'. ".format(key) + self.__class__.__name__ 
                            + ' only accepts keys of {}.'.format(self.keytype))
        else:
            return key
    
    def __cast__(self, val):
        '''
        Attempts to cast values to type specified in 'dtype' keyword argument 
        of constructor.
        '''
        try:
            return self.cast(val)
        except ValueError:
            return val
    
    def __init__(self, name=None, data=None, 
                 decimal=5, dtype=float, preamble=''):
        '''    Intialisation keyword arguments:
            name - A name for the block that will appear 
                   in the __str__ and __repr__ methods.
            data - A dict type object supporting iteritems() 
                   to initialize Block values.
            decimal - Number of decimal points with which 
                      to write out parameter values.
            dtype - a function to cast parameter values if 
                    read in as strings i.e. int, float.
            preamble - Some text to print before the __str__ output.
        '''
        super(Block, self).__init__()
        self.name = name
        self.cast = dtype # value casting function
        self.fmt = ':+.{}e'.format(decimal) # format string
        self.preamble = preamble
        self.keytype = int
        if data is not None:
            for k,v in data.iteritems():
                self[k]=v
                
    def __setitem__(self,key,value):
        return super(Block, self).__setitem__(self.__checkkey__(key),
                                              self.__cast__(value))

    def __repr__(self):
        return ('<SHLA Block: "{}"; {} entries.>'.format(self.name, len(self)))

    def __str__(self):
        content = []
        sortitems = sorted(self.items())
        for k,v in sortitems:
            try:
                val = float(v)
                fmt = self.fmt
            except ValueError:
                fmt = ''
            
            line = ('    {{: <4}} {{{}}}\n'.format(fmt)).format
            content.append(line(k,val)) 
            
        string = (self.preamble+'\n'
                  +'BLOCK {}\n'.format(self.name)
                  + ''.join(content) + '\n')
        return string
    
    def dict(self):
        '''Return SHLA Block data as a regular python dict.'''
        return {k:v for k,v in self.iteritems()}

class Matrix(Block):
    '''    
    Container class for SLHA block with multiple counters. A subclass of 
    `collections.OrderedDict`with a restriction on tuple keys and a modified 
    __repr__(). Block can't be initialised with any positional arguments but 
    rather with the 'data' keyword argument. It can optionally be named using 
    the 'name' keyword argument. The__str__ function are also defined to output 
    the contained data in an SLHA formatted block. The object is indexed 
    like a numpy multi dimensional array ( x[i,j,k,...] ).
    '''
    
    def __init__(self,*args,**kwargs):
        super(Matrix, self).__init__(*args, **kwargs)
        self.keytype = tuple
    
    def __setitem__(self, key, value):
        return super(Matrix, self).__setitem__(key, value)
    
    def __getitem__(self, key):
        return super(Matrix, self).__getitem__(self.__checkkey__(key))

    def __repr__(self):
        return ('<SHLA Matrix: "{}"; {} entries.>'.format(self.name, len(self)))

    def __str__(self):
        content = []
        sortitems = sorted(self.items(), key=itemgetter(0,0))
        for k,v in sortitems:
            try:
                v = float(v)
                fmt = self.fmt
            except ValueError:
                fmt=''
            ind = '{: <4}'*len(k)
            line = ('    {} {{{}}}\n'.format(ind,fmt)).format
            args = list(k)+[v]
            content.append(line(*args))
        string = (self.preamble+'\n'
                  +'BLOCK {}\n'.format(self.name)
                  + ''.join(content) )
        return string
    
    def array(self):
        pass
    def dimension(self):
        pass

class NamedBlock(Block):
    '''
    Class derived from 'Block' with the added functionality of assigning a name 
    to each key via the 'names' keyword argument. The values can then also be 
    referenced by name via a lookup in self._numbers. 
    '''
    
    def __parse__(self, key):
        '''    
        Allows for elements to additionally be referred to by name. 
        Looks up self._numbers for an assigned name and returns the 
        associated key. Rasies KeyError if name is not booked. 
        Used in overloading __setitem__, __getitem__, __contains__ 
        and __delitem__.
        '''
        if type(key) is str:
            try:
                return self._numbers[key]
            except KeyError:
                err = ('Name "{}" has not been assigned to a '.format(key) +
                       'key in SLHA.NamedBlock {}._names'.format(self.name))
                raise KeyError(err)
        else:
            return key
    
    def __init__(self, name=None, data=None, 
                 comment='', decimal=5, dtype=float, preamble=''):
        '''    
        Same as the SLHA.Block constructor but additionally checks if the data 
        keyword argument has a "_names" attribute (i.e. if it is an existing 
        instance of NamedBlock) and stores it. The "comment" keyword argument 
        prints a comment to the right of the block declaration in __str__().
        '''        
        if data is not None and hasattr(data, '_names'):
            self._names = data._names
            try:
                self._numbers = CaseInsensitiveOrderedDict({v:k for k,v 
                                                  in self._names.iteritems()})
            except AttributeError:
                raise ValueError('"names" keyword argument must be a'
                                 'dictionary or support iteritems() method.')
        else:
            self._names, self._numbers = {}, CaseInsensitiveOrderedDict()

        self.comment = comment

        return super(NamedBlock, self).__init__(name=name, data=data, 
                                                decimal=decimal, dtype=dtype,
                                                preamble = preamble)
                                                
    def __setitem__(self, key, value):
        return super(NamedBlock, self).__setitem__(self.__parse__(key),
                                                   self.__cast__(value))

    def __getitem__(self, key):
        return super(NamedBlock, self).__getitem__(self.__parse__(key))
    
    def __delitem__(self, key):
        super(NamedBlock, self).__delitem__(self.__parse__(key))
        
        # Additional cleanup needed for _names and _numbers lookup dicts.
        if type(key) is str:
            # key = key.lower()
            try:
                del self._names[self._numbers[key]]
                del self._numbers[key]
            except KeyError:
                pass
        else:
            try:
                del self._numbers[self._names[key]]
                del self._names[key]
            except KeyError:
                pass
                                     
    def __contains__(self, key):
        try:
            return super(NamedBlock, self).__contains__(self.__parse__(key))
        except KeyError:
            return False
        
    def __repr__(self):
        return ('<SHLA NamedBlock: "{}"; {} entries, {} named.>'.format(
                                        self.name, len(self), len(self._names)))
    def __str__(self):
        content = []
        sortitems = sorted(self.items(), key=itemgetter(0))
        for k,v in sortitems:
            try:
                strval = ('{{{}}}'.format(self.fmt)).format(float(v))
            except ValueError:
                strval = v

            if k in self._names:
                content.append('    {: <4} {} # {}'.format(k, strval,
                                                           self._names[k]))
            else:
                content.append('    {: <4} {}'.format(k,strval))

        string = (self.preamble + '\n'
                  + 'BLOCK {} # {}\n'.format(self.name, self.comment)
                  + '\n'.join(content) + '\n')
        return string

    def get_name(self, key, default=''):
        return self._names.get(key, default)
        
    def get_number(self, name, default=-1):
        return self._numbers.get(name, default)
    
    def new_entry(self, key, value, name=None):
        '''
        Add a new named block entry. Ensures that the key hasn't already 
        been set and the name given hasn't already been booked.
        '''
           
        if key in self:
            err = ("Key '{}' already belongs to {} ".format(key,
                                                            self.__class__)
                 +  "'{}', mapped to name '{}'.".format(self.name,
                                                        self.get_name(key)))
            raise KeyError(err)
        
        if name in self._numbers:
            err = ("Name '{}' already booked in ".format(name) +
                   "NamedBlock {}, mapped to key '{}'.".format(
                                   self.name, self._numbers[name]))
            raise KeyError(err)
        else:
            if name is not None:
                self._names[key] = name
                self._numbers[name] = key
            self[key]=value
            
    def namedict(self):
        '''Return python dict of name:key pairs.'''
        return {self._names[k]:v for k,v in self.iteritems() 
                                 if k in self._names }

class NamedMatrix(Matrix, NamedBlock):
    '''    
    Class derived from `Matrix` and `NamedBlock` to add the named indexing 
    functionality to the multi-counter SLHA block structure.
    '''
                
    def __setitem__(self, key, value):
        return super(NamedMatrix, self).__setitem__(self.__parse__(key), value)
    
    def __getitem__(self, key):
        return super(NamedMatrix, self).__getitem__(self.__parse__(key))
                                            
    def __repr__(self):
        return ('<SHLA NamedMatrix: "{}"; {} entries.>'.format(self.name, 
                                                               len(self)))
                                                               
    def __str__(self):
        content = []
        sortitems = sorted(self.items(), key=itemgetter(0,0))
        for k,v in sortitems:
            try:
                v = float(v)
                fmt = self.fmt
            except ValueError:
                fmt=''
            vname = self._names.get(k,None)
            comment = '' if vname is None else '# {}'.format(vname)
            
            ind = '{: <4}'*len(k)
            line = ('    {} {{{}}} {{}}\n'.format(ind,fmt)).format
            args = list(k)+[v, comment]
            content.append(line(*args))
        string = (self.preamble+'\n'
                  +'BLOCK {}\n'.format(self.name)
                  + ''.join(content) )
        return string

class Decay(OrderedDict):
    '''
    Container class for SLHA Decay blocks. A subclass of `collections.OrderedDict` 
    with a restriction on tuple keys and float values less than 1. A modified 
    __repr__() function is implemented for easy writing to file. Decay is 
    initialised with a PID argument to specify the particle to which it refers 
    as well as its total width. The sum of branching ratios is kept and a 
    ValueError will be raised if the total exceeds 1. It can optionally be 
    named using the 'name' keyword argument. Finally a __str__() function is 
    also defined to output the SLHA formatted block.
    '''
    
    def __checkkey__(self, key):
        '''    Forces key to be a tuple and casts the elements to integers.'''
        if type(key) is not tuple: 
            raise TypeError( self.__class__.__name__ +
                             ' only accepts tuple keys: (PID1, PID2,...).' ) 
        else:
            return tuple(map(int,key))
    
    def __checkval__(self, val):
        '''    Forces values (i.e. branching ratios) to be a float less than 1.'''
        try:
            fval = float(val)
        except ValueError:
            raise TypeError( self.__class__.__name__ +
                         ' only accepts floats or values castable via float()' )
        if fval > 1.:
            raise TypeError("SLHA Decay object for PID = {}. ".format(self.PID)+
                            "Branching ratio > 1 encountered : {}".format(fval))
        return fval
    
    def __init__(self, PID, total, 
                 data=None, comment='', decimal=5, preamble= ''):
        '''    Positional arguments:
            PID - integer to denote particle whose decay is being described
            total - total width
            
            Keyword arguments:
            data - A dict type object supporting iteritems() 
                   to initialize Decay values.
            comment - prints a comment to the right of the block 
                      declaration in __str__().
            decimal - Number of decimal points with which 
                      to write out width and BRs.
            preamble - Some text to print before the __str__ output.'''
            
        super(Decay, self).__init__()
        try:
            self.PID=int(PID)
        except ValueError:
            err = ("SLHA Decay object for PID = {}. ".format(PID) + 
                   "'PID' argument must be an integer or be castable via int()")
            raise TypeError(err)
            
        try:
            self.total=float(total)
        except ValueError:
            err = ("SLHA Decay object for PID = {}. ".format(PID) + 
                  "'total' argument must be a float or be castable via float()")
            raise TypeError(err)

        self._BRtot = 0.
        self._fmt = ':+.{}e'.format(decimal)
        self._comment = comment
        self._decimal = decimal
        self._comments = {}
        self.preamble = preamble
        
        if data is not None:
            for k,v in data.iteritems():
                self[k]=v
                
    def __setitem__(self, key, value):
        super(Decay,self).__setitem__(self.__checkkey__(key),
                                      self.__checkval__(value))
        self._BRtot+=self.__checkval__(value)
        if self._BRtot > 1.:
            print '!!! ERROR !!!'
            print self
            raise ValueError("SLHA Decay object for PID = {}. ".format(self.PID)
                            + "Sum of branching ratios > 1!")            
    
    def __delitem__(self, key):
        super(Decay,self).__delitem__(self.__checkkey__( key ),
                                      self.__checkval__(value))
        self._BRtot-=self.__checkval__(self[key])
        
    def __repr__(self):
        return ( '<SHLA Decay: PID={}; {} entries.>'.format(self.PID, 
                                                            len(self)) )
    
    def __str__(self):
        above = '#        PDG        Width\n'
        title = ('DECAY    {{:<10}} {{{}}} # {{}}\n'.format(self._fmt)).format
        below = '#    BR{}    NDA       ID1       ID2...\n'.format(' '*self._decimal)
        if len(self)==0: below=''
        content = []
        for k,v in self.iteritems():
            nparts = len(k)
            idfmt = nparts*'{: <10}'
            line = ('{{{}}}    {{: <10}}{}'.format(self._fmt,idfmt)).format

            cmnt = ('# {}'.format(self._comments[k]) 
                     if k in self._comments else '')
            
            content.append(line(v, nparts, *k) + cmnt)

        string = (self.preamble + '\n' + above 
                 + title(self.PID, self.total, self._comment) 
                 + below + '\n'.join(content) )
        return string
    
    def new_channel(self, PIDs, BR, comment=None):
        '''
        Add a new decay channel. 
        PIDs - tuple of integers.
        BR - the branching ratio into that channel.
        comment - optional comment to be written to the 
                  right of that channel in __str__().
        '''
        self[PIDs]=BR
        if comment is not None: self._comments[PIDs]=comment

class Card(object):
    '''
    SLHA card object: a container for storing multiple SLHA.Block, 
    SLHA.NamedBlock and SLHA.Decay objects. Blocks and decays are stored in 
    OrderedDicts self.blocks and self.decays respectively. 
    Index syntax mycard[key] can be used to get or set elements of blocks or 
    decays possessed by the Card instance. If passed a string key, the card 
    instance will look up the first block in self.blocks possessing a parameter 
    with the given name while an int key will return the SLHA.Decay object for 
    that PID.
    '''
    def _parent_block(self, key):
        '''
        Returns the parent of a given string key. First searches for a Matrix 
        object with that name, then searches in self.matrices for a Matrix 
        containing that name and finally searches in self.blocks for a block 
        containing that name. Otherwise raises Key error.
        '''
        if self.has_matrix(key): return self.matrices
        
        for block in self.matrices.values():
            if key in block: return block
            
        for block in self.blocks.values():
            if key in block: return block
        
        return None

    def _container(self, key):
        '''
        Returns the container containing the indexed key. Used in overloading 
        __setitem__, __getitem__, __contains__ and __delitem__.
        '''
        if type(key) is int:
            return self.decays
        elif type(key) is str:
            return self._parent_block(key.lower())
        else:
            err = ('SLHA Card has integer keys for '
                   'DECAY and string keys for BLOCK.')
            raise ValueError(err)
        
    def __init__(self, blocks=None, decays=None, name=None):
        '''    Keyword arguments:
        blocks - a dictionary of items with which to initialise 
                 individual blocks in the card instance i.e. 
                 name:block pairs with block an SLHA.NamedBlock.
        decays - a dictionary of SLHA.Decay objects.
        matrices - a dictionary of SLHA.NamedMatrix objects.
        name - card name'''
        
        self.blocks = CaseInsensitiveOrderedDict()
        self.decays = CaseInsensitiveOrderedDict()
        self.matrices = CaseInsensitiveOrderedDict()
        self.name = name if name is not None else ''
        if blocks is not None:
            for bname, block in blocks.iteritems():
                self.blocks[bname] = NamedBlock(name=bname, data=block)  
        if decays is not None:
            for PID, decay in decays.iteritems():
                self.decays[PID]= Decay(PID,decay.total, data=decay)
            
    def __repr__(self):
        return ('<SHLA Card "{}": {} blocks, {} decays.>'.format(self.name,
                       len(self.matrices)+ len(self.blocks), len(self.decays)))
    def __contains__(self, key):
        container = self._container(key)
        return True if container is not None else False
    
    def __getitem__(self, key):
        container = self._container(key)
        if container is not None:
            return container[key.lower()]
        else:
            err = 'Key/Matrix "{}" not found in {}'.format(key, self)
            raise KeyError(err)
    
    def __delitem__(self, key):
        container = self._container(key)
        if container is not None:
            del container[key.lower()]
        else:
            err = 'Key/Matrix "{}" not found in {}'.format(key, self)
            raise KeyError(err)
    
    def __setitem__(self, key, value):
        container = self._container(key)
        if container is not None:
            return container.__setitem__(key.lower(), value)
        else:
            err = 'Key/Matrix "{}" not found in {}'.format(key, self)
            raise KeyError(err)
        
    def add_block(self, block, preamble=''):
        '''Append an SLHA.Block or NamedBlock to self.blocks.'''
        block.preamble = preamble
        if isinstance(block,Matrix):
            self.matrices[block.name] = block
        else:
            self.blocks[block.name] = block
        
    def add_decay(self, decay, preamble=''):
        '''Append an SLHA.Decay to self.decays.'''
        decay.preamble = preamble
        self.decays[decay.PID] = decay
    
    def add_entry(self, blockname, key, value, name=None):
        '''
        Add a new field in a given block. If the Card instance already  
        has such a block, a new field is appended. If the Card doesn't, a new 
        block is created.
        '''
        if self.has_block(blockname):
            self.blocks[blockname].new_entry(key, value, name=name)
        elif self.has_matrix(blockname):
            self.matrices[blockname].new_entry(key, value, name=name)
        else:
            if type(key) is tuple:
                container = Matrix
                namedcontainer = NamedMatrix
            else:
                container = Block
                namedcontainer = NamedBlock
                
            if name is not None:
                theblock = namedcontainer(name=blockname)
                theblock.new_entry(key, value, name=name)
            else:
                theblock = container(name=blockname)
                theblock.new_entry(key, value)
                
            self.add_block(theblock)
                
    def add_channel(self, PID, channel, partial, comment=None):
        '''
        Add a new channel in a given decay. The Decay for the given PID 
        must already exist in the Card instance.
        '''
        assert(self.has_decay(PID)),('Tried adding a decay channel '
                                     'for non existent decay PID')
        self.decays[PID].new_channel(channel, partial, comment=comment)
    
    def new_channel(self, PIDs, BR, comment=None):
        '''Append a new channel to a given Decay block.'''
        self[PIDs]=BR
        if comment is not None: self._comments[PIDs]=comment
        
    def has_block(self, name):
        return name.lower() in self.blocks 
    
    def has_matrix(self, name):
        return name.lower() in self.matrices
    
    def has_decay(self, PID):
        return PID in self.decays
    
    def write(self, filename, blockorder = [], preamble='',postamble=''):
        '''
        Write contents of Card in SLHA formatted style to "filename". 
        Makes use of the __str__ methods written for the SLHA elements. 
        Keyword arguments:
            blockorder - Specify an ordering for printing the block names. 
                         Names given in blockorder will be printed first in the 
                         order specified and others will be printed as ordered 
                         in self.blocks
            preamble - Some text to write before the Block and Decay information
            postamble - Some text to write after the Block and Decay information
        '''
        
        with open(filename,'w') as out:
            out.write(preamble)
            
            allblocks = self.blocks.keys() + self.matrices.keys()
            other_blocks = [b for b in allblocks if b not in blockorder]

            for block in blockorder:
                if self.has_block(block):
                    out.write(str(self.blocks[block]))
                elif self.has_matrix(block):
                    out.write(str(self.matrices[block]))
                    
            for block in other_blocks:
                if self.has_block(block):
                    out.write(str(self.blocks[block]))
                elif self.has_matrix(block):
                    out.write(str(self.matrices[block]))
                                
            for decay in self.decays.values():
                out.write(str(decay))
            out.write(postamble)

class SLHAReadError(Exception): # Custom error name for reader
    pass

def read(card):
    '''
    SLHA formatted card reader. Blocks and Decay structures are read 
    into an SLHA.Card object which is returned. Comments are specified by the # 
    character. Comments to the right of the structures as wel as the individual 
    fields are stored.
    '''
    
    def get_comment(line):
        '''
        Returns characters following a "#" in line.
        returns empty string if match is not found.
        '''
        match = re.match(r'.*#\s*(.*)\s*', line)
        if match: return match.group(1).strip()
        else: return ''

    thecard = Card()
    pcard = open(card,'r')
    lines = iter(pcard)
    counter = 0
    
    try:
        while True:
            counter+=1 # keep track of line number
            stop=False
            try: ll=(last_line.strip())
            except NameError: ll = (lines.next()).strip()
        
            if not ll: continue

            first_chars = re.match(r'\s*(\S+).*',ll).group(1).lower()
            
            if first_chars=='block':
                try:
                    block_details = re.match(r'\s*block\s+([^\n]+)',ll,
                                             re.IGNORECASE).group(1)
                except AttributeError:
                    err = ('Invalid block format encountered ' + 
                          'in line {} of {}.'.format(counter, card) )
                    raise SLHAReadError(err)
                    
                bname = block_details.split('#')[0].strip()
                
                comment = get_comment(ll)
                
                block_data, last_line, stop = read_until(lines,'block','decay')
                
                elements = []
                
                for datum in block_data:
                    counter +=1                    
                    is_comment = re.match(r'\s*#.*',datum)
                
                    if (not datum.strip() or is_comment): continue
                    
                    info = re.match(r'\s*((?:\d+\s+)+)\s*(\S+).*',
                                    datum)
                    if not info:
                        print datum
                        print ('Ignored datum in block '+
                                '{},'.format(theblock.name) +
                                ' (line {} of {})'.format(counter, card))
                        continue
                    
                    key, value = info.group(1), info.group(2)
                    
                    try:
                        key = int(key)
                    except ValueError:
                        key = tuple( map(int, key.split()) )

                    dname = get_comment(datum)
                    
                    try:
                        entry = float(value)
                    except ValueError:
                        entry = value
                    finally:
                        elements.append((key,value,dname))
                
                
                if type(elements[0][0]) is tuple:
                    theblock = NamedMatrix(name=bname, comment=comment)
                else:
                    theblock = NamedBlock(name=bname, comment=comment)
                                
                for ele in elements:
                    theblock.new_entry(*ele)
                
                thecard.add_block(theblock)

            elif first_chars=='decay':
                try:
                    decay_details = re.match(r'\s*decay\s+(.+)',ll,
                                             re.IGNORECASE).group(1)
                except AttributeError:
                    err = ('Invalid decay format encountered' + 
                          'in line {} of {}.'.format(counter, card) )
                    raise SHLAReadError(err)
                    
                info = re.match(r'\s*(\d+)\s+(\S+)\s+.*', decay_details)
                PID, total = info.group(1), info.group(2)
                
                comment = get_comment(decay_details)
                    
                thedecay = Decay(PID=int(PID), total=float(total), 
                                 comment=comment)
                
                decay_data, last_line, stop = read_until(lines,'block','decay')
                
                for datum in decay_data:
                    counter +=1                    
                    is_comment = re.match(r'\s*#.*',datum)
                
                    if ((not datum.strip()) or (is_comment)): continue

                    info = re.match(r'\s*(\S+)\s+(\d+)\s+(.+)',datum)
                    if not info:
                        print datum
                        print ('Ignored above datum in decay '+
                                '{},'.format(thedecay.PID) +
                                ' (line {} of {})'.format(counter, card))
                        continue
                        
                    BR, nout = info.group(1), info.group(2)
                    PIDinfo = info.group(3).split('#')[0]
                    
                    PIDs = tuple( map(int, PIDinfo.split()) )
                    
                    if len(PIDs)!=int(nout):
                        print ("Number of external particles in column 2 doesn't "
                               "match number of subsequent columns:")
                        print datum
                        print ('Ignored above datum in decay '+
                                '{},'.format(thedecay.PID) +
                                ' (line {} of {})'.format(counter, card))
                        continue

                    comment = get_comment(datum)
                        
                    thedecay.new_channel(PIDs, float(BR), comment=comment)
                    
                thecard.add_decay(thedecay)
                
            if stop: raise StopIteration
            
    except StopIteration:
        pcard.close()

    return thecard

def read_until(lines, here, *args):
    '''
    Loops through an iterator of strings by calling next() until 
    it reaches a line starting with a particular string.
    Case insensitive.
    Args:
        lines - iterator of strings
        here - string (plus any further argumnts). 
               Reading will end if the line matches any of these.
    Return:
        lines_read - list of lines read
        line - last line that was read (containing string "here")
    '''
    end_strings = [here.lower()]+[a.lower() for a in args]
    lines_read = []
    line = ''
    stopiter = False
    while not any([line.strip().lower().startswith(x) for x in end_strings]):
        try:
            line = lines.next()
            lines_read.append(line.strip('\n'))
        except StopIteration:
            stopiter=True
            break
    try:
        if stopiter:
            return lines_read, '', stopiter
        else:
            return lines_read[:-1],lines_read[-1], stopiter
    except IndexError:
        return [],'',stopiter

if __name__=='__main__':
    b= CaseInsensitiveOrderedDict()
    b['buMs']=1
    print 'bums' in b
    print b.keys()
    # a = CaseInsensitiveOrderedDict({'oNe':1,'twO':2,'THRee':3})
    pass