import os, sys, hashlib, glob
import cv2
import numpy as np

print('=== InsightFace recognition diagnostic ===')
print('Python:', sys.version)

try:
    import onnxruntime as ort
    import insightface
    print('onnxruntime:', ort.__version__)
    print('providers:', ort.get_available_providers())
    print('insightface:', getattr(insightface, '__version__', 'unknown'))
except Exception as e:
    print('IMPORT ERROR:', repr(e)); raise

home = os.path.expanduser('~')
model_dir = os.path.join(home, '.insightface', 'models', 'antelopev2')
model_path = os.path.join(model_dir, 'glintr100.onnx')
print('recognition model:', model_path)
if not os.path.exists(model_path):
    print('ERROR: glintr100.onnx does not exist'); sys.exit(2)
size = os.path.getsize(model_path)
print('model size bytes:', size)
print('model size MiB:', round(size / 1024 / 1024, 2))
sha = hashlib.sha256()
with open(model_path, 'rb') as f:
    for chunk in iter(lambda: f.read(1024*1024), b''):
        sha.update(chunk)
print('model sha256:', sha.hexdigest())

# Find one registration image relative to backend working directory.
patterns = [
    os.path.join('data','REGISTER_PERSONS','*','*.jpg'),
    os.path.join('data','REGISTER_PERSONS','*','*.jpeg'),
    os.path.join('data','REGISTER_PERSONS','*','*.png'),
    os.path.join('data','register_persons','*','*.jpg'),
]
imgs=[]
for p in patterns: imgs += glob.glob(p)
if not imgs:
    print('ERROR: could not find a registration image under data/REGISTER_PERSONS'); sys.exit(3)
img_path=imgs[0]
img=cv2.imread(img_path)
print('test image:', img_path, 'shape=', None if img is None else img.shape)
if img is None: sys.exit(4)

from insightface.app import FaceAnalysis
app=FaceAnalysis(name='antelopev2', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_thresh=0.35, det_size=(640,640))
faces=app.get(img)
print('faces detected:', len(faces))
if not faces: sys.exit(5)
face=max(faces, key=lambda f: float((f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1])))
print('bbox:', face.bbox)

for attr in ['embedding','normed_embedding']:
    try:
        v=getattr(face, attr, None)
        print('\n', attr, 'type=', type(v))
        if v is None:
            print('  value=None'); continue
        a=np.asarray(v)
        print('  shape=', a.shape, 'dtype=', a.dtype)
        print('  finite=', int(np.isfinite(a).sum()), '/', a.size)
        print('  nan=', int(np.isnan(a).sum()), 'inf=', int(np.isinf(a).sum()))
        finite=a[np.isfinite(a)]
        if finite.size:
            print('  min=', float(finite.min()), 'max=', float(finite.max()), 'norm=', float(np.linalg.norm(finite)))
        print('  first10=', a.reshape(-1)[:10])
    except Exception as e:
        print('  ERROR reading', attr, repr(e))

print('\n=== Direct recognition-model inference ===')
# Locate recognition model inside FaceAnalysis and invoke get_feat on aligned crop if possible.
rec = None
for m in getattr(app, 'models', {}).values():
    if getattr(m, 'taskname', None) == 'recognition': rec=m
print('recognition object:', type(rec), 'found=', rec is not None)
if rec is not None:
    try:
        from insightface.utils import face_align
        crop = face_align.norm_crop(img, landmark=face.kps, image_size=112)
        print('aligned crop:', crop.shape, crop.dtype, 'finite=', np.isfinite(crop).all())
        feat = rec.get_feat(crop)
        a=np.asarray(feat)
        print('direct feat shape=',a.shape,'dtype=',a.dtype,'finite=',int(np.isfinite(a).sum()),'/',a.size,'nan=',int(np.isnan(a).sum()),'inf=',int(np.isinf(a).sum()))
        print('direct first10=',a.reshape(-1)[:10])
    except Exception as e:
        print('DIRECT INFERENCE ERROR:', repr(e))

print('\nIf embedding/direct feat contains NaN or Inf, the FastAPI recognition code is NOT the cause.')
