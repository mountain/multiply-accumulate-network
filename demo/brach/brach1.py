import torch as th

from manet.aeg.flow import LearnableFunction
from demo.brach.model import TraceNet


class BRModel1(TraceNet):
    def __init__(self):
        super().__init__()
        self.lf = LearnableFunction(in_channel=3, out_channel=1)

    def init(self, width, x, y):
        pass

    def trace(self, width, x, y):
        return self.lf(th.cat((x, y, width), dim=1).view(-1, 3, 1))


def _model_():
    return BRModel1()
