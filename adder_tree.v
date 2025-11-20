/**
 * @module generic_adder_tree
 * @brief 'INPUT_COUNT'에 따라 자동으로 파이프라인 단을 생성하는
 * 파라미터화된 Adder Tree (SystemVerilog 필요)
 *
 * @param INPUT_COUNT - 입력 개수 (반드시 2의 거듭제곱: 4, 8, 16, ...)
 * @param DATA_WIDTH  - 각 입력의 비트 폭
 */
 
module generic_adder_tree #(

    // 입력 데이터 개수
    parameter INPUT_COUNT = 8,
    
    // 각 입력 데이터의 비트 폭
    parameter DATA_WIDTH  = 16
    
) (
    input clk,
    input rst_n,

    // 2D 배열 입력 포트
    input [INPUT_COUNT-1:0] [DATA_WIDTH-1:0] i_data,

    // 최종 출력
    output reg [$clog2(INPUT_COUNT)+DATA_WIDTH-1:0] o_sum
);

    // 1. 파라미터 자동 계산
    
    // 트리 단계 수 (예: 8입력 -> $clog2(8) = 3단계)
    localparam STAGES = $clog2(INPUT_COUNT); 
    
    // 최종 출력 비트 폭 (예: 16bit + 3 = 19bit)
    localparam FINAL_WIDTH = DATA_WIDTH + STAGES;

    // 2. 파이프라인 중간 단계 변수
    
    // Stage 0 (입력단)은 조합 논리(wire)로 선언
    wire [FINAL_WIDTH-1:0] sums_stage_0 [0:INPUT_COUNT-1];

    // Stage 1 ~ Stage (STAGES-1)은 순차 논리(reg)로 선언
    // (8입력(STAGES=3)의 경우, sums_pipe_reg[1]과 sums[2]가 생성됨)
    // (STAGES=1, 즉 2입력인 경우 이 배열은 생성되지 않음)
    reg [FINAL_WIDTH-1:0] sums_pipe_reg [1:STAGES-1][0:INPUT_COUNT-1];

    // 3. 하드웨어 생성
    genvar s, i; // generate 루프용 변수

    generate
        // 0단계: 입력 연결 (조합 논리)
        // always_comb -> generate for + assign
        for (i = 0; i < INPUT_COUNT; i = i + 1) begin : INPUT_PADDING
            // (FINAL_WIDTH - DATA_WIDTH) 만큼 0으로 채워 비트 폭 맞춤
            assign sums_stage_0[i] = {{(FINAL_WIDTH-DATA_WIDTH){1'b0}}, i_data[i]};
        end

        // 파이프라인 1단계 ~ 마지막(STAGES) 단계 생성
        for (s = 0; s < STAGES; s = s + 1) begin : STAGE_LOOP
            
            // 현재 단계(s)에서 필요한 덧셈기(Adder)의 수
            localparam NUM_ADDERS = INPUT_COUNT / (2**(s+1));

            for (i = 0; i < NUM_ADDERS; i = i + 1) begin : ADDER_LOOP
                
                // 현 단계 덧셈기의 입력을 명확히 선택
                wire [FINAL_WIDTH-1:0] in_a, in_b;
                
                // s=0 (첫 단계)이면 입력(sums_stage_0)에서 가져옴
                // s>0 (중간 단계)이면 이전 파이프라인 레지스터(sums_pipe_reg[s])에서 가져옴
                assign in_a = (s == 0) ? sums_stage_0[2*i]   : sums_pipe_reg[s][2*i];
                assign in_b = (s == 0) ? sums_stage_0[2*i+1] : sums_pipe_reg[s][2*i+1];
                
                
                // 마지막 단계(s == STAGES-1)인 경우
                // 출력을 'o_sum' 레지스터에 바로 저장
                if (s == STAGES - 1) begin : FINAL_STAGE_REG
                    
                    always @(posedge clk or negedge rst_n) begin
                        if (!rst_n) begin
                            o_sum <= 0;
                        end else begin
                            // 덧셈 결과를 최종 출력 레지스터에 저장
                            o_sum <= in_a + in_b;
                        end
                    end
                    
                // 중간 단계인 경우
                // 출력을 다음 단계 'sums_pipe_reg' 배열에 저장
                end else begin : INTERMEDIATE_STAGE_REG
                
                    always @(posedge clk or negedge rst_n) begin
                        if (!rst_n) begin
                            sums_pipe_reg[s+1][i] <= 0;
                        end else begin
                            // 덧셈 결과를 다음 파이프라인 레지스터에 저장
                            sums_pipe_reg[s+1][i] <= in_a + in_b;
                        end
                    end
                end // if-else
            end // ADDER_LOOP
        end // STAGE_LOOP
    endgenerate

endmodule