# -*- coding: utf-8 -*-
"""
Created on Fri Dec 18 11:18:03 2020

@author: Admin
"""
# code credit: Janathan Jouty

import sys
sys.path.append('C:/Users/Admin/PySpike')# import pyspike

# Recording
notebooks_path = "C:/Users/Admin/Desktop/hennig_project/download/rgcclassification/sample_dara_hamed/"
data_path = "C:/Users/Admin/Desktop/hennig_project/download/rgcclassification/sample_dara_hamed/"
data_dir ="C:/Users/Admin/Desktop/hennig_project/download/rgcclassification/sample_dara_hamed/"
#filenames=['2019_07_21_wl_secondmouce.mat','2018_12_12_left_nasal.mat','2020_01_17_rhalf1.mat','2018_11_28_WT_Left.mat','2018_11_29_WT1_Left.mat','2019_07_17_mrg.mat','2019_07_16_lw.mat','2020_01_25_r1.mat','2020_02_04_l1_before.mat','2020_02_06_r1_before.mat','2020_01_25_left.mat','2020_01_16_wl.mat']
#filenames=['2020_02_07_rd10_l1_before.mat','2020_02_07_rd10_l2.mat','2020_02_07_rd10_r1_before.mat','2020_02_05_rd10_l1_before.mat','2020_02_05_rd10_r1_before.mat']
filenames=['2020_02_07_rd10_l1_before.mat','2020_02_07_rd10_r1_before.mat','2020_02_05_rd10_l1_before.mat','2020_02_05_rd10_r1_before.mat']


# stimulus information
#report_filenames  = [ data_path+"2019_07_17_mrg_report.txt" ]
#trigger_filenames = [ data_path+"trigger_2019_07_17_mrg.mat" ]
report_filenames  = [ data_path+"2020_02_07_rd10_l1_before_report.txt",
#                     data_path+"2020_02_07_rd10_l2_report.txt",## this recording is without drug
                     data_path+"2020_02_07_rd10_r1_before_report.txt",
                     data_path+"2020_02_05_rd10_l1_before_report.txt",
                     data_path+"2020_02_05_rd10_r1_before_report.txt"]
                     


trigger_filenames = [   data_path+"2020_02_07_rd10_l1_before_trigger.mat",
#                        data_path+"2020_02_07_rd10_l2_trigger.mat",
                        data_path+"2020_02_07_rd10_r1_before_trigger.mat",
                        data_path+"2020_02_05_rd10_l1_before_trigger.mat",
                        data_path+"2020_02_05_rd10_r1_before_trigger.mat"]
#
# Set to False to reload the spike data from the original hdf5 files 
LOAD_STORED_SPIKES = False

# Set to False to re-compute the distance matrices
LOAD_STORED_DISTANCES = True


# Unit selection

# estimate the spatial spread of spikes for each unit
# poorly sorted units have a wide spread and/or high eccentricity
EVAL_THRES = 0.17 # threshold for average spread
ECC_THRES = 0.85 # threshold for eccentricity

# exclude units with insufficient spike counts (per trial)
MIN_SPIKES_FF = 1 # min spikes in Full Field stimulus
MIN_SPIKES_CHIRP =20# min spikes in Chirp stimulus

# set to True to apply an additional fiilter based on the STA
# note this excludes units without a valid STA
# we found not all RGCs have a clean STA, so this will exclude valid neurons
# doing this reduces the number of clusters considerably
FILTER_STA = True
STA_MAX_DIST = 0.7
STA_MAX_ASYM = 0.9

# set to True to save the figures generated below
SAVE_FIGS = False


import os.path, sys
from os.path import dirname, join as pjoin
import scipy.io as sio

from herdingspikes import *
from spikeclass_metrics import *

import numpy as np
import seaborn as sns
import matplotlib as matplotlib

import re
import h5py
import pyspike as spk

import joblib

import scipy.cluster as cluster
import scipy.spatial.distance as distance
from scipy.spatial.distance import squareform
import sklearn.metrics.cluster as metrics
from sklearn.metrics import confusion_matrix

from sta import *
from spikeutilities import *

# plot parameters
rcParams = {
   'axes.labelsize': 12,
   'font.size': 10,
   'legend.fontsize': 12,
   'xtick.labelsize': 12,
   'ytick.labelsize': 12,
   'text.usetex': False,
   'figure.figsize': [4, 2.5] # instead of 4.5, 4.5
   }

get_cluster_inds = lambda C, cl: np.where(C==cl)[0]
data_path=data_dir
i = 0
base_path = data_path + filenames[i]
base_path = base_path.replace('.hdf5','__save_.npy')
mkp = lambda n: base_path.replace('_.npy','_'+n+'.npy')



# Stuff that will be filled from spikeclass
Times = {}
ClusterIDs = {}
ClusterLoc = {}
ClusterSizes = {}
# Stuff we want to compute
sCorrs = {}
ClusterEvals = {}
Sampling = 1#7062.058198545425 # copied from previous output
cell_names=[]
dsi_cels=[]
esta={}
#esta= sio.loadmat('e_STA 2019_07_17_mrg.mat')
#Data=esta['Data']
#times=Data['time_sta']
#e_sta=Data['e_sta']
E_STA=[]
esta_all={}
if LOAD_STORED_SPIKES == False:
    ncl={}
    for i,f in enumerate(filenames):
        mat_fname = pjoin(data_dir, f)
        mat_contents = sio.loadmat(mat_fname)

#        O = spikeclass(sf)
        Times[i] = mat_contents['data']*Sampling
        ClusterIDs[i]= mat_contents['ClusterIDs']
        ncl[i] = len(unique(ClusterIDs[i]))
        
        esta_fname = pjoin(data_dir, 'e_STA '+f)
        try:
            ESTA=sio.loadmat(esta_fname)['Data'][0]
            esta[i]= ESTA[0:-1]#['e_sta']# trigerss are removed
            esta_all=np.hstack((esta_all,esta[i]))

        except IOError:
            esta[i]= [None] * ncl[i]
            print( "No e-sta" , f)
            esta_all=np.hstack((esta_all,[None] * ncl[i]))

        print("Number of units: %d" % ncl[i])

        E_STA.append(np.asarray(esta[i]))
        cell_names.append(np.asarray(mat_contents['Chname']))
        if '2019_07_21_wl_secondmouce.mat' in f:# this dataset does not have moving bar stimulus manualy set to zero
            dsi_cels=np.hstack((dsi_cels,np.ones(ncl[i], dtype=bool)))
          
#            dsi_cels.append(np.ones(ncl[i], dtype=bool))
        else: 
            dsi_cels=np.hstack((dsi_cels,np.zeros(ncl[i], dtype=bool)))

#            dsi_cels.append(np.zeros(ncl[i], dtype=bool))  
esta_all=np.delete(esta_all, 0)

#%% chech if the sta is significant

def sta_sif(esta_i):

           
 #   esta_i=np.asarray(esta_all[i][3].flatten())
    esta_i_basline=esta_i[30:]
    esta_i_evoked=esta_i[:25]
    esta_i_p=np.hstack((esta_i_basline, np.max(esta_i_evoked)))
    esta_i_t=np.hstack((esta_i_basline, np.min(esta_i_evoked))) 

    df= pd.DataFrame(esta_i_p,columns=['Data_p'])
    df['Data_t']=esta_i_t    
    df['Data_zscore_p']=(df['Data_p']-df['Data_p'].mean())/df['Data_p'].std(ddof=0)
    df['Data_zscore_t']=(df['Data_t']-df['Data_t'].mean())/df['Data_t'].std(ddof=0)
    df['pval_p']=(1-ndtr(df['Data_zscore_p']))
    df['pval_t']=(1-ndtr(-df['Data_zscore_t']))   
    alpha=.0001
    
    df['statistically_signicicance']=(df.pval_p.iloc[-1]<alpha) |(df.pval_t.iloc[-1]<alpha)#.astype(int) .astype(int)

    sta_sig_condition=False
    if np.nansum(df['statistically_signicicance'])>0:
        sta_sig_condition=True
    return sta_sig_condition    

#%% find signigicant STAs       

Cell_names = []
i=-1
for sublist in cell_names:
    i=i+1
    
    for val in sublist[0]:
        Cell_names.append(filenames[i][:-4]+"_"+val[0])
Cell_names=np.asarray(Cell_names)   

#%
from scipy.special import ndtr as ndtr
import pandas as pd
from scipy.stats import norm
from scipy import stats
from scipy import signal


def ztests(x,m,sigma):
    samplesize=size(x)
    ser=sigma/np.sqrt(samplesize)
    zval=(x.mean()-m)/ser
    
    norm.pdf(x)
    pp =2*norm.cdf(-abs(zval))   
    return pp


stas_dis=[]
with_sta_cells=np.zeros(len(esta_all),dtype=bool)

high_snr=np.zeros(len(esta_all),dtype=bool)
p_values=np.zeros(len(esta_all),dtype=bool)
mean_var_ratio=[]
min_maz=np.zeros(len(esta_all))
psd_all=[]

