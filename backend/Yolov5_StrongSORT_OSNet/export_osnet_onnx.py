import torch
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[0]
sys.path.append(str(repo_root))

from boxmot.appearance.backbones.osnet import osnet_x0_25

# Load model without classification head
model = osnet_x0_25(num_classes=0, pretrained=False)

# Strip classification weights from checkpoint
state_dict = torch.load("boxmot/osnet_x0_25_msmt17.pt", map_location='cpu')
state_dict = {k: v for k, v in state_dict.items() if not k.startswith("classifier.")}
model.load_state_dict(state_dict, strict=False)
model.eval()

dummy_input = torch.randn(1, 3, 256, 128)

torch.onnx.export(
    model,
    dummy_input,
    "osnet_x0_25.onnx",
    input_names=["input"],
    output_names=["embedding"],
    dynamic_axes={"input": {0: "batch_size"}, "embedding": {0: "batch_size"}},
    opset_version=11
)

print("✅ ONNX export successful: osnet_x0_25.onnx")
