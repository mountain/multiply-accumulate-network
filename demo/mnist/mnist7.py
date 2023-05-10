import torch as th
import lightning as pl

from torch import nn
from torch.nn import functional as F

from manet.mac import Reshape
# from torchvision.ops import MLP
from manet.mac import MLP, MacMatrixUnit


class MNModel7(pl.LightningModule):
    def __init__(self, learning_rate=1e-3):
        super().__init__()
        self.learning_rate = 1e-3
        self.counter = 0
        self.labeled_loss = 0
        self.labeled_correct = 0
        self.recognizer = nn.Sequential(
            nn.Conv2d(1, 3, kernel_size=5, padding=2),
            MLP(1, [1], mac_unit=MacMatrixUnit),
            Reshape(3, 28, 28),
            nn.MaxPool2d(2),
            nn.Conv2d(3, 6, kernel_size=5, padding=2),
            MLP(1, [1], mac_unit=MacMatrixUnit),
            Reshape(6, 14, 14),
            nn.MaxPool2d(2),
            nn.Conv2d(6, 12, kernel_size=5, padding=2),
            MLP(1, [1], mac_unit=MacMatrixUnit),
            Reshape(12, 7, 7),
            nn.MaxPool2d(2),
            nn.Conv2d(12, 24, kernel_size=3, padding=1),
            MLP(1, [1], mac_unit=MacMatrixUnit),
            Reshape(24, 3, 3),
            nn.MaxPool2d(2),
            Reshape(24, 1),
            MLP(24, [10], mac_unit=MacMatrixUnit, mac_steps=6),
            nn.LogSoftmax(dim=1)
        )

    def forward(self, x):
        return self.recognizer(x)

    def configure_optimizers(self):
        return th.optim.Adam(self.parameters(), lr=self.learning_rate)

    def training_step(self, train_batch, batch_idx):
        x, y = train_batch
        x = x.view(-1, 1, 28, 28)
        z = self(x)
        loss = F.nll_loss(z, y)
        self.log('train_loss', loss, prog_bar=True)
        return loss

    def validation_step(self, val_batch, batch_idx):
        x, y = val_batch
        x = x.view(-1, 1, 28, 28)
        z = self(x)
        loss = F.nll_loss(z, y)
        self.log('val_loss', loss, prog_bar=True)
        pred = z.data.max(1, keepdim=True)[1]
        correct = pred.eq(y.data.view_as(pred)).sum() / y.size()[0]
        self.log('correct', correct, prog_bar=True)
        self.labeled_loss += loss.item() * y.size()[0]
        self.labeled_correct += correct.item() * y.size()[0]
        self.counter += y.size()[0]

    def test_step(self, test_batch, batch_idx):
        x, y = test_batch
        x = x.view(-1, 1, 28, 28)
        z = self(x)
        pred = z.data.max(1, keepdim=True)[1]
        correct = pred.eq(y.data.view_as(pred)).sum() / y.size()[0]
        self.log('correct', correct, prog_bar=True)

    def on_save_checkpoint(self, checkpoint) -> None:
        import pickle, glob, os

        correct = self.labeled_correct / self.counter
        loss = self.labeled_loss / self.counter
        record = '%2.5f-%03d-%1.5f.ckpt' % (correct, checkpoint['epoch'], loss)
        fname = 'best-%s' % record
        with open(fname, 'bw') as f:
            pickle.dump(checkpoint, f)
        # for ix, ckpt in enumerate(sorted(glob.glob('best-*.ckpt'), reverse=True)):
        #     if ix > 5:
        #         os.unlink(ckpt)

        self.counter = 0
        self.labeled_loss = 0
        self.labeled_correct = 0


def _model_():
    return MNModel7()