for i in range(len(esta_all)):
    freqsl, psd = signal.welch(esta_all[i][3].flatten(),25, nperseg=50)

    psd_all.append(psd)

    if not(esta_all[i]==None):
        if len(esta_all[i][3])>1:
            esta_i=np.asarray(esta_all[i][3].flatten())


            with_sta_cells[i]=True

            peak=esta_i[np.argmax(esta_i)]
            trough=esta_i[np.argmin(esta_i)]


            k2, p = stats.normaltest(esta_i)
            stds=np.std(esta_i[26:])
            avgs=np.average(esta_i[26:])

            from statsmodels.stats import weightstats as stests
            
            xmax=np.max(esta_i[:26])
            xmin=np.min(esta_i[:26])

            m=np.mean(esta_i[26:])
            sigma=np.std(esta_i[26:])

            p1=ztests(xmax,m,sigma)
            p2=ztests(xmin,m,sigma)
            singi= sta_sif(esta_i)
            
          
            p_values[i]=singi#p<.05#(p1<.001)|(p2<.001)


empty_sta=~with_sta_cells
with_sta_cells=( (p_values)&(with_sta_cells) ) 

#plt.hist(np.asarray(mean_var_ratio).flatten(), bins=55);
   

 #%%  Plot STAs
import scipy.stats
gsta_matrix=[]
goodstas=esta_all[with_sta_cells]
for ii in range(len(goodstas)):
    if  not(goodstas[ii]==None):
        if len(goodstas[ii][2])>1:
            stime=goodstas[ii][2]
            rsta=asarray(goodstas[ii][3].flatten())
            nsta=(rsta-rsta.min())
            gsta_matrix.append(rsta)
            

         
bsta_matrix=[]
bad_trl_sta=[]    
badstas=esta_all[~with_sta_cells]
for ii in range(len(badstas)):
    if  not(badstas[ii]==None):
        if len(badstas[ii][2])>1:
            stime=badstas[ii][2]
            rsta=asarray(badstas[ii][3].flatten())
            nsta=(rsta-rsta.min())
            bsta_matrix.append(rsta)




plt.figure(figsize=(10,18))
plt.subplot(121)
plt.ylabel('Unit #',fontsize=14)
plt.xlabel('Time (s)')

plt.imshow(scipy.stats.zscore(gsta_matrix, axis=1, ddof=0),aspect='auto', extent=[-1,1,1,len(gsta_matrix)])            
plt.subplot(122)

plt.imshow(scipy.stats.zscore(bsta_matrix, axis=1, ddof=0),aspect='auto',extent=[-1,1,1,len(bsta_matrix)])  
plt.xlabel('Time (s)')
plt.rcParams.update({'font.size': 14})

if SAVE_FIGS:
   plt.savefig('good_bad_sta_rd10.pdf', bbox_inches='tight')  
     #%% Plot PSDs
goodstas=esta_all[(~with_sta_cells) &(~empty_sta)]
ROI=[];
import matplotlib.pyplot as plt

STA_group='Bad_Sta'
for figs in range(len(goodstas)):
    esta_i=np.asarray(goodstas[figs][3].flatten())
  
    esta_time=np.asarray(goodstas[figs][2].flatten())
    freqs, psd = signal.welch(esta_i[:26],25, nperseg=50)
    norm_psd=psd/sum(psd);  
    
    spsd=norm_psd
    max_arg=[]
    for ps in range(len(freqs)):
        if sum(spsd)>=.5:
            max_arg.append(np.argmax(spsd))
            spsd=np.where(spsd==spsd[np.argmax(spsd)], 0, spsd) 
    max_psd=norm_psd[np.max(max_arg)]
    min_psd=norm_psd[np.min(max_arg)]    
    spsd=np.where(spsd==0, nan, spsd)     
    roi=freqs[np.min(max_arg)],freqs[np.max(max_arg)]
    mask= np.zeros(len(spsd), dtype=bool)
    ROI.append(roi)
    frq_mask=(freqs>=roi[0]) & (freqs<=roi[1])

    if SAVE_FIGS: 
        paths=STA_group+'_ '+str(figs)+'_ PSD.png'
      
        plt.figure(figsize=(10,4))
        plt.subplot(121)
        #
        plt.plot(esta_time,esta_i,linewidth=3)
        plt.title('Electrical STA')
        plt.xlabel('Time s')
        plt.ylabel('Amplitude(mv)')
        #from scipy import signal
        #fs=25
        plt.subplot(122)
    
    
        plt.vlines(freqs[np.max(max_arg)],min(norm_psd),norm_psd[np.max(max_arg)],color='k', linestyle='dashed')
        plt.vlines(freqs[np.min(max_arg)],min(norm_psd),norm_psd[np.min(max_arg)],color='k', linestyle='dashed')
        #plt.axhline(norm_psd[np.min(max_arg)],color='k', linestyle='dashed')
        #plt.hlines(norm_psd[np.max(max_arg)],freqs[np.min(max_arg)],freqs[np.max(max_arg)],color='k', linestyle='dashed')
        
        plt.plot(freqs, norm_psd,linewidth=3)
        #plt.plot(freqs, spsd,linewidth=2)
        plt.plot(freqs[frq_mask], norm_psd[frq_mask],linewidth=3,color='k')
        
        plt.ylim([0,max(norm_psd)+.01])
        plt.title('PSD: normalized power spectral density')
        plt.xlabel('Frequency Hz')
        plt.ylabel('Power')
        plt.tight_layout()
        plt.savefig(paths, bbox_inches='tight')   
        plt.show()
print((np.mean(ROI,axis=0)) )

  
  
#%%
     
Stimuli = {}
timeStampMatrices = {}
trg={}
for ix,(rf,tf) in enumerate(zip(report_filenames,trigger_filenames)):
    print("Reading file set %s: %s, %s" % (ix,rf,tf))
    Stimuli[ix], timeStampMatrices[ix] = read_stimuli_info(rf,tf)
    trg[ix] = loadmat(tf)
#timeStampMatrices[ix]=timeStampMatrices[ix]*50000
    
for ix in range(len(Stimuli)):    
    stim_ntrials = []
    for i,name in enumerate(Stimuli[ix]['Name']):
        nstim1 = Stimuli[ix]['Nstim1'][i]
        ntrials = 0.1
        
    
        if 'Fullfield' in name:
          
            ntrials = nstim1
        elif 'chirp2' in name:
            ntrials = nstim1
        elif 'color' in name:
            ntrials = nstim1
     #       
        elif 'movingbar' in name:
            ntrials = nstim1
        elif 'Bar' in name:
            ntrials = 5.0
        else:
            print("Unknown stimulus name: %s." % name)
            raise Exception
    
        stim_ntrials.append(int(ntrials))
    Stimuli[ix]['NTrials'] = stim_ntrials
stim_durs=np.array([4,12,4,4,4,4,4,4,4,4,12]) *Sampling   
SpikeTimes = {} # dictionary
for ix in ClusterIDs:
  SpikeTimes[ix] = []
  

for ix in ClusterIDs: 
    for cl in range(ncl[ix]):
        cl_spikes = np.where(ClusterIDs[ix]==cl+1)[0]
        cl_times  = np.unique(Times[ix][cl_spikes])
        SpikeTimes[ix].append(cl_times)
        #print(cl_spikes,cl_times)
    
print(SpikeTimes[0][0])

for key in SpikeTimes.keys():
    if SpikeTimes[key] ==[]:
       print(key)



STss=[] 
stims=[0,1] 
for stimid in stims:
    stim_trains_all= []

    stim_trains = []

    # 
    for ix in range(len(ClusterIDs)):
        STs = []
            #stimid=1
        # figure out how long each stimulus is
        n_trials    = Stimuli[ix]['NTrials'][stimid]
        stim_img_n  = Stimuli[ix]['Nstim1'][stimid] / n_trials
        stim_img_ms = Stimuli[ix]['Nrefresh'][stimid] * (1000/60)
        stim_dur    =stim_durs[stimid] #np.ceil(stim_img_ms * (Sampling/1000) * stim_img_n)
        if stimid==0:        
            stim_start_end=np.array(trg[ix].get('Fullfield')).flatten().reshape([n_trials,-1])*Sampling
            n_trials=60

        elif stimid==1:
            stim_start_end=np.array(trg[ix].get('color')).flatten().reshape([n_trials,-1])*Sampling
            n_trials=15    
        for cl in range(ncl[ix]):
          cl_trains = []
          # use pre-filtered cluster times, avoids doing it every time
          cl_times = SpikeTimes[ix][cl]
          for tx in range(n_trials):
            s0 = stim_start_end[tx,0]
            s1 = s0 + stim_dur
            trial_filter = np.where((cl_times >= s0) & (cl_times <= s1))[0]
            trial_times  = cl_times[trial_filter] - s0
            trial_times  = trial_times / (Sampling/1000)
            st = spk.SpikeTrain(trial_times, stim_dur/(Sampling/1000))
            cl_trains.append(st)
          stim_trains.append(cl_trains)
          stim_trains_all.append(cl_trains)
        STs.append(np.asarray(stim_trains))
    del STs
    STss.append(np.asarray(stim_trains_all))
    
Stimuli['SpikeTrains'] = STss   
ncl=len(stim_trains_all )
plt.figure(figsize=(3,2))
plot(spk.psth(Stimuli['SpikeTrains'][0][222],100).y)
     

