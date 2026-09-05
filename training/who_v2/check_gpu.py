import torch
print('torch:',torch.__version__)
print('CUDA available:',torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:',torch.cuda.get_device_name(0))
    print('CUDA runtime:',torch.version.cuda)
    x=torch.randn(1024,1024,device='cuda'); y=x@x
    print('GPU smoke test OK:',float(y.mean()))
