import argparse, math
from pathlib import Path
import cv2, numpy as np, pandas as pd
import mediapipe as mp
from tqdm import tqdm


def hand_features(results):
    hands=[]
    if results.multi_hand_landmarks:
        hands=sorted(results.multi_hand_landmarks,key=lambda h:h.landmark[0].x)[:2]
    feat=[]
    for h in hands:
        w=h.landmark[0]; m=h.landmark[9]
        s=max(math.hypot(w.x-m.x,w.y-m.y),1e-6)
        for lm in h.landmark:
            feat += [(lm.x-w.x)/s,(lm.y-w.y)/s,(lm.z-w.z)/s]
    feat += [0.0]*(126-len(feat))
    if len(hands)==2:
        a,b=hands
        feat += [math.hypot(a.landmark[0].x-b.landmark[0].x,a.landmark[0].y-b.landmark[0].y),
                 math.hypot(a.landmark[8].x-b.landmark[8].x,a.landmark[8].y-b.landmark[8].y)]
    else: feat += [1.0,1.0]
    return np.asarray(feat,np.float32), hands

def crop_from_hands(frame,hands,pad=.30,size=192):
    h,w=frame.shape[:2]
    if not hands:
        return np.zeros((size,size,3),np.uint8)
    xs=[]; ys=[]
    for hand in hands:
        xs += [lm.x*w for lm in hand.landmark]; ys += [lm.y*h for lm in hand.landmark]
    x1,x2=min(xs),max(xs); y1,y2=min(ys),max(ys)
    bw,bh=x2-x1,y2-y1
    x1=max(0,int(x1-pad*bw)); x2=min(w,int(x2+pad*bw))
    y1=max(0,int(y1-pad*bh)); y2=min(h,int(y2+pad*bh))
    if x2<=x1 or y2<=y1: return np.zeros((size,size,3),np.uint8)
    crop=frame[y1:y2,x1:x2]
    return cv2.resize(crop,(size,size),interpolation=cv2.INTER_AREA)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',default='manifests/master_manifest.csv')
    ap.add_argument('--cache-dir',default='cache')
    ap.add_argument('--sample-every',type=int,default=2,help='30fps->15fps uses 2')
    ap.add_argument('--image-size',type=int,default=192)
    args=ap.parse_args()
    base=Path(__file__).resolve().parent
    manifest=Path(args.manifest); manifest=manifest if manifest.is_absolute() else base/manifest
    cache=Path(args.cache_dir); cache=cache if cache.is_absolute() else base/cache
    cache.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(manifest)
    mp_hands=mp.solutions.hands
    hands=mp_hands.Hands(static_image_mode=False,max_num_hands=2,min_detection_confidence=.4,min_tracking_confidence=.4)
    index=[]
    for (ds,stem),g in tqdm(df.groupby(['dataset','video_stem']),desc='videos'):
        vp=Path(str(g.video_path.iloc[0]))
        if not vp.exists(): continue
        needed=set(int(x) for x in g.frame_idx.iloc[::args.sample_every])
        cap=cv2.VideoCapture(str(vp)); fi=0
        vdir=cache/ds/stem; vdir.mkdir(parents=True,exist_ok=True)
        lms=[]; frames_meta=[]
        while True:
            ok,frame=cap.read()
            if not ok: break
            if fi in needed:
                rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                res=hands.process(rgb)
                feat,hs=hand_features(res)
                crop=crop_from_hands(frame,hs,size=args.image_size)
                img_path=vdir/f'{fi:07d}.jpg'
                cv2.imwrite(str(img_path),crop,[int(cv2.IMWRITE_JPEG_QUALITY),90])
                lms.append(feat); frames_meta.append(fi)
            fi+=1
        cap.release()
        if lms:
            np.save(vdir/'landmarks.npy',np.stack(lms))
            np.save(vdir/'frame_idx.npy',np.asarray(frames_meta,np.int32))
            index.append({'dataset':ds,'video_stem':stem,'cache_dir':str(vdir),'frames_cached':len(lms),'split':g.split.iloc[0]})
    hands.close()
    pd.DataFrame(index).to_csv(cache/'cache_index.csv',index=False)
    print(f'Cached {len(index)} videos -> {cache}')
if __name__=='__main__': main()
