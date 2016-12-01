from itertools import combinations_with_replacement as comb
import argparse
import os
from ...internal import SLHA
from ... import session, settings, implemented_bases
from ..interface import RosettaInterface, allowed_flav

# Higgs decay channels
h_channels = {'bb':(5,-5),'mumu':(13,-13), 'tautau':(15,-15), 
                'gammagamma':(22,22), 'ZZ':(23,23), 'WW':(24,-24)}

# construct & name double Higgs decay channels
hh_channels={}

for ch1, ch2 in comb(h_channels.keys(), 2):
    if ch2=='bb': ch1, ch2 = ch2, ch1
    
    id1, id2 = h_channels[ch1], h_channels[ch2]
    
    if ch1==ch2:
        ch = '4'+ch1[:len(ch1)/2]
    else:
        ch = '2'+ch1[:len(ch1)/2]+'2'+ch2[:len(ch2)/2]
        
    hh_channels[ch] = (h_channels[ch1], h_channels[ch2])

# allowed values for command line options
allowed_channels = ['all'] + hh_channels.keys()
allowed_sqrts = (7,8,13,14,100)
allowed_flav = ('general', 'diagonal', 'universal')

class DiHiggsInterface(RosettaInterface):
    
    interface = 'dihiggs'

    description = ("Compute production cross section times branching fractions "
                   "for double Higgs production at the LHC")

    helpstr = ("Double Higgs production at the LHC")

    parser_args = {
        ('param_card',):{
            'metavar':'PARAMCARD', 'type':str, 
            'help':'Input parameter card.'
        },
        ('--sqrts',):{
            'type':int, 'choices':allowed_sqrts, 'default':8, 'metavar':'',
            'help':('Specify pp collider centre-of mass energy in TeV. '
                    +'Allowed values are: '
                    +', '.join([str(s) for s in allowed_sqrts])
                    +' (default = 8).')
        },
        ('--flavor',):{
            'type':str, 'default':'general', 'choices':allowed_flav, 
            'metavar':'FLAVOR',
            'help':('Specify flavor structure. Allowed values are: '+
                    ', '.join(allowed_flav)+' (default = general)')
        },
        ('--channel',):{
            'type':str, 'default':['all'], 'choices':allowed_channels, 
            'metavar':'CHANNEL',
            'nargs':'+',
            'help':('Specify one or more decay channels. Allowed values are: '+
                    ', '.join(allowed_channels)+' (default = all)')
        },
        ('--params',):{
            'action':'store_true',
            'help':('Also print out values of effective Lagrangian parameters')
        }
        # ('--ehdecay',):{
        #     'action':'store_true',
        #     'help':'Interface with eHDECAY for Higgs branching fractions.'
        # }
        # ('--no-ehdecay',):{
        #     'action':'store_true',
        #     'help':"Don't interface with eHDECAY for Higgs branching fractions."
        # }
    }

    def __call__(self, args):
        basis_instance = self.from_param_card(args.param_card,
                                              flavor=args.flavor)
        
        BC_instance = basis_instance.translate(target='bsmc')  
             
        from dihiggs import get_xs_and_br, get_dihiggs_params
        
        kl, kt, c2, cg, c2g = get_dihiggs_params(BC_instance)
        
        xs, err, decays = get_xs_and_br(BC_instance, sqrts=args.sqrts)
        
        
        session.drawline(text='dihiggs results', ignore_silent=True)
        
        if (args.params):
            session.stdout('Effective Lagrangian parameters:')
            session.stdout(('kl = {:.3e}, kt = {:.3e}, '
                            'c2 = {:.3e}, \ncg = {:.3e}, '
                            'c2g = {:.3e}\n').format(kl, kt, c2, cg, c2g))
        
        session.stdout('Cross section at {} TeV: {:.3e} fb'.format(args.sqrts, xs))
        session.stdout('')
        session.stdout('Uncertainties:')
        session.stdout('    scale (+ {scalep:.3e}, {scalem:.3e}), '.format(**err))
        session.stdout('    PDF +- {PDF:.3e} , '.format(**err))
        session.stdout('    alphaS +- {alphaS:.3e} , '.format(**err))
        session.stdout('    top mass +- {mtop:.3e} fb'.format(**err))
        session.stdout('')
        session.stdout('Decay modes:')        
        session.stdout('')
        session.stdout('    channel       BR             xs x BR (fb)')
        session.stdout('  -------------------------------------------')
                
        if 'all' in args.channel:
            channels = hh_channels.keys()
        else:
            channels = args.channel
        
        for ch in channels:
            id1, id2 = hh_channels[ch]
            
            BR = decays[id1]*decays[id2]
            if id1!=id2: BR*=2.
    
            mustr = '    {:<10}    {:.3e}      {:.3e}'.format(ch, BR, xs*BR)
        
            session.stdout(mustr)
        
        session.drawline()
        session.exit(0)
        