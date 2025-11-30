from base_golden_model import BaseGoldenModel

class GoldenMux(BaseGoldenModel):
    """
    Simple latency-only golden model for parameterized synchronous MUX.
    - RTL internal structure is NOT emulated.
    - Only latency and functional mapping are considered.
    """

    def __init__(self, params):
        super().__init__(params)

        self.INPUT_COUNT = params["INPUT_COUNT"]
        self.DATA_WIDTH  = params["DATA_WIDTH"]

        # MUX는 1-cycle latency
        self.latency = 1

        # 파이프라인 버퍼 (None은 아직 출력 불가 → x)
        self.pipe = [None] * self.latency

        # 리셋 출력값 = 0
        self.zero_value = 0

    # ---------------------------------------------------------
    # reset
    # ---------------------------------------------------------
    def reset(self):
        """Reset pipeline to zero output"""
        self.pipe = [self.zero_value] * self.latency

    # ---------------------------------------------------------
    # 단순 슬라이싱: data_in(1D hex) → 선택 데이터 추출
    # ---------------------------------------------------------
    def _select_value(self, data_in_int, sel):
        """
        data_in_int: packed integer
        sel: index
        """

        if sel < 0 or sel >= self.INPUT_COUNT:
            return 0

        mask = (1 << self.DATA_WIDTH) - 1
        return (data_in_int >> (sel * self.DATA_WIDTH)) & mask

    # ---------------------------------------------------------
    # step
    # ---------------------------------------------------------
    def step(self, inputs):
        """
        inputs = {
            "rst_n": 0 or 1,
            "data_in": <int>,
            "sel": <int>
        }
        """
        rst_n = inputs.get("rst_n", 1)
        data_in = inputs["data_in"]
        sel = inputs["sel"]

        # 리셋이면 이번 cycle 입력은 '0' 사용
        if rst_n == 0:
            next_val = self.zero_value
        else:
            next_val = self._select_value(data_in, sel)

        # 이번 사이클 출력
        out_val = self.pipe[0]

        # 없습니다 → x 출력
        if out_val is None:
            out_val = "x"

        # 파이프라인 밀기
        self.pipe[0] = next_val

        return {"data_out": out_val}
