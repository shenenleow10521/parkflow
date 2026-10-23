"""Camera bay detection: does a small model trained on some cameras work on cameras it has never seen?

Data: CNRPark+EXT (Amato et al. 2017), 150x150 patches of single parking bays from 9 CCTV-style cameras,
labelled free or occupied, in sunny, overcast and rainy weather. Licence: ODbL v1.0.
  https://github.com/fabiocarrara/deep-parking/releases/download/archive/CNR-EXT-Patches-150x150.zip
  (unzip it; pass the folder that contains PATCHES/ and LABELS/ as --data)

Test: fine-tune MobileNetV3-Small (ImageNet weights; small enough for the Jetson-class AI box in the cost sheet)
on cameras 1-5, then test on every patch from cameras 6-9, which the model never sees. That is the situation
at a new mall: a model trained elsewhere, pointed at new cameras.
Reported: bay accuracy overall, by weather and by camera; and car counts per camera frame (all bays a camera
sees at one moment), which is what the pilot's "car count accuracy vs hand counts" target measures.

Usage: python cv_benchmark.py --data <folder>   (writes cv_benchmark_results.txt)
"""
import argparse
import random
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

SEED = 7
SIZE = 112                       # input size; patches are 150x150
TRAIN_CAMS = {1, 2, 3, 4, 5}
TEST_CAMS = {6, 7, 8, 9}
TRAIN_N = 20000                  # patches sampled from the training cameras
VAL_N = 2000                     # held out from the training cameras, to pick the best epoch
EPOCHS = 3
BATCH = 64

# Patch names look like S_2015-11-12_07.09_C01_184.jpg: weather, date, time, camera, bay.
NAME = re.compile(r"([SOR])_(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2})_C(\d+)_(\d+)\.jpg$", re.I)
WEATHER = {"S": "sunny", "O": "overcast", "R": "rainy"}


def load_labels(data):
    """Read LABELS/all.txt: '<path under PATCHES> <0 free | 1 occupied>'."""
    items = []
    for line in (data / "LABELS" / "all.txt").read_text().split("\n"):
        if not line.strip():
            continue
        rel, lab = line.split()
        m = NAME.search(rel)
        if not m:
            continue
        w, date, hhmm, cam, bay = m.groups()
        items.append({"path": data / "PATCHES" / rel, "label": int(lab), "weather": WEATHER[w.upper()],
                      "cam": int(cam), "frame": (date, hhmm, int(cam)), "bay": int(bay)})
    return items


