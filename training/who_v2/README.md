# AKAM WHO v2 training

The PSKUS dataset can stay anywhere (for example on the Windows Desktop). Nothing copies the raw videos into the app repo.

## 1. GPU environment (GTX 1650)
Use a separate training venv so the running backend environment remains untouched.

```bat
cd C:\path\to\hospital-ai-web\training\who_v2
py -3.11 -m venv train_env
train_env\Scripts\activate
python -m pip install --upgrade pip
pip uninstall -y torch torchvision torchaudio
pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements-training.txt
python check_gpu.py
```

You want `CUDA available: True` and `GPU: NVIDIA GeForce GTX 1650`.

## 2. Build leakage-free consensus manifest
Replace the data path with the folder that directly contains `DataSet1 ... DataSet11`.

```bat
python 01_build_manifest.py --data-root "C:\Users\YOUR_NAME\Desktop\PSKUS_dataset"
```

The builder discovers `Annotator*`, keeps washing and WHO consensus separately, marks WHO transition frames, and splits by whole video.

## 3. Extract a reusable 15 FPS cache
This CPU-heavy step runs MediaPipe only once and stores 192x192 hand crops + 128-D landmark features.

```bat
python 02_extract_cache.py --manifest manifests\master_manifest.csv --cache-dir cache --sample-every 2 --image-size 192
```

## 4. Train on GTX 1650
Start conservatively with batch size 4. Mixed precision is enabled automatically on CUDA.

```bat
python 03_train.py --epochs 30 --batch-size 4 --lr 0.0003
```

If CUDA runs out of memory, use `--batch-size 2`. If VRAM usage is low, try 6 or 8.

Best checkpoint: `checkpoints\who_v2_best.pt`
Reports: `reports\val_classification.txt`, `reports\val_confusion_matrix.csv`

## 5. Export CPU inference model

```bat
python 04_export_onnx.py
```

Output: `checkpoints\who_v2.onnx`.

Do not replace the current app model until v2 validation is clearly better and the backend is updated to provide both RGB clips and landmark clips.
