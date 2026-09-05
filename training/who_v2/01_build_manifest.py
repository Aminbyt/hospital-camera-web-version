import argparse, json, random, re
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd

VIDEO_EXTS = {'.mp4','.avi','.mov','.mkv','.m4v'}
DATASET_RE = re.compile(r'dataset\s*0*(\d+)', re.I)

def natural_dataset_key(p: Path):
    m = DATASET_RE.search(p.name)
    return int(m.group(1)) if m else 9999

def find_dataset_dirs(root: Path):
    ds = [p for p in root.iterdir() if p.is_dir() and DATASET_RE.search(p.name)]
    return sorted(ds, key=natural_dataset_key)

def find_child_ci(parent: Path, name: str):
    for p in parent.iterdir():
        if p.name.lower() == name.lower(): return p
    return None

def load_annotation(path: Path):
    with path.open('r', encoding='utf-8') as f:
        obj = json.load(f)
    labels = obj.get('labels')
    if not isinstance(labels, list):
        raise ValueError(f'{path}: missing labels[]')
    extras = {k:v for k,v in obj.items() if k != 'labels'}
    return labels, extras

def consensus(vals):
    if not vals: return None, 0, 0.0
    c = Counter(vals)
    value, votes = c.most_common(1)[0]
    return value, votes, votes/len(vals)

def transition_mask(codes, margin):
    n=len(codes); mask=[False]*n
    for i in range(1,n):
        if codes[i] != codes[i-1]:
            lo=max(0,i-margin); hi=min(n,i+margin+1)
            for j in range(lo,hi): mask[j]=True
    return mask

def deterministic_split(stem, seed=42):
    # stable split by video stem, never by frame/window
    import hashlib
    v=int(hashlib.sha1(f'{seed}:{stem}'.encode()).hexdigest()[:8],16)%100
    if v < 80: return 'train'
    if v < 90: return 'val'
    return 'test'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data-root', required=True)
    ap.add_argument('--out', default='manifests/master_manifest.csv')
    ap.add_argument('--transition-margin', type=int, default=15)
    ap.add_argument('--allow-missing-video', action='store_true')
    args=ap.parse_args()

    root=Path(args.data_root).expanduser().resolve()
    out=Path(args.out)
    if not out.is_absolute(): out=Path(__file__).resolve().parent/out
    out.parent.mkdir(parents=True, exist_ok=True)

    rows=[]; video_rows=[]; warnings=[]
    datasets=find_dataset_dirs(root)
    if not datasets: raise SystemExit(f'No DataSet* folders found under {root}')

    for ds in datasets:
        ann_root=find_child_ci(ds,'Annotations')
        vids_root=find_child_ci(ds,'Videos') or find_child_ci(ds,'videos')
        if not ann_root:
            warnings.append(f'{ds.name}: no Annotations folder'); continue
        annotators=sorted([p for p in ann_root.iterdir() if p.is_dir() and p.name.lower().startswith('annotator')])
        if not annotators:
            warnings.append(f'{ds.name}: no Annotator* folders'); continue

        by_stem=defaultdict(list)
        for ad in annotators:
            for jp in ad.glob('*.json'):
                by_stem[jp.stem].append((ad.name,jp))

        video_index={}
        if vids_root:
            for vp in vids_root.iterdir():
                if vp.is_file() and vp.suffix.lower() in VIDEO_EXTS:
                    video_index[vp.stem]=vp

        for stem, anns in sorted(by_stem.items()):
            if stem not in video_index and not args.allow_missing_video:
                warnings.append(f'{ds.name}/{stem}: video missing, skipped')
                continue
            loaded=[]; extras_all={}
            for aname,jp in anns:
                try:
                    labels,extras=load_annotation(jp)
                    loaded.append((aname,labels))
                    extras_all[aname]=extras
                except Exception as e:
                    warnings.append(str(e))
            if not loaded: continue
            lengths=[len(x[1]) for x in loaded]
            n=min(lengths)
            if len(set(lengths))>1:
                warnings.append(f'{ds.name}/{stem}: annotation lengths {lengths}; using min={n}')

            frame_consensus=[]
            for i in range(n):
                washing=[int(labels[i].get('is_washing',0)) for _,labels in loaded]
                codes_raw=[int(labels[i].get('code',0)) for _,labels in loaded]
                # PSKUS code 7 = turning off faucet with paper towel. AKAM WHO v2
                # is a 7-class 0..6 washing-technique model, so map 7 -> 0 but preserve raw votes.
                codes=[0 if c==7 else c for c in codes_raw]
                wc,wv,wa=consensus(washing)
                cc,cv,ca=consensus(codes)
                # WHO hard target only makes sense while consensus says washing
                frame_consensus.append((wc,wv,wa,cc,cv,ca,codes,codes_raw,washing))
            raw_codes=[x[3] for x in frame_consensus]
            tmask=transition_mask(raw_codes,args.transition_margin)
            split=deterministic_split(f'{ds.name}/{stem}')
            vp=video_index.get(stem)

            for i,(wc,wv,wa,cc,cv,ca,codes,codes_raw,washing) in enumerate(frame_consensus):
                rows.append({
                    'dataset':ds.name,'video_stem':stem,'video_path':str(vp) if vp else '',
                    'frame_idx':i,'split':split,'num_annotators':len(loaded),
                    'washing_consensus':int(wc),'washing_votes':wv,'washing_agreement':round(wa,4),
                    'who_code':int(cc),'who_votes':cv,'who_agreement':round(ca,4),
                    'who_transition':int(tmask[i]),
                    'who_valid_strict':int(wc==1 and len(loaded)>=2 and cv>=2 and ca>=0.75 and not tmask[i]),
                    'washing_votes_raw':'|'.join(map(str,washing)),
                    'who_votes_raw':'|'.join(map(str,codes_raw)),
                    'who_votes_mapped':'|'.join(map(str,codes)),
                })
            video_rows.append({'dataset':ds.name,'video_stem':stem,'video_path':str(vp) if vp else '',
                               'split':split,'frames':n,'num_annotators':len(loaded)})

    if not rows: raise SystemExit('No manifest rows produced.')
    df=pd.DataFrame(rows)
    df.to_csv(out,index=False)
    vout=out.with_name(out.stem+'_videos.csv')
    pd.DataFrame(video_rows).to_csv(vout,index=False)
    print(f'Wrote {len(df):,} frame rows -> {out}')
    print(f'Wrote {len(video_rows):,} videos -> {vout}')
    print('\nSplit counts (videos):')
    print(pd.DataFrame(video_rows)['split'].value_counts())
    print('\nWHO strict usable frames:')
    print(df[df.who_valid_strict==1].who_code.value_counts().sort_index())
    print('\nWashing consensus:')
    print(df.washing_consensus.value_counts().sort_index())
    if warnings:
        wout=out.with_name(out.stem+'_warnings.txt')
        wout.write_text('\n'.join(warnings),encoding='utf-8')
        print(f'Warnings: {len(warnings)} -> {wout}')

if __name__=='__main__': main()
