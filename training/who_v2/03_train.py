import argparse, json, random
from collections import Counter
from pathlib import Path
import cv2, numpy as np, pandas as pd, torch
from torch import nn
from torch.utils.data import Dataset,DataLoader,WeightedRandomSampler
from torchvision.transforms import v2
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from model import WhoHybrid

class SeqDataset(Dataset):
    def __init__(self,manifest,cache_dir,split,seq_len=24,stride=8,min_agreement=.75,train=False):
        self.df=pd.read_csv(manifest)
        self.cache=Path(cache_dir); self.seq_len=seq_len; self.samples=[]; self.train=train
        for (ds,stem),g in self.df[self.df.split==split].groupby(['dataset','video_stem']):
            g=g.sort_values('frame_idx')
            vdir=self.cache/ds/stem
            fidxp=vdir/'frame_idx.npy'; lmp=vdir/'landmarks.npy'
            if not fidxp.exists() or not lmp.exists(): continue
            cached=np.load(fidxp); pos={int(f):i for i,f in enumerate(cached)}
            valid=g[(g.washing_consensus==1)&(g.who_agreement>=min_agreement)&(g.who_transition==0)]
            labels=dict(zip(valid.frame_idx.astype(int),valid.who_code.astype(int)))
            frames=sorted(set(pos)&set(labels), key=lambda f: pos[f])
            # Split into truly contiguous cached runs. This prevents a sequence from
            # jumping across transition-excluded gaps.
            runs=[]; run=[]; prev_pos=None
            for f in frames:
                p=pos[f]
                if prev_pos is None or p==prev_pos+1:
                    run.append(f)
                else:
                    if run: runs.append(run)
                    run=[f]
                prev_pos=p
            if run: runs.append(run)
            for run in runs:
                for s in range(0,max(0,len(run)-seq_len+1),stride):
                    win=run[s:s+seq_len]
                    if len(win)<seq_len: continue
                    labs=[labels[f] for f in win]; top,n=Counter(labs).most_common(1)[0]
                    if n/seq_len < .80: continue
                    self.samples.append((ds,stem,[pos[f] for f in win],win,top))
        self.aug=v2.Compose([v2.RandomHorizontalFlip(.5),v2.RandomRotation(8),v2.ColorJitter(.15,.15,.1,.03)]) if train else None
    def __len__(self): return len(self.samples)
    def __getitem__(self,i):
        ds,stem,positions,frames,y=self.samples[i]; vdir=self.cache/ds/stem
        lm=np.load(vdir/'landmarks.npy',mmap_mode='r')[positions].astype(np.float32)
        imgs=[]
        for f in frames:
            im=cv2.imread(str(vdir/f'{f:07d}.jpg'))
            if im is None: im=np.zeros((192,192,3),np.uint8)
            im=cv2.cvtColor(im,cv2.COLOR_BGR2RGB)
            imgs.append(torch.from_numpy(im).permute(2,0,1).float()/255.)
        x=torch.stack(imgs)
        if self.aug:
            # apply same random transform to whole sequence by temporarily flattening T into batch;
            # torchvision v2 samples parameters consistently for leading dims
            x=self.aug(x)
        x=(x-torch.tensor([.485,.456,.406])[:,None,None])/torch.tensor([.229,.224,.225])[:,None,None]
        return x,torch.from_numpy(lm),torch.tensor(y,dtype=torch.long)

def eval_model(model,loader,device):
    model.eval(); ys=[]; ps=[]; loss_sum=0; ce=nn.CrossEntropyLoss()
    with torch.no_grad():
        for x,l,y in loader:
            x,l,y=x.to(device),l.to(device),y.to(device)
            out=model(x,l); loss_sum+=ce(out,y).item()*len(y)
            ys += y.cpu().tolist(); ps += out.argmax(1).cpu().tolist()
    return loss_sum/max(1,len(ys)), f1_score(ys,ps,average='macro',zero_division=0),ys,ps

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',default='manifests/master_manifest.csv'); ap.add_argument('--cache-dir',default='cache'); ap.add_argument('--epochs',type=int,default=30); ap.add_argument('--batch-size',type=int,default=4); ap.add_argument('--lr',type=float,default=3e-4); ap.add_argument('--seq-len',type=int,default=24); args=ap.parse_args()
    base=Path(__file__).resolve().parent
    manifest=Path(args.manifest); manifest=manifest if manifest.is_absolute() else base/manifest
    cache=Path(args.cache_dir); cache=cache if cache.is_absolute() else base/cache
    out=base/'checkpoints'; out.mkdir(exist_ok=True); reports=base/'reports'; reports.mkdir(exist_ok=True)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Device:',device)
    if device.type=='cuda': print('GPU:',torch.cuda.get_device_name(0))
    train=SeqDataset(manifest,cache,'train',seq_len=args.seq_len,train=True); val=SeqDataset(manifest,cache,'val',seq_len=args.seq_len)
    print('Sequences train/val:',len(train),len(val))
    if len(train)==0 or len(val)==0: raise SystemExit('No sequences. Build manifest/cache first.')
    counts=Counter(s[-1] for s in train.samples)
    weights=[1.0/(counts[s[-1]]**0.5) for s in train.samples]
    sampler=WeightedRandomSampler(weights,num_samples=len(weights),replacement=True)
    print('Train class sequences:',dict(sorted(counts.items())))
    tl=DataLoader(train,batch_size=args.batch_size,sampler=sampler,num_workers=0,pin_memory=device.type=='cuda'); vl=DataLoader(val,batch_size=args.batch_size,shuffle=False,num_workers=0,pin_memory=device.type=='cuda')
    model=WhoHybrid().to(device); opt=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=1e-4); ce=nn.CrossEntropyLoss(label_smoothing=.03)
    scaler=torch.cuda.amp.GradScaler(enabled=device.type=='cuda'); best=-1
    for ep in range(1,args.epochs+1):
        model.train(); total=0; n=0
        for x,l,y in tl:
            x,l,y=x.to(device),l.to(device),y.to(device); opt.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=device.type=='cuda'):
                logits=model(x,l); loss=ce(logits,y)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); total+=loss.item()*len(y); n+=len(y)
        vl_loss,f1,ys,ps=eval_model(model,vl,device)
        print(f'Epoch {ep:02d}: train_loss={total/n:.4f} val_loss={vl_loss:.4f} macroF1={f1:.4f}')
        if f1>best:
            best=f1; torch.save({'model':model.state_dict(),'epoch':ep,'macro_f1':f1,'seq_len':args.seq_len,'image_size':192},out/'who_v2_best.pt')
            (reports/'val_classification.txt').write_text(classification_report(ys,ps,digits=4,zero_division=0),encoding='utf-8')
            np.savetxt(reports/'val_confusion_matrix.csv',confusion_matrix(ys,ps,labels=list(range(7))),fmt='%d',delimiter=',')
    print('Best macro F1:',best)
if __name__=='__main__': main()