#%% Combine two stimuli
sts_chirp = Stimuli['SpikeTrains'][0]#flash
sts_color = Stimuli['SpikeTrains'][1]#color 
st_ch_c=[]

trial_times=[]
trial_times  = np.asarray(trial_times) / (Sampling/1000)
st2 = spk.SpikeTrain(trial_times, stim_dur/(Sampling/1000))
for cll in range(ncl):
    ST2=[]
    for chc in range(15):# color data has 14 trials
        st2 = spk.SpikeTrain(trial_times, stim_dur/(Sampling/1000))
        if len(sts_chirp[cll][chc].spikes)+len(sts_color[cll][chc].spikes)>0:
            st2.spikes=np.hstack((sts_chirp[cll][chc+20].spikes,sts_color[cll][chc].spikes+4000))# for second dataset flash stimulus has no data in the first 20 truals(+20)  
            st2.t_end=sts_chirp[0][0].t_end+sts_color[0][1].t_end
            ST2.append(st2)
        
            
        else:
            trial_times=[]
            trial_times  = np.asarray(trial_times) / (Sampling/1000)
            st2 = spk.SpikeTrain(trial_times, stim_dur/(Sampling/1000))
            st2.t_end=sts_chirp[0][0].t_end+sts_color[0][1].t_end
            ST2.append(st2)            
    st_ch_c.append(ST2)

Stimuli['SpikeTrains'].append(np.asarray(st_ch_c))
from scipy.stats.stats import pearsonr


#%% function to remove low quality data- (removing outliers)
def Remove_outliers(stimuli):
    stimuli=Stimuli['SpikeTrains'][0]
    diffs=np.array([])
    for i,st in enumerate(stimuli):
        diff_cell=np.array([])
        for j,s in enumerate(st):
            diff_cell=np.append(diff_cell,np.diff(s)/1000)
        if len(diff_cell)>0:    
            diffs=np.append(diffs,np.median(diff_cell))
        else:
            diffs=np.append(diffs,0)   
        
    sums=np.array([])
    for i,st in enumerate(stimuli):
        mean_cell=np.array([])
        for j,s in enumerate(st):
            mean_cell=np.append(mean_cell,len(s))
        sums=np.append(sums,sum(mean_cell)/len(st))
           
        
    sum_zs=(sums[:]-np.mean(sums))/np.std(sums)
    diff_zs=(diffs[:]-np.mean(diffs))/np.std(diffs)   
    data_array_std = np.std(diffs)
    data_array_mean = np.mean(diffs)
    sigma_stdev = (2*data_array_std)+data_array_mean
    upper_limit = data_array_mean+data_array_std
    lower_limit = data_array_mean-data_array_std
    
    condition_diff = (diffs>0)& (diffs<upper_limit)&(diffs>0)
    condition_0ff_diff=~condition_diff
    
    data_array_std = np.std(sums)
    data_array_mean = np.mean(sums)
    sigma_stdev = (2*data_array_std)+data_array_mean
    upper_limit = data_array_mean+sigma_stdev
    lower_limit = data_array_mean-sigma_stdev
    
    condition_sums=(sums>0)& (sums<upper_limit)&(sums>10)
    condition_sums_off=~condition_sums
    return condition_sums,condition_diff

#%% function2 to remove low quality data- this uses pearson correlation between stimulus and response(we do not use it for rd10 data)
def pearsonr_score(stimuli):
    stimuli=Stimuli['SpikeTrains'][0]
    
    b1 = np.full(1,0)
    b2 = np.ones(19)
    b4 =np.ones(1)*0    
    b3 = np.ones(19)*0
    org_signal_interval = np.array([*b1,*b2,*b3,*b4])    
    PSTH = np.empty((len(stimuli),40))
    pearson_corr=np.empty((len(stimuli)))
    
    for i in range(len(stimuli)):
        PSTH[i,:]=spk.psth(Stimuli['SpikeTrains'][0][i],100).y
        pearson_corr[i] = pearsonr(PSTH[i,:],org_signal_interval)[0]
 #       plot(pearson_corr)   
    return pearson_corr

#%% compute variance ratio to remove low quality data
  
cond_sum,cond_diff=Remove_outliers(Stimuli)
#pearson_corr=pearsonr_score(Stimuli)
valid_units = np.ones(ncl, dtype=bool)
print("Valid units: %d" %np.sum(valid_units))

    
def psth_trl(spike_trains, bin_size):
    bin_count = int((spike_trains.t_end - spike_trains.t_start) /
                    bin_size)
    bins = np.linspace(spike_trains.t_start, spike_trains.t_end,
                       bin_count+1)


    combined_spike_train = spike_trains.spikes
    vals, edges = np.histogram(combined_spike_train, bins, density=False)
    #bin_size = edges[1]-edges[0]
    return 1000*(vals/bin_size)#PieceWiseConstFunc(edges, vals) 

empty_trials = {}
# spike count in each full field trial
empty_trials[0] = np.asarray([np.median([len(s) for s in st])<MIN_SPIKES_FF for st in Stimuli['SpikeTrains'][0]])
# spike count in each chirp trial
empty_trials[1] = np.asarray([np.median([len(s) for s in st])<MIN_SPIKES_CHIRP for st in Stimuli['SpikeTrains'][1]])
#empty_trials[1]=empty_trials[0] 

ff=[]
FF=np.empty(ncl)
ffs=[]
var_idx = np.empty(ncl)

for cel in range(ncl):# CELL NUMBER
    st=Stimuli['SpikeTrains'][0][cel]
    psthtrl=[]
    for s in range(len(st)):# TRIAL NUMBER
                #ffs.append(np.asarray(st.flatten()[s]))
        ff=np.concatenate((ff,np.asarray(st.flatten()[s])),axis=0)
        if len(st[s])>0:
            psthtrl.append(psth_trl(st[s],225))

    
    var_idx[cel]=mean(np.var(psthtrl,axis=0,ddof=1))/var(psthtrl)
    FF[cel]=nanmean(np.var(psthtrl,axis=0,ddof=1)/np.mean(psthtrl,axis=0))

    del psthtrl

good_cells=(var_idx<.9988)#&( var_idx>0.6)


good_cellsts_idx = np.where(((~empty_trials[1]&(~empty_trials[0]))&(good_cells)))[0][:]
bad_cells_idx = np.where(((~good_cells)|(empty_trials[1])|(empty_trials[0])))[0][:]
good_cells_idx = np.where(((~empty_trials[1]&(~empty_trials[0]))&(good_cells)))[0][:]

#%% plot spike raster
#plt.figure(figsize=(13,22))
#ntrials =10
#for i,e in enumerate(good_cells_idx):
#    for ii,st in enumerate(Stimuli['SpikeTrains'][0][e][:]):
#        plt.plot(st, np.ones(len(st))+ii+i*ntrials,'k|',ms=2, lw=4)
##    plt.plot((0,12000),((i+1)*ntrials+0.5,(i+1)*ntrials+0.5),'grey')
#plt.title('Valid units')

#plt.figure(figsize=(12,22))
#ntrials =10
#for i,e in enumerate(bad_cells_idx):
#    for ii,st in enumerate(Stimuli['SpikeTrains'][1][e][:]):
#        plt.plot(st, np.ones(len(st))+ii+i*ntrials,'k|',ms=2, lw=4)
#    plt.plot((0,12000),((i+1)*ntrials+0.5,(i+1)*ntrials+0.5),'grey')
#plt.title('inValid units')      
# exclude units with insufficient spike counts (per trial)

#conditions = (~np.asarray(empty_trials[1]))*valid_units*good_cells
#conditions =(((~empty_trials[0])&(~empty_trials[0]))&(with_sta_cells))
conditions =(((~empty_trials[0]))&(with_sta_cells))

print("Valid units remaining: %d" %np.sum(conditions))


#%% plot PSTH
valids=np.where(conditions)
celss=zip(*valids)
PSTH = np.empty((size(valids),160))
plt.figure(figsize=(15,10))

for i,ii in enumerate(celss):
#    plot(spk.psth(Stimuli['SpikeTrains'][1][ii],100).y)
    PSTH[i,:]=spk.psth(Stimuli['SpikeTrains'][2][ii],100).y
PSTH_norm = PSTH/np.max(PSTH, axis=1).reshape(-1,1)

plt.figure(figsize=(15,10))
plt.subplot(221)
plt.imshow(PSTH_norm, aspect='auto')
valids=np.where(~conditions)
celss=zip(*valids)
PSTH = np.empty((size(valids),160))

for i,ii in enumerate(celss):
#    plot(spk.psth(Stimuli['SpikeTrains'][1][ii],100).y)
    PSTH[i,:]=spk.psth(Stimuli['SpikeTrains'][2][ii],100).y
PSTH_norm = PSTH/np.max(PSTH, axis=1).reshape(-1,1)