class Patches(Dataset):
    def __init__(self, items, train):
        self.items = items
        aug = [transforms.RandomHorizontalFlip(), transforms.ColorJitter(0.3, 0.3, 0.2)] if train else []
        self.tf = transforms.Compose([transforms.Resize((SIZE, SIZE)), *aug, transforms.ToTensor(),
                                      transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        it = self.items[i]
        return self.tf(Image.open(it["path"]).convert("RGB")), it["label"]


def predict(model, items, workers):
    model.eval()
    out = []
    with torch.no_grad():
        for x, _ in DataLoader(Patches(items, False), batch_size=256, num_workers=workers):
            out.append(model(x).argmax(1).numpy())
    return np.concatenate(out)


def bay_metrics(y, p):
    tp = int(((p == 1) & (y == 1)).sum()); tn = int(((p == 0) & (y == 0)).sum())
    fp = int(((p == 1) & (y == 0)).sum()); fn = int(((p == 0) & (y == 1)).sum())
    return {"n": len(y), "acc": (tp + tn) / len(y), "prec": tp / max(tp + fp, 1), "rec": tp / max(tp + fn, 1),
            "fp": fp, "fn": fn}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    torch.set_num_threads(max(1, torch.get_num_threads()))

    items = load_labels(args.data)
    train_pool = [it for it in items if it["cam"] in TRAIN_CAMS]
    test = [it for it in items if it["cam"] in TEST_CAMS]
    random.shuffle(train_pool)
    val, train = train_pool[:VAL_N], train_pool[VAL_N:VAL_N + TRAIN_N]

    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, 2)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss()
    loader = DataLoader(Patches(train, True), batch_size=BATCH, shuffle=True, num_workers=args.workers,
                        generator=torch.Generator().manual_seed(SEED))
    best, best_state, log = -1.0, None, []
    t0 = time.time()
    for ep in range(1, EPOCHS + 1):
        model.train()
        for x, y in loader:
            opt.zero_grad()
            loss_fn(model(x), y).backward()
            opt.step()
        va = bay_metrics(np.array([it["label"] for it in val]), predict(model, val, args.workers))["acc"]
        log.append(f"  epoch {ep}: validation accuracy (training cameras) {va:.2%}")
        if va > best:
            best, best_state = va, {k: v.clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    train_min = (time.time() - t0) / 60

    t1 = time.time()
    p = predict(model, test, args.workers)
    ms = (time.time() - t1) / len(test) * 1000
    y = np.array([it["label"] for it in test])

    L = ["CAMERA BAY DETECTION ON UNSEEN CAMERAS (CNRPark+EXT)",
         f"  Model: MobileNetV3-Small (ImageNet weights), fine-tuned at {SIZE}x{SIZE}px, seed {SEED}",
         f"  Trained on cameras {sorted(TRAIN_CAMS)}: {len(train):,} patches, {EPOCHS} epochs ({train_min:.0f} min on CPU)",
         f"  Tested on cameras {sorted(TEST_CAMS)}, never seen in training: {len(test):,} patches", *log, ""]
    m = bay_metrics(y, p)
    L.append(f"BAYS: accuracy {m['acc']:.2%}  (occupied: precision {m['prec']:.2%}, recall {m['rec']:.2%}; "
             f"{m['fp']:,} free bays called occupied, {m['fn']:,} occupied called free)")
    for key, label in (("weather", "By weather"), ("cam", "By camera")):
        L.append(f"  {label}:")
        for v in sorted({it[key] for it in test}):
            idx = np.array([it[key] == v for it in test])
            mm = bay_metrics(y[idx], p[idx])
            L.append(f"    {str(v):<10}{mm['n']:>8,} patches   accuracy {mm['acc']:.2%}")

    # Car counts per camera frame: every bay one camera sees at one moment.
    frames = defaultdict(lambda: [0, 0, 0])            # true occupied, predicted occupied, bays
    for it, pi in zip(test, p):
        f = frames[it["frame"]]
        f[0] += it["label"]; f[1] += int(pi); f[2] += 1
    err = np.array([abs(t - q) for t, q, _ in frames.values()])
    bays = np.array([n for *_, n in frames.values()])
    true_tot = sum(t for t, _, _ in frames.values()); pred_tot = sum(q for _, q, _ in frames.values())
    L += ["", f"CAR COUNTS PER CAMERA FRAME ({len(frames):,} frames, {bays.mean():.0f} bays per frame on average)",
          f"  Exact count: {np.mean(err == 0):.1%} of frames;  within 1 car: {np.mean(err <= 1):.1%};  within 2: {np.mean(err <= 2):.1%}",
          f"  Mean error: {err.mean():.2f} cars per frame = {err.sum() / bays.sum():.2%} of bays "
          f"(count accuracy {1 - err.sum() / bays.sum():.2%}; pilot target 95%)",
          f"  All frames together: {pred_tot:,} cars counted vs {true_tot:,} true ({(pred_tot - true_tot) / true_tot:+.2%})",
          "", f"SPEED: {ms:.1f} ms per bay on this CPU, batch 256 (a camera frame of ~{bays.mean():.0f} bays in about "
          f"{ms * bays.mean():.0f} ms)",
          "", "Limits: one outdoor car park in Italy; the test cameras are new viewpoints of the same car park, not a new site.",
          "Bay positions are marked by hand. Speed is on a laptop CPU, not the Jetson AI box. Indoor basements (lighting,",
          "pillars, low ceilings) still need testing; we plan to film B1 at KL East Mall and hand-label frames (deck A14).",
          "Data: CNRPark+EXT, Amato et al. (2017), Expert Systems with Applications 72; licence ODbL v1.0."]
    out = "\n".join(L)
    print(out)
    Path(__file__).with_name("cv_benchmark_results.txt").write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
