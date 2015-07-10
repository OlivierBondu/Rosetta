from internal import Basis
import SILHBasis as SB
import math
from math import sqrt
from itertools import combinations_with_replacement as comb
from itertools import product
from internal import PID
################################################################################
flavmat = Basis.flavour_matrix
# Warsaw basis class
class WarsawBasis(Basis.Basis):
    name = 'warsaw'
    ###### declare blocks
    # [Tab. 1]
    WBV2H2 = ['cGG','ctGG','cWW','ctWW','cBB','ctBB','cWB','ctWB']
    
    WBH4D2 = ['cH','cT']
    
    WBH6 = ['c6H']
    
    WBV3D3 = ['c3W','c3G','ct3W','ct3G']
    
    cu = flavmat('cu',kind='general',domain='complex')
    cd = flavmat('cd',kind='general',domain='complex')
    ce = flavmat('ce',kind='general',domain='complex')

    WBF2H3 = cu + cd + ce
    
    cHl  = flavmat('cHl' ,kind='hermitian',domain='complex')
    cpHl = flavmat('cpHl',kind='hermitian',domain='complex')
    cHe  = flavmat('cHe' ,kind='hermitian',domain='complex')
    cHq  = flavmat('cHq' ,kind='hermitian',domain='complex')
    cpHq = flavmat('cpHq',kind='hermitian',domain='complex')
    cHu  = flavmat('cHu' ,kind='hermitian',domain='complex')
    cHd  = flavmat('cHd' ,kind='hermitian',domain='complex')
    cHud = flavmat('cHud',kind='general',domain='complex')
    WBF2H2D = cHl + cpHl + cHe + cHq + cpHq + cHu + cHd + cHud
    
    # affects Gf input, Warsaw <-> SILH translation
    WB4F = ['cll1221','cll1122','cpuu3333'] 
    ######
    blocks = {'WBV2H2':WBV2H2, 'WBH4D2':WBH4D2, 'WBH6':WBH6, 'WBV3D3':WBV3D3, 
              'WBF2H3':WBF2H3, 'WBF2H2D':WBF2H2D, 'WB4F':WB4F}
    
    independent = WBH4D2 + WBH6 + WBV3D3 + WBF2H3  + WBV2H2 + WBF2H2D + WB4F
    
    required_masses = set([y for x in PID.values() for y in x.values()])
    required_inputs = {1, 2, 4, 8} # aEWM1, Gf, MZ, MH
        
    def calculate_inputs(self): # calculate a few required EW params from aEWM1, Gf, MZ
        ee2 = 4.*math.pi/self.inputs['aEWM1'] # EM coupling squared
        gs2 = 4.*math.pi*self.inputs['aS'] # strong coupling squared
        Gf, MZ = self.inputs['Gf'], self.inputs['MZ']
        s2w = (1.- sqrt(1. - ee2/(sqrt(2.)*Gf*MZ**2)))/2. # sin^2(theta_W)
        c2w = (1.-s2w)
        gw2 = ee2/s2w # SU(2) coupling squared
        gp2 = gw2*s2w/c2w # Hypercharge coupling squared
        vev =  2.*MZ*sqrt(c2w/gw2)
        return s2w, c2w, ee2, gw2, gp2, MZ, vev, gs2
        
    # def translate(self):
    #     if self.target_basis=='mass':
    #         from MassBasis import MassBasis
    #         self.newname='Mass'
    #         instance = MassBasis()
    #         return self.translate_to_mass(instance)
    #     elif self.target_basis=='higgs':
    #         from HiggsBasis import HiggsBasis
    #         self.newname='Higgs'
    #         instance = HiggsBasis()
    #         return self.translate_to_mass(instance)
    #     else:
    #         raise NotImplementedError
            
    def to_mass(self, instance):
        s2w, c2w, ee2, gw2, gp2, MZ, vev, gs2 = self.calculate_inputs() 
        MH = self.mass[25]
        MW = MZ*sqrt(c2w)
        
        A = self
        B = instance

        def delta(i,j):
            return 1. if i==j else 0.
                    
        def f(T3,Q,i,j): # [eqn (4.11)]
                return delta(i,j)*( -Q*A['cWB']*gw2*gp2/(gw2-gp2)
                                   + (A['cT']-dv)*(T3 + Q*gp2/(gw2-gp2)))

        # Higgs vev shift [eqn (4.8)]
        dv = (A['cpHl11']+A['cpHl22'])/2.-A['cll1221']/4.
        
        # W mass shift [eqn (4.9)]
        B['dM'] = ( gw2*A['cT'] - gp2*gw2*A['cWB']-gp2*dv )/(gw2-gp2)
        # W/Z chiral coupling deviations
        for i,j in comb((1,2,3),2):
            ind = '{}{}'.format(i,j)
            tail = [ind] if i==j else [ind+'Re', ind+'Im']
            for t in tail:
                # [eqn (4.10)]
                B['dGLwl%s' % t] = (A['cpHl%s' % t] + f(1./2.,0.,i,j) 
                                                    - f(-1./2.,-1.,i,j))
                B['dGLzv%s' % t] = (1./2.*A['cpHl%s' % t] - 1./2.*A['cHl%s' % t] 
                                                          + f(1./2.,0.,i,j))
                B['dGLze%s' % t] = (-1./2.*A['cpHl%s' % t] - 1./2.*A['cHl%s' % t] 
                                                           + f(-1./2.,-1.,i,j))
                B['dGRze%s' % t] = - 1./2.*A['cHe%s' % t] + f(0.,-1.,i,j)
                # [eqn (4.12)]
                B['dGLwq%s' % t] = (A['cpHq%s' % t] + f(1./2.,2./3.,i,j)
                                                    - f(-1./2.,-1./3.,i,j))
                B['dGLzu%s' % t] = (1./2.*A['cpHq%s' % t] - 1./2.*A['cHq%s' % t] 
                                                          + f(1./2.,2./3.,i,j))
                B['dGLzd%s' % t] = (-1./2.*A['cpHq%s' % t] 
                                  - 1./2.*A['cHq%s' % t] + f(-1./2.,-1./3.,i,j))
                B['dGRzu%s' % t] = - 1./2.*A['cHu%s' % t] + f(0.,2./3.,i,j)
                B['dGRzd%s' % t] = - 1./2.*A['cHd%s' % t] + f(0.,-1./3.,i,j)
                # [eqn (4.13)]
                B['CLwl%s' % t] = B['dGLwl%s' % t]
                B['CLzv%s' % t] = B['dGLzv%s' % t]
                B['CLze%s' % t] = B['dGLze%s' % t]
                B['CRze%s' % t] = B['dGRze%s' % t]
                B['CLwq%s' % t] = B['dGLwq%s' % t]
                B['CLzu%s' % t] = B['dGLzu%s' % t]
                B['CLzd%s' % t] = B['dGLzd%s' % t]
                B['CRzu%s' % t] = B['dGRzu%s' % t]
                B['CRzd%s' % t] = B['dGRzd%s' % t]
        
        # Treat dGRwq separately as it has more flavour components
        dGRwq = flavmat('dGRwq', kind='general', domain='complex')
        for coeffW, coeffM in zip(self.cHud, dGRwq):
            B[coeffM] = -1./2.*A[coeffW]
            cvff = coeffM.replace('dG','C')
            B[cvff] = B[coeffM]
        
        # Higgs couplings to W/Z [eqn (4.14)]
        B['dCw'] = ( -A['cH']*(gw2-gp2) - A['cWB']*4.*gw2*gp2 
                    + A['cT']*4.*gw2 - dv*(3.*gw2+gp2) )/(gw2-gp2)
        B['dCz'] = -A['cH'] - 3.*dv 
        
        # Two derivative field strength interactions [eqn (4.15)]
        B['Cgg']  = A['cGG'] 
        B['Caa']  = A['cWW'] + A['cBB'] - 4.*A['cWB']
        B['Czz']  = ( gw2**2*A['cWW'] + gp2**2*A['cBB'] 
                     + 4.*gw2*gp2*A['cWB'] )/(gw2+gp2)**2
        B['Czbx'] =  -(2./gw2)*(A['cT'] - dv) 
        B['Cza']  = ( gw2*A['cWW'] - gp2*A['cBB'] 
                      - 2.*(gw2-gp2)*A['cWB'] )/(gw2+gp2)
        B['Cabx'] =  2./(gw2-gp2)*((gw2+gp2)*A['cWB'] - 2.*A['cT'] + 2.*dv) 
        B['Cww']  =  A['cWW']
        B['Cwbx'] =  2./(gw2-gp2)*(gp2*A['cWB'] - A['cT'] + dv) 
        
        B['CTgg'] = A['ctGG'] 
        B['CTaa'] =  A['ctWW'] + A['ctBB'] - 4.*A['ctWB']
        B['CTzz'] = ( gw2**2*A['ctWW'] + gp2**2*A['ctBB'] 
                      + 4.*gw2*gp2*A['ctWB'] )/(gw2+gp2)**2
        B['CTza'] = ( gw2*A['ctWW'] - gp2*A['ctBB'] 
                      - 2.*(gw2-gp2)*A['ctWB'] )/(gw2+gp2)
        B['CTww'] =  A['ctWW']
        
        
        # solution for  [eqn (4.16)]
        # dy*cos(phi) == X
        # dy*sin(phi) == Y
        def dy_sf(X,Y): 
            R = sqrt(X**2+Y**2)
            if R==0: 
                return 0., 0.
            elif Y==0.:
                return X, 0.
            else:
                signY = Y/abs(Y)
                if X*Y > 0.:
                    return R*signY, abs(Y)/R
                else:
                    return -R*signY, -abs(Y)/R

        # Yukawa type interaction coefficients [eqns. (4.16) & (4.17)]
        for i,j in product((1,2,3),(1,2,3)): 
            diag = delta(i,j)*(A['cH']+dv)
            diag2 = 2.*delta(i,j)*A['cH']
            for f in ('u','d','e'):
                mi, mj = self.mass[ PID[f][i] ],self.mass[ PID[f][j] ] 
                name = '{}{}{}'.format(f,i,j)
                if (mi and mj):
                    c_Re, c_Im = A['c'+name+'Re'], A['c'+name+'Im']
                    
                    dy_cosphi = vev*c_Re/sqrt(2.*mi*mj) - diag
                    dy_sinphi = vev*c_Im/sqrt(2.*mi*mj)
                    
                    B['dY'+name], B['S'+name]  = dy_sf(dy_cosphi, dy_sinphi)
                    
                    B['Y2{}Re'.format(name)] = 3.*vev*c_Re/sqrt(2.*mi*mj) - diag2
                    B['Y2{}Im'.format(name)] = 3.*vev*c_Im/sqrt(2.*mi*mj)
        
        # Triple gauge couplings [eqn. (4.18)]
        B['dG1z'] = (gw2+gp2)/(gw2-gp2)*( -A['cWB']*gp2 + A['cT'] - dv )
        B['dKa']  = A['cWB']*gw2
        B['dKz']  = (-A['cWB']*2.*gw2*gp2 + (gw2+gp2)*(A['cT'] - dv))/(gw2-gp2)
        B['La']   = -A['c3W']*3./2.*gw2**2
        B['Lz']   = B['La']
        B['KTa']  = A['ctWB']*gw2
        B['KTz']  = -A['ctWB']*gp2
        B['LTa']  = -A['ct3W']*3./2.*gw2**2
        B['LTz']  = B['LTa']
        B['C3g']  = A['c3G']
        B['CT3g']  = A['ct3G']
        
        # Quartic gauge couplings [Sec 3.7] [eqn (3.23)] 
        B['dGw4'] = 2.*c2w*B['dG1z']
        B['dGw2z2'] = 2.*B['dG1z']
        B['dGw2za'] = B['dG1z']
        
        # two derivative quartic gauge couplings [Sec 3.7] [eqn (3.24)] 
        B['Ldw4'] = -gw2/2./MW**2*B['Lz']
        B['LTdw4'] = -gw2/2./MW**2*B['LTz']
        B['Ldzdwzw'] = -gw2*c2w/MW**2*B['Lz']
        B['LTdzdwzw'] = -gw2*c2w/MW**2*B['LTz']
        B['Ldzdwaw'] = -ee2/MW**2*B['Lz']
        B['LTdzdwaw'] = -ee2/MW**2*B['LTz']
        B['Ldadwaw'] = -sqrt(ee2*gw2*c2w)/MW**2*B['Lz']
        B['LTdadwaw'] = -sqrt(ee2*gw2*c2w)/MW**2*B['LTz']
        B['Ldadwzw'] = -sqrt(ee2*gw2*c2w)/MW**2*B['Lz']
        B['LTdadwzw'] = -sqrt(ee2*gw2*c2w)/MW**2*B['LTz']
        B['Ldgg3'] = 3.*sqrt(gs2)**3/vev**2*B['C3g']
        B['LTdgg3'] = 3.*sqrt(gs2)**3/vev**2*B['CT3g']
        
        # Higgs cubic interaction [eqn. (4.19)]
        B['dL3']  =  -MH**2/(2.*vev**2) * (3.*A['cH'] + dv) - A['c6H']
        
        # Couplings of two Higgs bosons to gluons [Sec 3.8]
        # [eqn (3.27)] copied from HiggsBasis implemetation
        B['Cgg2'], B['CTgg2'] = B['Cgg'], B['CTgg']
        
        # 4-fermion 
        B['cll1122'] = A['cll1122']
        B['cpuu3333'] = A['cpuu3333']
        B['cll1221'] = A['cll1221']
        
        # print B.card.blocks
        # print B.card.blocks['mbvertex']
        # W mass shift
        self.mass[24] = MW + B['dM']
        return B
        
    def to_silh(self, instance):
        s2w, c2w, ee2, gw2, gp2, MZ, vev, gs2 = self.calculate_inputs() 
        MH = self.mass[25]
        lam = -MH**2/(2.*vev**2) # Higgs self-coupling
        
        W = self
        S = instance
        
        def delta(i,j):
            return 1. if i==j else 0.
        
        S['sBB'] = W['cBB'] - 4.*W['cWB'] + W['cWW']
        S['stBB'] = W['ctBB'] - 4.*W['ctWB'] + W['ctWW']
        S['s2W'] = W['cll1221']/gw2
        S['s2B'] = (2.*W['cll1122'] + W['cll1221'])/gp2
        S['s2G'] = 3.*W['cpuu3333']/gs2
        
        S['sB'] = (4.*W['cWB'] - W['cWW'] 
                  - (4.*W['cHl11'] + 4.*W['cll1122'] + 2.*W['cll1221'])/gp2)
        S['sW'] = W['cWW'] - (2.*W['cll1221'] - 4.*W['cpHl11'])/gw2        
        S['sHW'] = - W['cWW']
        S['stHW'] = - W['ctWW']
        S['sHB'] = W['cWW'] - 4.*W['cWB']
        S['stHB'] = W['ctWW'] - 4.*W['ctWB']
        S['sH'] = W['cH'] - 3./4.*W['cll1221'] + 3.*W['cpHl11']
        S['sT'] = W['cT'] - W['cHl11'] - W['cll1122']/2. - W['cll1221']/4.
    
        S['s6H'] = W['c6H'] - 2.*lam*(W['cll1221'] - 4.*W['cpHl11'])
        
        def sHf(wc, Yf, i, j):
            if 'Im'!=wc[-2:]:
                return W[wc] + delta(i,j)*2.*Yf*W['cHl11'] 
            else:
                return W[wc]

        def spHf(wc, i, j):
            if 'Im'!=wc[-2:]:
                return W[wc] - delta(i,j)*W['cpHl11']
            else:
                return W[wc]
            
        for i,j in comb((1,2,3),2):
            ind = '{}{}'.format(i,j)
            tail = [ind] if i==j else [ind+'Re', ind+'Im']
            for t in tail:
                S['sHl'+t] = sHf('cHl'+t, -1./2., i, j)
                S['sHe'+t] = sHf('cHe'+t, -1., i, j)
                S['sHq'+t] = sHf('cHq'+t, 1./6., i, j)
                S['sHu'+t] = sHf('cHu'+t, 2./3., i, j)
                S['sHd'+t] = sHf('cHd'+t, -1./3., i, j)
                S['spHl'+t] = spHf('cpHl'+t, i, j)
                S['spHq'+t] = spHf('cpHq'+t, i, j)
                if i==j==1:
                    S['sHl'+t] = 0.
                    S['spHl'+t] = 0.
        
        def sf(wc, i, j):
            mass = self.mass[ PID[f][i] ]
            yuk = mass/vev/sqrt(2.)
            if 'Im'!=wc[-2:]:
                return W[wc] - delta(i,j)*yuk*(W['cll1221'] - 4.*W['cpHl11'])
            else:
                return W[wc]
            
        # [eqn (5.9)]
        for i,j in product((1,2,3),(1,2,3)): # flavour loop
            ind = ['{}{}{}'.format(i,j,cplx) for cplx in ('Re','Im')]
            for t in ind: # Re, Im loop
                for f in ('u','d','e'): # fermion loop
                    scoeff, wcoeff = 's{}{}'.format(f,t),'c{}{}'.format(f,t)
                    S[scoeff] = sf(wcoeff, i, j)
        
        # trivial translation, sX==cX
        sHud = flavmat('sHud', kind='general', domain='complex')
        others = ['sGG','stGG','s3W','st3W','s3G','st3G']
        trivial = sHud+others
        for coeff in trivial:
            wcoeff = 'c'+coeff[1:]
            S[coeff] = W[wcoeff]
        
        return S

################################################################################