plt.subplot(222)
plt.imshow(PSTH_norm[np.argsort(np.mean(PSTH_norm,axis=1))], aspect='auto')
#%%
# example rasters of filtered units
#istim = 0 # , 1 for chirp
#plt.figure(figsize=(10,75))
#empty_ones = np.where(((~empty_trials[1])&(good_cells)))[0][:]
#ntrials =10
#for i,e in enumerate(empty_ones):
#    for ii,st in enumerate(Stimuli['SpikeTrains'][0][e][:]):
#        plt.plot(st, np.ones(len(st))+ii+i*ntrials,'k|',ms=2, lw=4)
##    plt.plot((0,4000),((i+1)*ntrials+0.5,(i+1)*ntrials+0.5),'grey')
#plt.title('Valid units')
#plt.savefig('Chirp_raster.png', bbox_inches='tight')
#
#plt.figure(figsize=(10,55))
#empty_ones = np.where((~((~empty_trials[1]))))[0][:20]
#ntrials = Stimuli['SpikeTrains'][istim][0].shape[0]
#
#
#for i,e in enumerate(empty_ones):
#    for ii,st in enumerate(Stimuli['SpikeTrains'][istim][e][:]):
#        plt.plot(st, np.ones(len(st))+ii+i*ntrials,'k|',ms=2, lw=4)
#    plt.plot((0,4000),((i+1)*ntrials+0.5,(i+1)*ntrials+0.5),'grey')
#plt.title('Invalid units')

## exclude units at borders
#noborder = (ClusterLoc[0]>1) & (ClusterLoc[0]<62)
#conditions = noborder[0]*noborder[1]*conditions
#print("Valid units remaining: %d" %np.sum(conditions))
#
#
#STAs = h5py.File(data_path+'P91_05_07_17_swn_stim2_ctl_clustered_sta.hdf5','r')
#insta = np.isin(STAs['units'],np.where(conditions)[0])
#inboth = np.isin(np.where(conditions)[0],STAs['units'])
#if FILTER_STA:
#    conditions[np.where(conditions)[0][~inboth]]=False
#print("Valid units remaining: %d" %np.sum(conditions))
#
#%% compute ISI metrics
# select full field and chirp
sel_stims = [0,1,2]

def flat_sts_for_dy(st):
    flat = []
    for i in range(st.shape[0]):
      for j in range(i+1,st.shape[0]):
        flat.append(st[[i,j],:].flatten())
    return flat

    # For the _fullfield_ and _chirp_ stimuli only.


def sts_trial_pairs_for_dy(st):
    flat_pairs = []
    for i in range(st.shape[0]):
        for j in range(i+1,st.shape[0]):
            flat_pairs.append((st[i,:],st[j,:]))
    return flat_pairs

def compute_SPIKE_on_flat_pair(pair):
    sti = pair[0]
    stj = pair[1]
    assert sti.shape[0] == stj.shape[0]
    ds = []
    for i in range(sti.shape[0]):
        for j in range(i+1,sti.shape[0]):
            ds.append(spk.spike_distance([sti[i], stj[j]]))
    return np.average(ds)

def compute_ISI_on_flat_pair(pair):
    sti = pair[0]
    stj = pair[1]
    assert sti.shape[0] == stj.shape[0]
    ds = []
    for i in range(sti.shape[0]):
        for j in range(i+1,sti.shape[0]):
            ds.append(spk.isi_distance([sti[i], stj[j]]))
    return np.average(ds)

def spikeRates(st_s):
    sr = []
    func_c = lambda s: np.count_nonzero(s.spikes)
    for st in st_s:
        cs = [c for c in map(func_c, st)]
        hzs = np.divide(cs,(st[0].t_end-st[0].t_start)/1000)
        sr.append( np.average(hzs) )
    return np.asarray(sr)

if LOAD_STORED_DISTANCES == False:

    SPIKE_dist_ys = []
    ISI_dist_ys   = []

    for stimid in sel_stims:
        print("Computing ISI and SPIKE distance matrix for stimid rd10_neworder_before): %d" % stimid)

        sts = Stimuli['SpikeTrains'][stimid][conditions]
        flat_sts = sts_trial_pairs_for_dy(sts)
        del sts

        SPIKE_dy = joblib.Parallel(n_jobs=-1,verbose=1)(joblib.delayed(compute_SPIKE_on_flat_pair)(st) for st in flat_sts)
        print(np.asarray(SPIKE_dy).shape)
        ISI_dy   = joblib.Parallel(n_jobs=-1,verbose=1)(joblib.delayed(compute_ISI_on_flat_pair)(st) for st in flat_sts)
        print(np.asarray(ISI_dy).shape)

        print("ISI and SPIKE complete for stimid rd10_neworder_before: %d" % stimid)

        assert(distance.is_valid_y(SPIKE_dy))
        assert(distance.is_valid_y(ISI_dy))

        SPIKE_dist_ys.append(SPIKE_dy)
        ISI_dist_ys.append(ISI_dy)

        del SPIKE_dy
        del ISI_dy

    SPIKE_dist_ys = np.asarray(SPIKE_dist_ys)
    ISI_dist_ys   = np.asarray(ISI_dist_ys)

    print(SPIKE_dist_ys.shape)
    print(ISI_dist_ys.shape)
    
    np.save('SPIKE_dist_ys_rd10_test',SPIKE_dist_ys)
    np.save('ISI_dist_ys_rd10_test',ISI_dist_ys)
else:
    SPIKE_dist_ys = np.load('SPIKE_dist_ys_rd10_test.npy')
    ISI_dist_ys   = np.load('ISI_dist_ys_rd10_test.npy')
    

#%% compure Bias index
OOi = np.zeros(ncl)
for cl in range(ncl):
    # FF is 4000 ms, take PSTH by spliting time into two parts
    r = spk.psth(Stimuli['SpikeTrains'][0][cl],2000).y
    oo = r[[0,1]]
    OOi[cl] = (oo[0]-oo[1])/(oo[0]+oo[1])
# fix NaNs to 0.0
OOi[np.where(np.isnan(OOi))] = 0.0
conditions_all = np.copy(conditions)

def get_tri_sq(m):
    return m[np.tril_indices(int(np.sqrt(2*m.shape[0]+1/4)+1/2),-1)]

ISI_dist_ys_valid = {}
SPIKE_dist_ys_valid = {}
for i in range(3):
    ISI_dist_ys_valid[i] = np.copy(ISI_dist_ys[i])
    SPIKE_dist_ys_valid[i] =  np.copy(SPIKE_dist_ys[i])

    invalid_sta=np.array([])
    bad_inds = np.isin(np.where(conditions)[0], invalid_sta)

    mask = np.ones(squareform(ISI_dist_ys_valid[i]).shape, dtype=bool)
    mask[bad_inds,:] = 0
    mask[:,bad_inds] = 0
    n_remain = mask.shape[0]-np.sum(bad_inds)
    new_distances = squareform(ISI_dist_ys_valid[i])[mask].reshape((n_remain,n_remain))
    ISI_dist_ys_valid[i] = new_distances[np.triu_indices_from(new_distances,1)]
    new_distances = squareform(SPIKE_dist_ys_valid[i])[mask].reshape((n_remain,n_remain))
    SPIKE_dist_ys_valid[i] = new_distances[np.triu_indices_from(new_distances,1)]



plt.figure()
sns.distplot(OOi, label='all')
sns.distplot(OOi[conditions_all], label='valid')
plt.xlabel('Bias index')
plt.legend()

if SAVE_FIGS:
    plt.savefig('Bias index_rd10.pdf', bbox_inches='tight')

#%% find optimum cluster number 
# obtain Gap statistic
tss = np.arange(0.3,3,0.01) # threshold values to test
gaps = np.empty((3,2,tss.shape[0]))
NCs_gap = np.empty((3,2,tss.shape[0]))

ncls = np.arange(3,61,1)
metric_scores = np.empty((3,4,len(ncls)))
links_ward_ISI   = []
links_ward_SPIKE = []
mk_l = lambda dy: cluster.hierarchy.linkage(dy, method='ward')
for i in range(3):
    links_ward_ISI.append(mk_l(ISI_dist_ys_valid[i]))
    links_ward_SPIKE.append(mk_l(SPIKE_dist_ys_valid[i]))

for s in (0,1,2):
    for i_d,d in enumerate((ISI_dist_ys_valid[s],SPIKE_dist_ys_valid[s])):
        Nc, Wk, Nc_shuff, Wk_shuff, Dk, Dk_shuff, ts = eval_gap_scores(d,tss)
        gaps[s,i_d,:] = np.log(Wk_shuff)-np.log(Wk)
        NCs_gap[s,i_d,:] = Nc
        
    isidm = distance.squareform(ISI_dist_ys_valid[s])
    spkdm = distance.squareform(SPIKE_dist_ys_valid[s])
    for i,t in enumerate(ncls):
        fcls_isi = cluster.hierarchy.fcluster(links_ward_ISI[s], t=t, criterion='maxclust')
        fcls_spk = cluster.hierarchy.fcluster(links_ward_SPIKE[s], t=t, criterion='maxclust')
        metric_scores[s,0,i] = metrics.adjusted_mutual_info_score(fcls_isi,fcls_spk)
        metric_scores[s,1,i] = metrics.completeness_score(fcls_isi,fcls_spk)
        metric_scores[s,2,i] = metrics.adjusted_rand_score(fcls_isi,fcls_spk)  
    
