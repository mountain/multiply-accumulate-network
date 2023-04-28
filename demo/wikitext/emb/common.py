import os
import pickle
import glob

import torch as th
import torch.nn as nn
import lightning as pl

from typing import Dict, Any


class EmbeddingModel(pl.LightningModule):
    def __init__(self):
        super().__init__()

        vname = 'datasets/vocabulary.txt'
        with open(vname) as f:
            self.vocabulary = list([ln.strip() for ln in f if len(ln.strip()) > 0])
        with open(vname) as f:
            self.dictionary = dict({ln.strip(): ix for ix, ln in enumerate(f) if len(ln.strip()) > 0})
            self.dictionary[''] = 0
        self.word_count = len(self.vocabulary)

        self.embedding = nn.Parameter(th.normal(0, 1, (self.word_count,)))

        self.labeled_loss = None

    def log_messages(self, key, loss_rel, loss_emb, loss_amb, loss):
        self.log(key, loss, prog_bar=True, batch_size=64)
        self.log('loss_rel', loss_rel, prog_bar=True, batch_size=64)
        self.log('loss_emb', loss_emb, prog_bar=True, batch_size=64)
        self.log('loss_amb', loss_amb, prog_bar=True, batch_size=64)
        self.log('max', self.embedding.max().item(), prog_bar=True, batch_size=64)
        self.log('min', self.embedding.min().item(), prog_bar=True, batch_size=64)
        self.log('mean', self.embedding.mean().item(), prog_bar=True, batch_size=64)
        self.log('std', th.std(self.embedding).item(), prog_bar=True, batch_size=64)

    def configure_optimizers(self):
        optimizer = th.optim.Adam(self.parameters(), lr=1e-3)
        return optimizer

    def forward(self, x):
        raise NotImplementedError()

    def step(self, key, batch):
        raise NotImplementedError()

    def training_step(self, train_batch, batch_idx):
        return self.step('train', train_batch)

    def validation_step(self, val_batch, batch_idx):
        self.labeled_loss = self.step('valid', val_batch)

    def test_step(self, test_batch, batch_idx):
        self.step('test', test_batch)

    def on_save_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        fname = 'best-%0.15f-%d.ckpt' % (self.labeled_loss, checkpoint['epoch'])
        with open(fname, 'bw') as f:
            pickle.dump(checkpoint, f)
        for ix, ckpt in enumerate(sorted(glob.glob('best-*.ckpt'))):
            if ix > 2:
                os.unlink(ckpt)
