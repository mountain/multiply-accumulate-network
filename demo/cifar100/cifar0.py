import torch as th
import torch.nn.functional as F
import torch.nn as nn

from manet.nn.model import MNISTModel
from torch import Tensor
from typing import TypeVar, Tuple


U = TypeVar('U', bound='Unit')


class LNon(nn.Module):
    def __init__(self: U,
                 steps: int = 3,
                 length: float = 0.33333,
                 points: int = 5,
                 ) -> None:
        super().__init__()

        self.num_steps = steps
        self.step_length = length
        self.num_points = points

        self.theta = nn.Parameter(
            th.linspace(0, 2 * th.pi, points).view(1, 1, points)
        )
        self.velocity = nn.Parameter(
            th.linspace(0, 1, points).view(1, 1, points)
        )
        self.channel_transform = nn.Parameter(
            th.normal(0, 1, (1, 1, 1))
        )
        self.spatio_transform = nn.Parameter(
            th.normal(0, 1, (1, 1, 1))
        )

    def accessor(self: U,
                 data: Tensor,
                 ) -> Tuple[Tensor, Tensor, Tensor]:

        index = th.sigmoid(data) * self.num_points

        bgn = index.floor().long()
        bgn = bgn * (bgn >= 0)
        bgn = bgn * (bgn <= self.num_points - 2) + (bgn - 1) * (bgn > self.num_points - 2)
        bgn = bgn * (bgn <= self.num_points - 2) + (bgn - 1) * (bgn > self.num_points - 2)
        end = bgn + 1

        return index, bgn, end

    def access(self: U,
               memory: Tensor,
               accessor: Tuple[Tensor, Tensor, Tensor]
               ) -> Tensor:

        index, bgn, end = accessor
        pos = index - bgn
        memory = memory.flatten(0)
        return (1 - pos) * memory[bgn] + pos * memory[end]

    def step(self: U,
             data: Tensor
             ) -> Tensor:

        accessor = self.accessor(data)
        theta = self.access(self.theta, accessor)
        velo = self.access(self.velocity, accessor)

        # by the flow equation of the arithmetic expression geometry
        ds = velo * self.step_length
        dx = ds * th.cos(theta)
        dy = ds * th.sin(theta)
        val = data * (1 + dy) + dx
        return val

    def forward(self: U,
                data: Tensor
                ) -> Tensor:
        shape = data.size()
        data = data.flatten(1)
        data = data.contiguous()
        data = data.view(-1, 1, 1)

        data = th.permute(data, [0, 2, 1]).reshape(-1, 1)
        data = th.matmul(data, self.channel_transform)
        # data = data * self.channel_transform
        data = data.view(-1, 1, 1)

        for ix in range(self.num_steps):
            data = self.step(data)

        data = th.permute(data, [0, 2, 1]).reshape(-1, 1)
        data = th.matmul(data, self.spatio_transform)
        # data = data * self.spatio_transform
        data = data.view(-1, 1, 1)

        return data.view(*shape)


class Cifar0(MNISTModel):
    def __init__(self):
        super().__init__()
        self.conv0 = nn.Conv2d(3, 25, kernel_size=7, padding=3)
        self.lnon0 = LNon(steps=1, length=1, points=2)
        self.conv1 = nn.Conv2d(25, 125, kernel_size=3, padding=1)
        self.lnon1 = LNon(steps=1, length=1, points=2)
        self.conv2 = nn.Conv2d(125, 125, kernel_size=1, padding=0)
        self.lnon2 = LNon(steps=1, length=1, points=2)
        self.conv3 = nn.Conv2d(125, 125, kernel_size=1, padding=0)
        self.lnon3 = LNon(steps=1, length=1, points=2)
        self.fc = nn.Linear(125 * 9, 100)

    def forward(self, x):
        x = self.conv0(x)
        x = self.lnon0(x)
        x = F.max_pool2d(x, 2)
        x = self.conv1(x)
        x = self.lnon1(x)
        x = F.max_pool2d(x, 2)
        x = self.conv2(x)
        x = self.lnon2(x)
        x = F.max_pool2d(x, 2)
        x = self.conv3(x)
        x = self.lnon3(x)
        x = x.flatten(1)
        x = self.fc(x)
        x = F.log_softmax(x, dim=1)
        return x


def _model_():
    return Cifar0()