for i,t in enumerate(ncls):
    fcls_0 = cluster.hierarchy.fcluster(links_ward_ISI[0], t=t, criterion='maxclust')
    fcls_1 = cluster.hierarchy.fcluster(links_ward_ISI[1], t=t, criterion='maxclust')
    metric_scores[0,3,i] = metrics.adjusted_mutual_info_score(fcls_0,fcls_1)
    fcls_0 = cluster.hierarchy.fcluster(links_ward_SPIKE[0], t=t, criterion='maxclust')
    fcls_1 = cluster.hierarchy.fcluster(links_ward_SPIKE[1], t=t, criterion='maxclust')
    metric_scores[1,3,i] = metrics.adjusted_mutual_info_score(fcls_0,fcls_1)
    fcls_0 = cluster.hierarchy.fcluster(links_ward_SPIKE[0], t=t, criterion='maxclust')
    fcls_1 = cluster.hierarchy.fcluster(links_ward_SPIKE[2], t=t, criterion='maxclust')
    metric_scores[2,3,i] = metrics.adjusted_mutual_info_score(fcls_0,fcls_1)
    

plt.rcParams.update({'font.size': 11})
plt.figure(figsize=(12,4))
ax = plt.subplot(121)
s_labels = ('Flash','Color','Flash & color')
d_labels = ('ISI distance','SPIKE distance','SPIKE distance 2')
with plt.rc_context(rcParams):
    for s in (0,1,2):
        for d in (0,1):
            p = plt.plot(NCs_gap[s,d,:],gaps[s,d,:], label=s_labels[s]+'; '+d_labels[d])
            print(s_labels[s]+' '+d_labels[d]+' gap stat peak at '+str(NCs_gap[s,d,np.argmax(gaps[s,d])])+' clusters')
            plt.vlines(NCs_gap[s,d,np.argmax(gaps[s,d])],0,gaps[s,d,np.argmax(gaps[s,d])],linestyles='--',colors=p[0].get_c())
plt.xlim((0,40))
plt.ylim((0,0.7))
plt.legend(frameon=False,loc = 'upper right')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.xlabel('Number of clusters')
plt.ylabel('Gap statistic');

ax = plt.subplot(122)
m = 0# use mutual info
with plt.rc_context(rcParams):
    for s in (0,1,2):
        p = plt.plot(ncls,metric_scores[s,m,:], label=s_labels[s])
        print(s_labels[s]+' mi score peak at '+str(ncls[np.argmax(metric_scores[s,m,:])])+' clusters')
        plt.vlines(ncls[np.argmax(metric_scores[s,m,:])],0,metric_scores[s,m,np.argmax(metric_scores[s,m,:])],linestyles='--',colors=p[0].get_c())
#    for s in (0,1,2):
#        p = plt.plot(ncls,metric_scores[s,3,:], label=d_labels[s])
#        print(d_labels[s]+' mi score peak at '+str(ncls[np.argmax(metric_scores[s,m,:])])+' clusters')
#        plt.vlines(ncls[np.argmax(metric_scores[s,3,:])],0,metric_scores[s,3,np.argmax(metric_scores[s,3,:])],linestyles='--',colors=p[0].get_c())
plt.xlim((0,60))
#plt.ylim((0,0.7))
plt.legend(frameon=False,loc = 'lower right')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.xlabel('Number of clusters')
plt.ylabel('Adjusted mutual information');

t_best_ff = ncls[np.argmax(metric_scores[0,m,:])]
t_best_chirp = ncls[np.argmax(metric_scores[1,m,:])]
t_best_ff_chirp_color = ncls[np.argmax(metric_scores[2,m,:])]


if SAVE_FIGS:
    plt.savefig('clusters_comparison_rd10.pdf', bbox_inches='tight')    


  
#%%Compurte distance matrix
stim = 0# here we select the stimulus 0is flash, 1 is color, 2 is combination of boath
#st_name =  Stimuli[stim]['Name'][stim]
st_name='flash'
t =t_best_ff
fcls = []
fcls.append(cluster.hierarchy.fcluster(links_ward_ISI[stim], t=t, criterion='maxclust'))
fcls.append(cluster.hierarchy.fcluster(links_ward_SPIKE[stim], t=t, criterion='maxclust'))

cnf_matrix = confusion_matrix(fcls[0], fcls[1], labels=np.arange(1,t+1))
normed_cnf = cnf_matrix.astype('float') / cnf_matrix.sum(axis=1)[:, np.newaxis]

with plt.rc_context(rcParams):
    plt.figure(figsize=(3,3))
    plt.imshow(normed_cnf[np.argmax(normed_cnf,axis=0),:],origin='lower')
    plt.axis('equal')
    cb = plt.colorbar()
    cb.set_label('Cluster overlap');
    plt.xlabel('ISI clusters')
    plt.ylabel('SPIKE clusters')
 #   plt.xticks((0,10,20))
#    plt.yticks((0,10,20))
    
if SAVE_FIGS:
    plt.savefig('clusters_MI_rd10_neworder_before'+st_name+'.pdf', bbox_inches='tight')    



def seriation(Z,N,cur_index):
    if cur_index < N:
        return [cur_index]
    else:
        left = int(Z[cur_index-N,0])
        right = int(Z[cur_index-N,1])
        return (seriation(Z,N,left) + seriation(Z,N,right))
    
def compute_serial_matrix(dist_mat,method="ward"):
    sq_dist_mat = squareform(dist_mat)
    N = sq_dist_mat.shape[0]
    res_linkage = cluster.hierarchy.linkage(dist_mat, method=method)
    #linkage(flat_dist_mat, method=method,preserve_input=True)
    res_order = seriation(res_linkage, N, N + N-2)
    seriated_dist = np.zeros((N,N))
    a,b = np.triu_indices(N,k=1)
    seriated_dist[a,b] = sq_dist_mat[ [res_order[i] for i in a], [res_order[j] for j in b]]
    seriated_dist[b,a] = seriated_dist[a,b]
    
    return seriated_dist, res_order, res_linkage

sorted_normed_cnf, res_order, res_linkage = compute_serial_matrix(SPIKE_dist_ys_valid[stim],method='ward')
with plt.rc_context(rcParams):
    plt.figure(figsize=(3,3))
    plt.imshow(sorted_normed_cnf, cmap=plt.cm.CMRmap, origin='lower')
    cb = plt.colorbar()
    cb.set_label('SPIKE distance')
    plt.axis('equal')
#    plt.xticks((0,40,00))
#    plt.yticks((0,40,80))
    
if SAVE_FIGS:
    plt.savefig('clusters_distance_matrix_clustered_SPIKE_rd10_neworder_before'+st_name+'.pdf', bbox_inches='tight')    
    




#%%

new_distances=SPIKE_dist_ys_valid[stim]
#new_distances=ISI_dist_ys_valid[1]
l = cluster.hierarchy.linkage(new_distances, method='ward')
fcls = cluster.hierarchy.fcluster(l, t=t, criterion='maxclust')
n_flat_clusters = np.unique(fcls).shape[0]

print("Distance %.2f\nNumber of (flat) clusters rd10_neworder_before: %d" % (t,n_flat_clusters))
silhouettes = metrics.silhouette_samples(distance.squareform(new_distances),fcls,metric='precomputed')
print("Mean Silhouette Coefficient rd10_neworder_before: %.2f" % np.average(silhouettes))
Cells_names_and_clusters=list(zip(Cell_names[conditions_all],fcls))
### plot dendrogram

plt.figure(figsize=(16,3))

## set things up for coloured dendrogram
n = 41
pal = sns.diverging_palette(180,359,sep=1,n=n)
OOi_cspace = np.linspace(-1,1,n)
OOi_c_func = lambda i: pal[np.searchsorted(OOi_cspace,OOi[conditions_all][i])]
DSi_cspace = np.linspace(0,1,n)
DSi_c_func = lambda i: pal[np.searchsorted(DSi_cspace,DSi[conditions_all][i,0])]

def create_colors_for_linkage(Z,data_len,base_col_func):
    colors = []
    for i1,i2,d,c in Z:
        if i1 >= data_len:
            c1 = colors[int(i1)-data_len]
        else:
            c1 = base_col_func(int(i1))
            
        if i2 >= data_len:
            c2 = colors[int(i2)-data_len]
        else:
            c2 = base_col_func(int(i2))
        new_c = sns.blend_palette([c1,c2],n_colors=3).as_hex()[1]
        colors.append(new_c)
    return colors

cs = create_colors_for_linkage(l,l.shape[0]+1,OOi_c_func)

# calculate labels
n = n_flat_clusters
T = np.unique(fcls)
#labels=list('' for i in range(20*n))
labels=list('' for i in range(len(l)+1))
for i in range(n):
    labels[i]=str(i)+ ',' + str(T[i])

with plt.rc_context({'lines.linewidth': 2, 'font.size':10}):
    dend = cluster.hierarchy.dendrogram(l, p=n, no_labels=False, leaf_font_size=10, color_threshold=t, 
                                        distance_sort='ascending', link_color_func=lambda k: cs[k-l.shape[0]-1], 
                                        truncate_mode='lastp', labels = labels, show_leaf_counts=True)

if SAVE_FIGS:
    plt.savefig('clustered_dendrogram rd10_neworder_before'+st_name+'.pdf', bbox_inches='tight')    

from scipy.interpolate import make_interp_spline
import matplotlib.gridspec as gridspec
      
        
#%% before blocker
from scipy import signal
from spk_trains_maker import spk_trains_maker# this includes three functions "spk_trains_maker","plot_clustrs", and "esta_clustering".
from spk_trains_maker import plot_clustrs
data_path = "C:/Users/Admin/Desktop/hennig_project/download/rgcclassification/sample_dara_hamed/"

