"""Cut one character out of a flat-background sprite sheet.

usage: python3 scripts/cut.py SHEET.png x0,y0,x1,y1 scripts/src/poses/NAME.png
Keys out the sheet's background colour (sampled from the crop border), drops the
drawn floor shadow and enclosed background holes, and unmixes the anti-aliased edge.
Needs Pillow, numpy, scipy.
"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
x0,y0,x1,y1=map(int,sys.argv[2].split(","))
src=np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.float32)[y0:y1,x0:x1]
B=np.median(np.concatenate([src[0],src[-1],src[:,0],src[:,-1]]),axis=0)
k=(src@B)/(B@B)
res=np.linalg.norm(src-k[...,None]*B,axis=2)
bglike=(k>0.5)&(res<9)
# background = bg-like regions connected to border
lab,_=ndi.label(bglike)
border=set(np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])))-{0}
bg=np.isin(lab,list(border))
fg=~bg
lab2,n=ndi.label(fg); sizes=ndi.sum(fg,lab2,range(1,n+1))
fg=lab2==(np.argmax(sizes)+1)
meank=ndi.mean(k,lab,range(1,lab.max()+1)); sz=ndi.sum(bglike,lab,range(1,lab.max()+1)); meanr=ndi.mean(res,lab,range(1,lab.max()+1)); big=np.where((sz>20)&(meank>0.62)&(meanr<4.5) | (sz>40)&(meank>0.7)&(meanr<7))[0]+1; fg&=~np.isin(lab,big)
# soft edge: in band around boundary estimate alpha by unmixing vs local bg (k*B)
band=fg & ~ndi.binary_erosion(fg,iterations=2)
alpha=fg.astype(np.float32)
F=np.array([28,28,30.])
lum=lambda c:c@np.array([.299,.587,.114])
bgcol=np.clip(k,0.5,1.0)[...,None]*B
a=(lum(bgcol)-lum(src))/(lum(bgcol)-lum(F)+1e-3)
a=np.clip(a,0,1)
bright=lum(src)>lum(bgcol)+6   # shoe/skin brighter than bg: keep opaque
alpha[band & ~bright]=a[band & ~bright]
alpha=np.maximum(alpha, ndi.binary_erosion(fg,iterations=2))
# decontaminate band colours
col=src.copy()
m=band&(alpha>0.02)
col[m]=np.clip((src[m]-(1-alpha[m])[:,None]*bgcol[m])/alpha[m][:,None],0,255)
rgba=np.dstack([col,alpha*255]).astype(np.uint8)
im=Image.fromarray(rgba,"RGBA"); im=im.crop(im.getchannel("A").getbbox())
im.save(sys.argv[3]); print(im.size)
