import numpy as np
import torch as th
import torch.nn as nn
import torch.nn.functional as F

from torch import Tensor, device, dtype
from typing import List, TypeVar, Tuple, Optional, Union
from torch.nn import Module


T = TypeVar('T', bound='MacUnit')


def _exchangeable_multiplier_(factor1: int, factor2: int) -> Tuple[int, int, int]:
    # this is the normal setting
    # return factor2, factor1

    # in this setting, the size of parameters can be reduced dramatically
    # but the performance may be worse, need to be tested more
    lcm = np.lcm(factor1, factor2)
    return lcm, lcm // factor1, lcm // factor2


class MacUnit(nn.Module):
    def __init__(self: T,
                 in_channels: int,
                 out_channels: int,
                 in_spatio_dims: int = 1,
                 out_spatio_dims: int = 1,
                 num_steps: int = 5,
                 num_points: int = 5,
                 ) -> None:

        super().__init__()

        # the hyper-parameters
        self.num_steps = num_steps
        self.num_points = num_points
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.in_spatio_dims = in_spatio_dims
        self.out_spatio_dims = out_spatio_dims

        # the constant tensors
        channel_dims, self.in_channels_factor, self.out_channels_factor = _exchangeable_multiplier_(in_channels, out_channels)
        spatio_dims, self.in_spatio_factor, self.out_spatio_factor = _exchangeable_multiplier_(in_spatio_dims, out_spatio_dims)
        self.dims = channel_dims * spatio_dims

        # the learnable parameters which govern the MAC unit
        self.angles = nn.Parameter(
            th.linspace(0, 2 * th.pi, num_points).view(1, 1, num_points)
        )
        self.velocity = nn.Parameter(
            th.linspace(0, 1, num_points).view(1, 1, num_points)
        )
        self.weight = nn.Parameter(
            th.normal(0, 1, (1, channel_dims, spatio_dims))
        )
        self.attention = nn.Parameter(
            th.normal(0, 1, (1, channel_dims, spatio_dims))
        )

        self.alpha = nn.Parameter(th.normal(0, 1, (1, channel_dims, spatio_dims)))
        self.beta = nn.Parameter(th.normal(0, 1, (1, channel_dims, spatio_dims)))

    def accessor(self: T,
                 data: Tensor,
                 ) -> Tuple[Tensor, Tensor, Tensor]:

        # calculate the index of the accessor
        index = th.sigmoid(data * self.alpha + self.beta) * self.num_points
        bgn = index.floor().long()
        end = (index + 1).floor().long()
        bgn = (bgn * (bgn + 1 < self.num_points) + (bgn - 1) * (bgn + 1 >= self.num_points)) * (bgn >= 0)
        end = (end * (end < self.num_points) + (end - 1) * (end == self.num_points)) * (end >= 0)

        return index, bgn, end

    def access(self: T,
               memory: Tensor,
               accessor: Tuple[Tensor, Tensor, Tensor]
               ) -> Tensor:

        index, bgn, end = accessor
        pos = index - bgn
        memory = memory.flatten(0)
        return (1 - pos) * memory[bgn] + pos * memory[end]

    def step(self: T,
             data: Tensor
             ) -> Tensor:

        accessor = self.accessor(data)
        velo = self.access(self.velocity, accessor)
        angels = self.access(self.angles, accessor)

        # by the flow equation of the arithmetic expression geometry
        return velo * th.cos(angels) + data * velo * th.sin(angels)

    def forward(self: T,
                data: Tensor
                ) -> Tensor:

        data = data.expand_as(self.weight) * self.weight
        for ix in range(self.num_steps):
            data = data + self.step(data) / self.num_steps
        data = data * self.attention
        data = data.view(-1, self.out_channels_factor, self.out_channels, self.out_spatio_factor, self.out_spatio_dims)
        return th.sum(data, dim=(1, 3))


class MLP(nn.Sequential):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: List[int],
        spatio_dims: int  = 1
    ):
        layers = []
        in_dim = in_channels
        for hidden_dim in hidden_channels:
            layers.append(MacUnit(in_dim, hidden_dim,
                in_spatio_dims=spatio_dims, out_spatio_dims=spatio_dims))
            in_dim = hidden_dim
        layers.append(nn.Flatten())
        super().__init__(*layers)


class Reshape(nn.Module):
    def __init__(self, *shape):
        super().__init__()
        self.shape = shape

    def forward(self, x):
        return x.view(-1, *self.shape)
