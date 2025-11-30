# base_golden_model.py
import math

class BaseGoldenModel:
    """
    모든 Golden Model이 공통으로 사용하는 기반 클래스
    - latency 처리
    - reset 처리
    - X(None) 처리
    - FINAL_WIDTH 계산은 자식이 설정하거나 params로 자동 계산
    """

    def __init__(self, params: dict):
        self.params = params

        # 자식 클래스에서 self.latency, self.FINAL_WIDTH 설정 안 하면 자동 계산
        INPUT_COUNT = params["INPUT_COUNT"]
        DATA_WIDTH  = params["DATA_WIDTH"]

        # 기본 latency = stage0 조합 1 + stage_reg log2(N)
        self.latency = 1 + math.ceil(math.log2(INPUT_COUNT))

        self.FINAL_WIDTH = DATA_WIDTH + math.ceil(math.log2(INPUT_COUNT))

        # latency FIFO
        self.queue = [None] * self.latency

    # --------------------------------------------------------------
    def reset(self):
        self.queue = [None] * self.latency

    # --------------------------------------------------------------
    def compute_raw(self, inputs: dict):
        """
        자식 클래스에서 구현해야 함.
        inputs: {"port": int or None}
        return: result(int) or None(X)
        """
        raise NotImplementedError("compute_raw() must be implemented in subclass")

    # --------------------------------------------------------------
    def step(self, inputs: dict):
        """
        1) raw값 계산
        2) FIFO로 latency 적용
        3) FIFO front를 output으로 반환
        """
        raw = self.compute_raw(inputs)

        # latency FIFO shift
        self.queue.pop(0)
        self.queue.append(raw)

        # FIFO front가 현재 cycle output
        return {"o_sum": self.queue[0]}
