"""Draw the briefing's IC and decile figures using its shared chart palette."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
import pandas as pd
import numpy as np

TEAL, RUST, INK = '#087b78', '#b24f35', '#243648'

def render(root):
    font = Path('C:/Windows/Fonts/msyh.ttc')
    font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({'font.family':font_manager.FontProperties(fname=str(font)).get_name(),
        'font.size':11,'axes.titlesize':12,'axes.titlepad':14,
        'axes.spines.top':False,'axes.spines.right':False,
        'axes.edgecolor':'#b7c1bf','text.color':INK,'axes.labelcolor':INK,
        'xtick.color':INK,'ytick.color':INK,'axes.unicode_minus':False,
        'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white',
        'svg.fonttype':'none'})
    daily=pd.read_csv(root/'evaluation/daily_ic.csv')
    groups=pd.read_csv(root/'evaluation/decile_summary.csv')
    dispersion=pd.read_csv(root/'evaluation/group_dispersion.csv')
    dest=root/'figures';dest.mkdir(exist_ok=True)
    def save(fig,name):
        fig.savefig(dest/(name+'.png'),dpi=200,bbox_inches='tight')
        fig.savefig(dest/(name+'.svg'),bbox_inches='tight')
        plt.close(fig)
    for c,ds in daily.groupby('formal_column',sort=False):
        ds=ds.sort_values('date');dates=pd.to_datetime(ds.date)
        fig,axes=plt.subplots(2,2,figsize=(12,7.4),sharex=True)
        for col,(metric,label,color) in enumerate([('pearson_ic','Pearson IC',RUST),('rank_ic','Rank IC',TEAL)]):
            ax=axes[0,col]
            ax.plot(dates,ds[metric],lw=.65,color=color,alpha=.28,label='每日相关')
            ax.plot(dates,ds[metric+'_rolling20'],lw=1.65,color=color,label='20 日滚动均值')
            ax.set_title(label+' · 日度与滚动均值',loc='left')
            ax.legend(frameon=False,fontsize=9,loc='upper right')
            axes[1,col].plot(dates,ds[metric+'_cumulative'],lw=1.7,color=color)
            axes[1,col].set_title('累计 '+label,loc='left')
            axes[1,col].set_xlabel('交易日期')
            for a in axes[:,col]:
                a.axhline(0,color=INK,lw=.6,alpha=.7)
                a.grid(axis='y',color='#e4e8e2',lw=.6)
                a.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
                a.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                a.tick_params(axis='x',labelrotation=25,labelsize=9)
        fig.suptitle(c+'  /  全部 601 日',x=.06,ha='left',fontsize=13)
        fig.tight_layout(rect=(0,0,1,.96),h_pad=2.3,w_pad=2.5)
        save(fig,c+'-daily')
        monthly=ds.groupby(ds.date.str[:7]).rank_ic.mean()
        fig,ax=plt.subplots(figsize=(12,4.2));x=np.arange(len(monthly))
        ax.bar(x,monthly,width=.68,color=[TEAL if v>=0 else RUST for v in monthly])
        ax.axhline(0,color=INK,lw=.7);ax.set_axisbelow(True);ax.grid(axis='y',color='#e4e8e2',lw=.6)
        ax.set_xticks(x[::2],monthly.index[::2],rotation=35,ha='right')
        ax.set_ylabel('月内日均 Rank IC');ax.set_title(c+'  /  30 个月的方向与强度',loc='left')
        fig.tight_layout();save(fig,c+'-monthly')
        g=groups[(groups.formal_column==c)&(groups.period=='full')].sort_values('group')
        d=dispersion[(dispersion.formal_column==c)&(dispersion.period=='full')].sort_values('group')
        mu=g['mean'].to_numpy()*10000
        fig,axes=plt.subplots(1,2,figsize=(12,4.5))
        for ax,err,title,color in [(axes[0],d.typical_within_std.to_numpy()*10000,'组内离散：均值 ± 日内标准差',TEAL),(axes[1],g.nw_se.to_numpy()*19600,'均值估计：95% NW 区间',RUST)]:
            ax.errorbar(range(1,11),mu,yerr=err,fmt='o-',color=color,capsize=4,lw=1.3,ms=5)
            ax.axhline(0,color=INK,lw=.6);ax.grid(axis='y',color='#e4e8e2',lw=.6)
            ax.set_xticks(range(1,11),['G'+str(i) for i in range(1,11)])
            ax.set_ylabel('日均毛收益（bp）');ax.set_xlabel('因子原值由低到高 →');ax.set_title(title,loc='left')
        fig.suptitle(c+'  /  全部 601 日',x=.06,ha='left',fontsize=13)
        fig.tight_layout(rect=(0,0,1,.94));save(fig,c+'-groups')
    return sorted(dest.glob('*'))
