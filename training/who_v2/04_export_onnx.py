import argparse
from pathlib import Path
import torch
from model import WhoHybrid

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--checkpoint',default='checkpoints/who_v2_best.pt'); ap.add_argument('--out',default='checkpoints/who_v2.onnx'); args=ap.parse_args()
    base=Path(__file__).resolve().parent; ck=Path(args.checkpoint); ck=ck if ck.is_absolute() else base/ck; out=Path(args.out); out=out if out.is_absolute() else base/out
    data=torch.load(ck,map_location='cpu'); model=WhoHybrid(pretrained=False); model.load_state_dict(data['model']); model.eval(); t=int(data.get('seq_len',24)); s=int(data.get('image_size',192))
    images=torch.randn(1,t,3,s,s); landmarks=torch.randn(1,t,128)
    torch.onnx.export(model,(images,landmarks),out,input_names=['images','landmarks'],output_names=['logits'],opset_version=17,dynamic_axes={'images':{0:'batch'},'landmarks':{0:'batch'},'logits':{0:'batch'}})
    print('Exported:',out)
if __name__=='__main__': main()
