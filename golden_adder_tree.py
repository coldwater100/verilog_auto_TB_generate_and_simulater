# ==== Golden Model for generic_adder_tree ======================
# BaseGoldenModel 상속 없이도 사용 가능하도록 작성
# (load_golden_model는 파일 내부 클래스 하나만 있을 때 자동로드됨)

class golden_adder_tree:

    def __init__(self, params_dict):
        """
        params_dict = {
            "INPUT_COUNT": 8,
            "DATA_WIDTH": 16
        }
        """
        self.INPUT_COUNT = params_dict["INPUT_COUNT"]
        self.DATA_WIDTH = params_dict["DATA_WIDTH"]

        # 파라미터 기반 자동 계산
        self.STAGES = (self.INPUT_COUNT.bit_length() - 1)   # = clog2(INPUT_COUNT)
        self.FINAL_WIDTH = self.DATA_WIDTH + self.STAGES

        # 파이프라인 레지스터 구조 생성 (Python 리스트로)
        # sums_pipe_reg[s][i]
        #   s = 1 .. STAGES-1
        #   i = 0 .. (INPUT_COUNT / (2**(s+1))) - 1
        self.sums_pipe_reg = []
        for s in range(self.STAGES):
            if s == 0:
                # stage0은 따로 reg가 없음
                self.sums_pipe_reg.append(None)
            else:
                num_regs = self.INPUT_COUNT // (2 ** (s + 1))
                self.sums_pipe_reg.append([0] * num_regs)

        self.o_sum = 0

    # ============================================================
    # RESET: Verilog reset 타이밍 동일하게 작동
    # ============================================================
    def reset(self):
        self.o_sum = 0
        for s in range(1, self.STAGES):
            num_regs = len(self.sums_pipe_reg[s])
            self.sums_pipe_reg[s] = [0] * num_regs

    # ============================================================
    # 한 cycle 수행 (posedge clk 상황)
    # ============================================================
    def step(self, input_vals):
        """
        input_vals = {
            "i_data": <integer>
        }

        .hex 파일은 1D flat integer이므로 이를 다시 2D 배열로 변환해야 한다.
        """

        # ---- 1D -> 2D 배열 복원 -----------------------------------
        # SystemVerilog에서:
        # input [INPUT_COUNT-1:0][DATA_WIDTH-1:0] i_data
        # Python에선 리스트로 복원해야 한다.
        flat_val = input_vals["i_data"]
        i_data = []
        maskDW = (1 << self.DATA_WIDTH) - 1
        for idx in range(self.INPUT_COUNT):
            part = (flat_val >> (idx * self.DATA_WIDTH)) & maskDW
            i_data.append(part)

        # ---- Stage 0 (Zero padding) = sums_stage_0 ---------------
        sums_stage_0 = []
        for x in range(self.INPUT_COUNT):
            sums_stage_0.append(i_data[x])

        # ---- Pipeline 업데이트를 위한 새로운 stage 저장 버퍼 -----
        next_pipe = [None] * self.STAGES
        next_pipe[0] = None  # stage0 없음

        # ---- 단계별 계산 -----------------------------------------
        for s in range(self.STAGES):

            NUM_ADDERS = self.INPUT_COUNT // (2 ** (s + 1))

            for i in range(NUM_ADDERS):

                if s == 0:
                    in_a = sums_stage_0[2 * i]
                    in_b = sums_stage_0[2 * i + 1]
                else:
                    in_a = self.sums_pipe_reg[s][2 * i]
                    in_b = self.sums_pipe_reg[s][2 * i + 1]

                result = in_a + in_b

                if s == self.STAGES - 1:
                    # final stage
                    self.o_sum = result
                else:
                    if next_pipe[s + 1] is None:
                        num_regs = self.INPUT_COUNT // (2 ** (s + 2))
                        next_pipe[s + 1] = [0] * num_regs
                    next_pipe[s + 1][i] = result

        # ---- pipeline 업데이트 commit (posedge clk 효과) --------
        for s in range(1, self.STAGES):
            if next_pipe[s] is not None:
                self.sums_pipe_reg[s] = next_pipe[s]

        # ---- 출력 반환 --------------------------------------------
        return {"o_sum": self.o_sum}
