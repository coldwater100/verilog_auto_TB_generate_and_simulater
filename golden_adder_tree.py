# golden_adder_tree.py
from base_golden_model import BaseGoldenModel
import math

class GoldenAdderTree(BaseGoldenModel):

    def __init__(self, params):
        super().__init__(params)

        self.INPUT_COUNT = params["INPUT_COUNT"]
        self.DATA_WIDTH  = params["DATA_WIDTH"]

        # Verilog와 동일하게 맞춘 실제 latency
        # stage0 combinational + stage1,2,3 registers + reset alignment
        self.latency = math.ceil(math.log2(self.INPUT_COUNT)) + 2

        # Verilog FINAL_WIDTH
        self.FINAL_WIDTH = self.DATA_WIDTH + math.ceil(math.log2(self.INPUT_COUNT))

        # FIFO 초기화
        self.queue = [None] * self.latency

    def reset(self):
        self.queue = [None] * self.latency

    def compute_raw(self, inputs: dict):
        flat = inputs["i_data"]

        if flat is None:
            return None

        mask = (1 << self.DATA_WIDTH) - 1
        total = 0

        for i in range(self.INPUT_COUNT):
            part = (flat >> (i * self.DATA_WIDTH)) & mask
            total += part

        return total
