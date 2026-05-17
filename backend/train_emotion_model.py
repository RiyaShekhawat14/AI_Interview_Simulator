import copy
import os
from pathlib import Path

os.environ["TORCH_HOME"] = "./torch_cache"

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms

DATASET_ROOT = Path("dataset")
TRAIN_DIR = DATASET_ROOT / "train"
TEST_DIR = DATASET_ROOT / "test"
OUTPUT_PATH = Path(os.getenv("EMOTION_OUTPUT_PATH", "backend/models/best_model.pth"))
BASE_CHECKPOINT = Path(os.getenv("EMOTION_BASE_CHECKPOINT", "backend/models/best_model.pth"))
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

BATCH_SIZE = int(os.getenv("EMOTION_BATCH_SIZE", "32"))
EPOCHS = int(os.getenv("EMOTION_EPOCHS", "12"))
LEARNING_RATE = float(os.getenv("EMOTION_LR", "3e-4"))
WEIGHT_DECAY = float(os.getenv("EMOTION_WEIGHT_DECAY", "1e-4"))
MAX_TRAIN_SAMPLES = int(os.getenv("EMOTION_MAX_TRAIN_SAMPLES", "0"))
MAX_TEST_SAMPLES = int(os.getenv("EMOTION_MAX_TEST_SAMPLES", "0"))


def build_transforms():
    train_tfms = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(12),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    test_tfms = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    return train_tfms, test_tfms


def build_loaders():
    train_tfms, test_tfms = build_transforms()
    train_ds = datasets.ImageFolder(TRAIN_DIR, transform=train_tfms)
    test_ds = datasets.ImageFolder(TEST_DIR, transform=test_tfms)

    if MAX_TRAIN_SAMPLES > 0:
        indices = torch.randperm(len(train_ds))[: min(MAX_TRAIN_SAMPLES, len(train_ds))].tolist()
        train_ds = Subset(train_ds, indices)
    if MAX_TEST_SAMPLES > 0:
        indices = torch.randperm(len(test_ds))[: min(MAX_TEST_SAMPLES, len(test_ds))].tolist()
        test_ds = Subset(test_ds, indices)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    return train_ds, test_ds, train_loader, test_loader


def build_model(num_classes: int):
    model = models.resnet18(weights=None)
    for parameter in model.parameters():
        parameter.requires_grad = False

    for parameter in model.layer4.parameters():
        parameter.requires_grad = True

    model.fc = nn.Sequential(
        nn.Linear(model.fc.in_features, 128),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(128, num_classes),
    )

    if BASE_CHECKPOINT.exists():
        state = torch.load(BASE_CHECKPOINT, map_location=DEVICE)
        model.load_state_dict(state, strict=False)

    return model.to(DEVICE)


def compute_class_weights(dataset):
    targets = dataset.targets if hasattr(dataset, "targets") else [dataset.dataset.targets[i] for i in dataset.indices]
    num_classes = len(dataset.classes) if hasattr(dataset, "classes") else len(dataset.dataset.classes)
    counts = torch.bincount(torch.tensor(targets), minlength=num_classes)
    weights = counts.sum().float() / counts.float().clamp_min(1)
    weights = weights / weights.sum() * len(weights)
    return weights.to(DEVICE)


def run_epoch(model, loader, criterion, optimizer=None):
    is_train = optimizer is not None
    model.train(is_train)

    total_loss = 0.0
    total_correct = 0
    total_count = 0

    for images, labels in loader:
        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        if is_train:
            optimizer.zero_grad()

        with torch.set_grad_enabled(is_train):
            logits = model(images)
            loss = criterion(logits, labels)
            if is_train:
                loss.backward()
                optimizer.step()

        total_loss += loss.item() * images.size(0)
        predictions = logits.argmax(dim=1)
        total_correct += (predictions == labels).sum().item()
        total_count += images.size(0)

    return total_loss / max(total_count, 1), total_correct / max(total_count, 1)


def main():
    if not TRAIN_DIR.exists() or not TEST_DIR.exists():
        raise SystemExit("Dataset folders not found. Expected dataset/train and dataset/test.")

    train_ds, test_ds, train_loader, test_loader = build_loaders()
    classes = train_ds.classes if hasattr(train_ds, "classes") else train_ds.dataset.classes
    model = build_model(num_classes=len(classes))
    class_weights = compute_class_weights(train_ds)

    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.05)
    optimizer = AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2)

    best_acc = 0.0
    best_state = copy.deepcopy(model.state_dict())

    print(f"Training on {DEVICE} with classes: {classes}")
    print(f"Train samples: {len(train_ds)} | Test samples: {len(test_ds)}")

    for epoch in range(1, EPOCHS + 1):
        train_loss, train_acc = run_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc = run_epoch(model, test_loader, criterion)
        scheduler.step(val_loss)

        if val_acc > best_acc:
            best_acc = val_acc
            best_state = copy.deepcopy(model.state_dict())

        print(
            f"Epoch {epoch:02d} | "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, OUTPUT_PATH)
    print(f"Saved best checkpoint to {OUTPUT_PATH} with val_acc={best_acc:.4f}")


if __name__ == "__main__":
    main()
