import torch
from torch import nn
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

class WhoHybrid(nn.Module):
    def __init__(self,num_classes=7,landmark_dim=128,hidden=128,pretrained=True):
        super().__init__()
        weights=MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        net=mobilenet_v3_small(weights=weights)
        self.rgb=net.features
        self.pool=nn.AdaptiveAvgPool2d(1)
        rgb_dim=576
        self.rgb_proj=nn.Sequential(nn.Linear(rgb_dim,128),nn.ReLU(),nn.Dropout(.15))
        self.lm=nn.Sequential(nn.Linear(landmark_dim,128),nn.ReLU(),nn.Linear(128,64),nn.ReLU())
        self.gru=nn.GRU(192,hidden,num_layers=2,batch_first=True,dropout=.2,bidirectional=True)
        self.head=nn.Sequential(nn.Linear(hidden*2,128),nn.ReLU(),nn.Dropout(.25),nn.Linear(128,num_classes))
    def forward(self,images,landmarks):
        # images B,T,3,H,W ; landmarks B,T,128
        b,t,c,h,w=images.shape
        x=images.reshape(b*t,c,h,w)
        x=self.pool(self.rgb(x)).flatten(1)
        x=self.rgb_proj(x).reshape(b,t,-1)
        l=self.lm(landmarks)
        z=torch.cat([x,l],dim=-1)
        z,_=self.gru(z)
        return self.head(z[:,-1])
