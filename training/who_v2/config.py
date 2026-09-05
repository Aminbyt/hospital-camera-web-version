from dataclasses import dataclass
from pathlib import Path

@dataclass
class TrainConfig:
    data_root: Path
    work_dir: Path = Path(__file__).resolve().parent
    fps_target: int = 15
    seq_len: int = 24
    seq_stride: int = 8
    min_who_agreement: float = 0.75
    min_washing_agreement: float = 0.75
    transition_margin_frames: int = 15  # ~0.5 s at 30 FPS
    image_size: int = 192
    batch_size: int = 4  # GTX 1650-safe starting point
    epochs: int = 30
    lr: float = 3e-4
    weight_decay: float = 1e-4
    num_classes: int = 7
    seed: int = 42

    @property
    def manifests_dir(self): return self.work_dir / "manifests"
    @property
    def cache_dir(self): return self.work_dir / "cache"
    @property
    def checkpoints_dir(self): return self.work_dir / "checkpoints"
    @property
    def reports_dir(self): return self.work_dir / "reports"