filenames=['2020_02_07_rd10_l1_before.mat','2020_02_07_rd10_r1_before.mat','2020_02_05_rd10_l1_before.mat','2020_02_05_rd10_r1_before.mat']

report_filenames  = [ data_path+"2020_02_07_rd10_l1_before_report.txt",
#                     data_path+"2020_02_07_rd10_l2_report.txt",## this recording is without drug
                     data_path+"2020_02_07_rd10_r1_before_report.txt",
                     data_path+"2020_02_05_rd10_l1_before_report.txt",
                     data_path+"2020_02_05_rd10_r1_before_report.txt"]
                     


trigger_filenames = [   data_path+"2020_02_07_rd10_l1_before_trigger.mat",
#                        data_path+"2020_02_07_rd10_l2_trigger.mat",
                        data_path+"2020_02_07_rd10_r1_before_trigger.mat",
                        data_path+"2020_02_05_rd10_l1_before_trigger.mat",
                        data_path+"2020_02_05_rd10_r1_before_trigger.mat"]
stims=[0,1]

spk_data_before, esta_all_rd_before, Cell_names=spk_trains_maker(filenames,report_filenames,trigger_filenames,stims)
plot_stims=[0,1]


psd_all_before=[]
for i in range(len(esta_all_rd_before)):
    freqsl_b, psd_b = signal.welch(esta_all_rd_before[i][3].flatten(),25, nperseg=25)
    
#    psd_all[i]=np.hstack((psd_all,freqs))
    psd_all_before.append(psd_b)
psd_all_before=np.asarray(psd_all_before)



plot_clustrs(spk_data_before,silhouettes,fcls,l,t,cs,OOi,conditions_all,esta_all,Cell_names,plot_stims,'rd10_Before')

Cells_names_and_clusters_before=list(zip(Cell_names[conditions_all],fcls))
with open("clusetr_numbers_rd_before.txt", 'w') as output:
    for row in Cells_names_and_clusters_before:
        output.write(str(row) + '\n')          
#%% after blocker
filenames=['2020_02_07_rd10_l1_after.mat','2020_02_07_rd10_r1_after.mat','2020_02_05_rd10_l1_after.mat','2020_02_05_rd10_r1_after.mat']
report_filenames  = [data_path+"2020_02_07_rd10_l1_after_report.txt",
                     data_path+"2020_02_07_rd10_r1_after_report.txt",
                     data_path+"2020_02_05_rd10_l1_after_report.txt",
                     data_path+"2020_02_05_rd10_r1_after_report.txt"]
                     


trigger_filenames = [data_path+"2020_02_07_rd10_l1_after_trigger.mat",
                     data_path+"2020_02_07_rd10_r1_after_trigger.mat",
                     data_path+"2020_02_05_rd10_l1_after_trigger.mat",
                     data_path+"2020_02_05_rd10_r1_after_trigger.mat"]
stims=[0]
spk_data_after, esta_all_rd_after, Cell_names_rd_after=spk_trains_maker(filenames,report_filenames,trigger_filenames,stims)
plot_stims=[0]

psd_all_after=[]
for i in range(len(esta_all_rd_before)):
    freqsl_a, psd_a = signal.welch(esta_all_rd_after[i][3].flatten(),25, nperseg=25)
#    psd_all[i]=np.hstack((psd_all,freqs))
    psd_all_after.append(psd_a)

psd_all_after=np.asarray(psd_all_after)
plot_clustrs(spk_data_after,silhouettes,fcls,l,t,cs,OOi,conditions_all,esta_all_rd_after,Cell_names_rd_after,plot_stims,'rd10_After')

Cells_names_and_clusters_after=list(zip(Cell_names_rd_after[conditions_all],fcls))
with open("clusetr_numbers_rd_after.txt", 'w') as output:
    for row in Cells_names_and_clusters_after:
        output.write(str(row) + '\n')  

#%%tsne_

psths = [] 
for sts in Stimuli['SpikeTrains'][2][conditions_all]:
    xs,ys = getPSTHs((sts,),bs=50)
    psths.append(ys[0])
psths = np.array(psths)    
from sklearn.manifold import TSNE
from sklearn.preprocessing import normalize
from sklearn.preprocessing import robust_scale
from matplotlib.colors import ListedColormap
plt.figure(figsize=(24,15))
psths_norm = psths/np.max(psths, axis=1).reshape(-1,1)
plt.imshow(psths_norm)
plt.imshow(psths[60:80])

#t_ = t_best_chirp
#new_distances_ = SPIKE_dist_ys_valid[1]
#l_ = cluster.hierarchy.linkage(new_distances_, method='ward')
#fcls_ = cluster.hierarchy.fcluster(l_, t=t_, criterion='maxclust')
n_flat_clusters_ = np.unique(fcls).shape[0]
show_order = np.unique(fcls)[::-1]-1

model = TSNE(n_components=2, random_state=0, perplexity=30)#,init='pca')
proj = model.fit_transform(psths) 

with plt.rc_context(rcParams):
    plt.figure(figsize=(14,5))
    ax = plt.subplot(121)
    # ax.set_facecolor((0.3,0.3,0.3))
    s = plt.scatter(proj[:,0],proj[:,1],s=16,lw=0,c=show_order[fcls-1],
                    cmap=ListedColormap(sns.hls_palette(n_flat_clusters_,l=0.6,s=0.6).as_hex()))
    cb = plt.colorbar(s)
    cb.set_label('Cluster')
    # plt.axis('equal')
    plt.grid(False)
    ax = plt.subplot(122)
    # ax.set_facecolor((0.3,0.3,0.3))
    p = plt.scatter(proj[:,0],proj[:,1],s=16,lw=0,c=np.array(((OOi[conditions_all]))),
                    cmap=sns.diverging_palette(180,359,sep=1,n=32,as_cmap=True))
    cb = plt.colorbar(p)
    cb.set_label('Bias index')
    # plt.axis('equal')
    plt.grid(False)

if SAVE_FIGS:
    plt.savefig('clusters_tsne_rd10_neworder_before'+st_name+'.pdf', bbox_inches='tight')
#
    
    
#%%ESTA clustering
  
stas_3=np.asarray([row[3][:25].flatten() for row in esta_all[conditions_all]])

zssta=[(row-mean(row))/std(row,ddof=0).flatten() for row in stas_3]


import sklearn.metrics

zssta_dstance=sklearn.metrics.pairwise_distances(zssta, Y=None, metric='euclidean')
zssta_dstance_flat=zssta_dstance[np.triu_indices(len(zssta), k = 1)]
zssta_dstance_flat=zssta_dstance_flat/zssta_dstance_flat.max()
plt.imshow(squareform(zssta_dstance_flat), interpolation='nearest', cmap=plt.cm.gnuplot2,
               vmin=0)
Nc, Wk, Nc_shuff, Wk_shuff, Dk, Dk_shuff, ts = eval_gap_scores(zssta_dstance_flat,tss) # threshold values to test

