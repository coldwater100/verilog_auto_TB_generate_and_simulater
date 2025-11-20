`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 11/04/2025 08:50:28 PM
// Design Name: 
// Module Name: mux
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


// (파일: mux.v)
// 파라미터화된 순차 논리(Synchronous) MUX 모듈
// (오직 clk의 posedge에서만 동작하며, 동기식 리셋을 사용)

module mux #(
    // --- 1. "변수" (파라미터) 정의 ---
    parameter INPUT_COUNT = 8,  // MUX 입력 개수 (기본값: 8-to-1)
    parameter DATA_WIDTH  = 32  // 데이터 비트 수 (기본값: 32bit)
)(
    // --- 2. 포트(Port) 정의 ---
    input wire clk,             // 클럭 신호
    input wire rst_n,           // 리셋 신호 (Active-low: 0일 때 리셋)

    // 입력 데이터 포트
    // (INPUT_COUNT * DATA_WIDTH) 크기의 1D 버스
    input wire [INPUT_COUNT * DATA_WIDTH - 1 : 0] data_in,
    
    // 입력 선택 신호 포트
    // $clog2 함수가 필요한 비트 수를 "자동으로 계산"
    // (예: INPUT_COUNT=8 -> $clog2(8) = 3 -> sel[2:0])
    input wire [$clog2(INPUT_COUNT) - 1 : 0] sel, 

    // 출력 포트
    output reg [DATA_WIDTH - 1 : 0] data_out
);

    // --- 3. MUX 로직 구현 (동기식) ---
    
    // "clk" 신호가 상승할 때(posedge) "만" 이 블록을 실행합니다.
    always @(posedge clk) begin
        
        // 동기식 리셋 (Synchronous Reset)
        // clk이 상승하는 순간에 rst_n 신호가 0인지 검사합니다.
        if (!rst_n) begin
            data_out <= {DATA_WIDTH{1'b0}};
        end
        else begin
            // 정상 동작 (클럭이 뛸 때):
            // 'sel' 신호에 해당하는 'data_in'의 "조각"을 선택하여
            // 'data_out' 레지스터에 "저장"합니다.
            
            // Verilog의 "Indexed Part-Select" (배열 슬라이싱) 문법:
            // data_in[ (시작 비트 인덱스) +: (선택할 비트 개수) ]
            
            data_out <= data_in[ (sel * DATA_WIDTH) +: DATA_WIDTH ];
        end
    end

endmodule