gapss = np.log(Wk_shuff)-np.log(Wk)
NCs_gaps = Nc
with plt.rc_context({'lines.linewidth': 2, 'font.size':12}):

    p = plt.plot(NCs_gaps,gapss)
    
    plt.vlines(NCs_gaps[np.argmax(gapss)],0,gapss[np.argmax(gapss)],linestyles='--',colors=p[0].get_c())
    plt.xlim((0,40))
    plt.ylim((0,1.1))
    plt.legend(frameon=False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xlabel('Number of clusters')
    plt.ylabel('Gap statistic');
if SAVE_FIGS:
    plt.savefig('Gap statistic_rd10_'+st_name+'.pdf', bbox_inches='tight')
#
cluster_number=NCs_gaps[np.argmax(gapss)]


sorted_normed_cnf, res_order, res_linkage = compute_serial_matrix(zssta_dstance_flat,method='ward')
with plt.rc_context(rcParams):
    plt.figure(figsize=(10,10))
    plt.imshow(sorted_normed_cnf, cmap=plt.cm.CMRmap, origin='lower')
    cb = plt.colorbar()
    cb.set_label('euclidean distance')
    plt.axis('equal')

from scipy.spatial.distance import pdist

l = cluster.hierarchy.linkage(zssta, "ward")
#cluster.hierarchy.dendrogram(l);
t=cluster_number
#l = cluster.hierarchy.linkage(zssta, method='average')
#fcls = cluster.hierarchy.fcluster(l, t=9.70909, criterion='distance')
fcls_sta = cluster.hierarchy.fcluster(l, t=t, criterion='maxclust')
#kmeans = KMeans(n_clusters=20, random_state=0).fit(zssta)
#fcls=kmeans.labels_
fig = plt.figure(figsize=(15,15))
ax = fig.add_axes([0.1, 0.1, 0.8, 0.8]) # main axes

ax.imshow(zssta_dstance[np.argsort(fcls_sta)], cmap=plt.cm.CMRmap, origin='lower')
ax.set_xticks(np.arange(len(zssta_dstance)))
ax.set_yticks(np.arange(len(zssta_dstance)))
ax.set_xticklabels(fcls_sta[np.argsort(fcls_sta)])
ax.set_yticklabels(fcls_sta[np.argsort(fcls_sta)])
plt.show

plt.xticks(fcls_sta[np.argsort(fcls_sta)])
#fcls = cluster.hierarchy.fcluster(l, 1.80, depth=10)
n = 41
pal = sns.diverging_palette(180,359,sep=1,n=n)
OOi_cspace = np.linspace(-1,1,n)
OOi_c_func = lambda i: pal[np.searchsorted(OOi_cspace,OOi[conditions_all][i])]
DSi_cspace = np.linspace(0,1,n)
DSi_c_func = lambda i: pal[np.searchsorted(DSi_cspace,DSi[conditions_all][i,0])]

cs = create_colors_for_linkage(l,l.shape[0]+1,OOi_c_func)

c, coph_dists = cluster.hierarchy.cophenet(l, pdist(zssta))
c
silhouettes = metrics.silhouette_samples(distance.squareform(pdist(zssta)),fcls_sta,metric='precomputed')
print("Mean Silhouette Coefficient: %.2f" % np.average(silhouettes))

n_flat_clusters = np.unique(fcls_sta).shape[0]
n = n_flat_clusters
T = np.unique(fcls_sta)
labels=list('' for i in range(20*n))
for i in range(n):
    labels[i]=str(i)+ ',' + str(T[i])
show_order_sta = np.unique(fcls_sta)[::-1]-1
max_num_clusters = np.unique(fcls_sta).shape[0]

palette = sns.hls_palette(max_num_clusters,l=0.6,s=0.6)    

max_num_clustersx=t

psd_all=np.asarray(psd_all)
# plt.figure(figsize=(9,max_num_clustersx*1.7/4.8))
plt.figure(figsize=(14,max_num_clustersx*1))
# plt.figure(figsize=(9,max_num_clustersx*1.7/4.8))

plot_stims = [0,1]

fs = 12#24

labels=list('' for i in range(n))
for i in range(n):
    labels[i] = '#' + str(T[i]) + '\n(' + str(np.count_nonzero(np.where(fcls_sta==T[i]))) + ')'
    
# plot_widths = [1.2,0.8,3,0.4,0.4, 0.4, 0.4]
plot_widths = [2,2.8,1.3,7.5,2.3,.7, 0.6]

gs = gridspec.GridSpec(max_num_clustersx, 7, width_ratios = plot_widths, wspace=0.1, hspace=0.1)

bins = 20 # ms

cids = np.where(conditions_all)[0]
has_sta = np.zeros_like(conditions_all).astype(dtype=bool)
#has_sta[STAs['units'].value] = True
sta_inds = np.zeros(np.sum(conditions_all), dtype(int))
#sta_inds[has_sta[with_sta_cells]] = np.where(np.isin(STAs['units'].value, np.where(with_sta_cells&has_sta)[0]))[0]
has_sta = has_sta[conditions_all]
#mean_rf_size = np.median((np.abs(STAs['fits'][has_sta,3]),np.abs(STAs['fits'][has_sta,3])))
mean_rf_size=np.zeros(np.sum(conditions_all), dtype(int))
ylims = [(0,40),(0,10)]
    
# for i, c in enumerate(show_order_sta):

#     n_units = np.where(fcls_sta == c+1)[0].shape[0]
#     for ci, stimid in enumerate(plot_stims):
#         sts = Stimuli['SpikeTrains'][stimid][conditions_all][np.where(fcls_sta == c+1)]
#         if stimid == 0:
#             txt = "Cluster %d (%d units)" % (c+1,n_units)
#         elif stimid == 1:
#             t_sils = silhouettes[np.where(fcls_sta == c+1)]
#             t_ooi  = OOi[conditions_all][np.where(fcls_sta == c+1)]
#             txt = "Avg. OOi: %.2f±%.2f    Avg. Silhouette Coeff.: %.2f±%.2f" % (np.average(t_ooi),np.std(t_ooi),np.average(t_sils),np.std(t_sils))
#         elif stimid == 5:
#             t_dsi = DSi[conditions_all][np.where(fcls_sta == c+1)][:,0]
#             txt = "Avg. DSi: %.2f±%.2f" % (np.average(t_dsi),np.std(t_dsi))
#         else:
#             txt = ""
#         if (ci == 0) & (i==0):
#             txt = 'B'
#         elif (ci == 1) & (i==0):
#             txt = 'C'
#         else:
#             txt = None
#         with plt.rc_context({'font.size':fs, 'axes.titleweight': 'bold'}):
#             ax = plt.subplot(gs[i,ci+2])
#             plotPSTHs(ax,sts,txt,bins,palette[c], show_sd=False, lw=1)
#             plt.xticks(())
#             plt.yticks(())
#             ax.spines['top'].set_visible(False)
#             ax.spines['bottom'].set_visible(False)
#             ax.spines['left'].set_visible(False)
#             ax.spines['right'].set_visible(False)


            
#     with plt.rc_context({'font.size':fs, 'axes.titleweight': 'bold'}):
#         ax = plt.subplot(gs[i,1])
# #        t_dsi = DSi[with_sta_cells][np.where(fcls == c+1)][:,0]
# #        sns.distplot(t_dsi,bins=np.arange(0,0.8,0.1),kde=True, norm_hist=True)
#         if i == 0:
#             txt = 'E'
#         else:
#             txt = ''
# #        t_dsi = np.median(DSi[with_sta_cells][:,0])
#         trl_sta=[]    
#         stas=esta_all[conditions_all][np.where(fcls_sta == c+1)]
#         for ii in range(len(stas)):
#             if  not(stas[ii]==None):
#                 if len(stas[ii][2])>1:
#                     stime=stas[ii][2]
#                     ssta=stas[ii][3]
    
#                     xnew = np.linspace(stime.min(), stime.max(), 200)  
#                     sta_smooth = make_interp_spline(stime.flatten(), ssta.flatten())(xnew)
#                     sta_smooth=(sta_smooth-mean(sta_smooth))/std(sta_smooth,ddof=0)
#                     trl_sta.append(sta_smooth)
                    
#                     plt.plot(xnew,sta_smooth,linewidth=.8,alpha=.7)
#                     plt.axhline(y=0, color='k', linestyle='--',linewidth=.8)
# #                    ax.set_ylim((stime.min(),stime.max()))
#                     plt.axvline(x=.020, color='k', linestyle='--',linewidth=.8)
                
# #                plt.plot(stas[i][2],(stas[i][3]-mean(stas[i][3]))/max(abs(stas[i][3])))
#         if trl_sta:
#             plt.plot(xnew,mean(trl_sta,axis=0),linewidth=1.5,color='k')
#         ax.set_title(txt)
#         ax.set_xticks(())
#         ax.set_yticks(())
#         ax.set_xlim((-1,0.5))

#         ax.spines['top'].set_visible(False)
#         ax.spines['right'].set_visible(False)
#         ax.spines['bottom'].set_visible(False)
#         ax.spines['left'].set_visible(False)
#         alpha =.5
#         if i==len(show_order_sta)-1:
#             plt.xlabel('esta', fontsize=8) 

#     with plt.rc_context({'font.size':fs, 'axes.titleweight': 'bold'}):
#         ax = plt.subplot(gs[i,4])
# #        t_dsi = DSi[with_sta_cells][np.where(fcls == c+1)][:,0]
# #        sns.distplot(t_dsi,bins=np.arange(0,0.8,0.1),kde=True, norm_hist=True)
#         if i == 0:
#             txt = 'E'
#         else:
#             txt = ''
# #        t_dsi = np.median(DSi[with_sta_cells][:,0])
#         trl_psd=[]    
#         psds=psd_all[conditions_all][np.where(fcls_sta == c+1)]
# #        freq_dtls=freq_details[conditions_all][np.where(fcls_sta == c+1)]
# #        peak_frq=np.mean(freq_dtls)
# #        bwidth=peak_frq[2]-peak_frq[1]
# #        peak_frq_table.append(np.hstack((peak_frq,bwidth)))
#         for ii in range(len(psds)):
#             if  any(psds[ii]):
#                 if len(psds[ii])>1:
#                     sfreq=freqsl
#                     spsd=psds[ii]
    
#                     xnew = np.linspace(sfreq.min(), sfreq.max(), 20)  
                    
#                     psd_smooth = spsd/np.max(spsd)#spline(sfreq.flatten(), spsd.flatten(), xnew)
#                     #psd_smooth=(psd_smooth-mean(psd_smooth))/std(psd_smooth,ddof=0)
#                     trl_psd.append(psd_smooth)
                    
#                     plt.plot(sfreq,psd_smooth,linewidth=.8,alpha=.7)
#                     plt.axhline(y=0, color='k', linestyle='--',linewidth=.8)
# #                    ax.set_ylim((stime.min(),stime.max()))
#                     plt.axvline(x=.020, color='k', linestyle='--',linewidth=.8)
                
# #                plt.plot(stas[i][2],(stas[i][3]-mean(stas[i][3]))/max(abs(stas[i][3])))
#         if trl_sta:
#             plt.plot(sfreq,mean(trl_psd,axis=0),linewidth=1.5,color='k')
#         ax.set_title(txt)
#         ax.set_xticks(())
#         ax.set_yticks(())
#         ax.set_xlim((0,10))

#         ax.spines['top'].set_visible(False)
#         ax.spines['right'].set_visible(False)
#         ax.spines['bottom'].set_visible(False)
#         ax.spines['left'].set_visible(False)
#         alpha =.5
#         if i==len(show_order_sta)-1:
#             plt.xlabel('psd', fontsize=8) 

#     with plt.rc_context({'font.size':fs, 'axes.titleweight': 'bold'}):
#         ax = plt.subplot(gs[i,5])
# #        t_dsi = DSi[conditions_all][np.where(fcls == c+1)][:,0]
# #        sns.distplot(t_dsi,bins=np.arange(0,0.8,0.1),kde=True, norm_hist=True)
#         if i == 0:
#             txt = 'E'
#         else:
#             txt = ''

        
#         clnames=Cell_names[conditions_all][np.where(fcls_sta == c+1)]
#         recording_names=[]
#         for idss, rcrdings in enumerate(Cell_names):
#             recording_names.append(Cell_names[idss][:-4])
            
#         recording_names_cluster=[]
#         for idss, rcrdings in enumerate(clnames):
#             recording_names_cluster.append(clnames[idss][:-4])
            
#         unqstrgns_cluster=np.unique(recording_names_cluster)    
#         unqstrgns=np.unique(recording_names)    
        
#         rcrding_numbers=[]
#         for unqnbr in unqstrgns:
#             rcrding_numbers.append(recording_names_cluster.count(unqnbr))
        
#         cmap = plt.cm.prism

#         plt.pie(rcrding_numbers, shadow=True, startangle=90)
        

        
# ax = plt.subplot(gs[:,0])
# p = ax.get_position()
# p.x1 = p.x1-0.02
# ax.set_position(p)
# with plt.rc_context({'lines.linewidth': 2, 'font.size':fs, 'axes.titleweight': 'bold'}):
#     dend = cluster.hierarchy.dendrogram(l, p=n, no_labels=False, leaf_font_size=7, color_threshold=t, 
#                                         distance_sort='none', link_color_func=lambda k: cs[k-l.shape[0]-1], 
#                                         truncate_mode='lastp', show_leaf_counts=True, orientation='left')

#     ax.set_title("A")
#     ax.set_yticklabels(labels)
#     ax.set_xticks(())
#     ax.spines['top'].set_visible(False)
#     ax.spines['bottom'].set_visible(False)
#     ax.spines['left'].set_visible(False)
#     ax.spines['right'].set_visible(False)

# if SAVE_FIGS:
#    plt.savefig('clusters_e_STA_color_mixed_rd10_neworder_before'+st_name+'.pdf', bbox_inches='tight')
    
    
    
    
# Cells_names_and_clusters_sta=list(zip(Cell_names[conditions_all],fcls_sta))
    
# with open("clusetr_numbers_sta_rd_before.txt", 'w') as output:
#     for row in Cells_names_and_clusters_sta:
#         output.write(str(row) + '\n')      
        
        



        #%% tsne plots for esta clusters

   
from sklearn.manifold import TSNE
from sklearn.preprocessing import normalize
from sklearn.preprocessing import robust_scale
from matplotlib.colors import ListedColormap

#t_ = cluster_number
#l_ = cluster.hierarchy.linkage(zssta, method='ward')
#fcls_ = cluster.hierarchy.fcluster(l_, t=t_, criterion='maxclust')
n_flat_clusters_ = np.unique(fcls_sta).shape[0]
show_order_ = np.unique(fcls_sta)[::-1]-1

model = TSNE(n_components=2, random_state=0, perplexity=20,n_iter=5000)#,init='pca')
proj = model.fit_transform(zssta) 

#import umap
#model = umap.UMAP() 
#proj = model.fit_transform(psths) 

with plt.rc_context(rcParams):
    plt.figure(figsize=(14,5))

    ax = plt.subplot(121)
    # ax.set_facecolor((0.3,0.3,0.3))
    s = plt.scatter(proj[:,0],proj[:,1],s=16,lw=0,c=show_order_[fcls_sta-1],
                    cmap=ListedColormap(sns.hls_palette(n_flat_clusters_,l=0.6,s=0.6).as_hex()))
#    plt.rc('xtick', labelsize=14)    # fontsize of the tick labels
#    plt.rc('ytick', labelsize=14)    # fontsize of the tick labels
    plt.rcParams.update({'font.size': 18})



    cb = plt.colorbar(s)
 #   cb.set_label('Cluster')
    plt.title('t-SNE embeddings')

    # plt.axis('equal')
    plt.grid(False)
    ax = plt.subplot(122)
    # ax.set_facecolor((0.3,0.3,0.3))
    p = plt.scatter(proj[:,0],proj[:,1],s=16,lw=0,c=np.array(((OOi[conditions_all]))),
                    cmap=sns.diverging_palette(180,359,sep=1,n=32,as_cmap=True))
    cb = plt.colorbar(p)
    cb.set_label('Bias index')
    # plt.axis('equal')

    plt.grid(False)
    plt.title('t-SNE embeddings')
    plt.rcParams.update({'font.size': 18})
#    plt.rc('xtick', labelsize=14)    # fontsize of the tick labels
#    plt.rc('ytick', labelsize=14)    # fontsize of the tick labels


if SAVE_FIGS:
    plt.savefig('clusters_tsne_normalized_esta_rd10_shortsta2.pdf', bbox_inches='tight')
    
    plt.savefig('clusters_tsne_normalized_esta_rd10_shortsta2.svg', bbox_inches='tight')

                
#%% plot esta clusters and  make table of frequancies
        
from spk_trains_maker import esta_clustsering        
t=cluster_number
freqsl= freqsl_b
plot_stims=[0,1]     
plot_psd=True  
frq_table_b=esta_clustsering(Stimuli,show_order_sta,silhouettes,palette,zssta,fcls_sta,l,cs,conditions_all,esta_all,psd_all_before,freqsl,Cell_names,plot_stims,t,'rd10_Before_shortsta2',OOi,plot_psd,SAVE_FIGS)

np.mean(frq_table_b,axis=0)

freqsl= freqsl_a
t=cluster_number
plot_stims=[0]       
frq_table_a=esta_clustsering(spk_data_after,show_order_sta,silhouettes,palette,zssta,fcls_sta,l,cs,conditions_all,esta_all_rd_after,psd_all_after,freqsl,Cell_names_rd_after,plot_stims,t,'rd10_After_shortsta2',OOi,plot_psd,SAVE_FIGS)
np.median(frq_table_a,axis=0)

#%% PCA
st_name='Flash'
# Z-score the features
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
scaler.fit(stas_3)
zstas_3 = scaler.transform(stas_3)

from sklearn.decomposition import PCA
pca = PCA(n_components=15)
X_r = pca.fit(zssta).transform(zssta)

plt.figure()

plt.figure(figsize=(14,10))

s = plt.scatter(X_r[:,0],X_r[:,1],s=16,lw=2,c=show_order_sta[fcls_sta-1],
                cmap=ListedColormap(sns.hls_palette(n_flat_clusters_,l=0.6,s=0.6).as_hex()))
cb = plt.colorbar(s)
cb.set_label('Cluster')
plt.title('PCA e-STAs') 
plt.xlabel('PC1')
plt.ylabel('PC2')
print(sum(pca.explained_variance_ratio_))   

#plt.ylim([-10,10])
#if SAVE_FIGS:
#    plt.savefig('PCA_projection_STA'+st_name+'.pdf', bbox_inches='tight')

plt.rcParams.update({'font.size': 18})
plt.rc('xtick', labelsize=14)    # fontsize of the tick labels
plt.rc('ytick', labelsize=14) 
plt.figure(figsize=(14,5), dpi=100)
axes=plt.subplot(121)
axes.scatter(X_r[:,0], X_r[:,1],s=16,lw=0, c=show_order_sta[fcls_sta-1],
             cmap=ListedColormap(sns.hls_palette(n_flat_clusters_,l=0.6,s=0.6).as_hex()))
axes.set_xlabel('PC1')
axes.set_ylabel('PC2')
axes.set_title('PC1 vs PC2')
axes.axvline(c='grey', lw=1)
axes.axhline(c='grey', lw=1)
   # fontsize of the tick labels

#plt.ylim([-10,10])


axes=plt.subplot(122)
axes.scatter(X_r[:,0], X_r[:,2],s=16,lw=0, c=show_order_sta[fcls_sta-1],
             cmap=ListedColormap(sns.hls_palette(n_flat_clusters_,l=0.6,s=0.6).as_hex()))
axes.set_xlabel('PC1')
axes.set_ylabel('PC3')
axes.set_title('PC1 vs PC3')
axes.axvline(c='grey', lw=1)
axes.axhline(c='grey', lw=1)
plt.rcParams.update({'font.size': 18})
plt.rc('xtick', labelsize=14)    # fontsize of the tick labels
plt.rc('ytick', labelsize=14)    # fontsize of the tick labels


#plt.ylim([-10,10])
if SAVE_FIGS:
    plt.savefig('Nornalized_PCA_projection_STA_rd10_shortsta2'+st_name+'.pdf', bbox_inches='tight')
    plt.savefig('Nornalized_PCA_projection_STA_rd10_shortsta2'+st_name+'.svg', bbox_inches='tight')