# ============================================================
# made by 이수찬(suchan lee)
#
# 작동을 위해 golden_base 필요
# 사용방법 : 프로그램과 골든모델(.py)(선택사항), 베릴로그(.v) 파일들을 같은 디렉토리에 넣고
# 예시)  python auto_vsim.py golden_model.py file1.v file2.v ... -> 이런식으로 실행하면
# 파일에서 모듈들을 읽어서 프로그램이 베릴로그 모듈들을 나열해줌
# top_module을 지정하면 top_module의 포트와 파라마터를 읽어서 자동으로 tb 생성
# 포트와 파라마터를 이용하여 자동으로 hex파일들(clk,rst를 제외한 포트 입력) 랜덤하게 생성
# vsim 결과물을 SystemVerilog 모드로 컴파일

# 골든모델(sw의 tb 역할까지 같이함)은 사람이 직접 작성. 골든 모델도 베릴로그와 같은 hex기반으로 실험함(결과 비교를 위해)
# 결과는 results/ 폴더 안에    골든모델 결과 ,TB 파일, hex파일, 시뮬 로그가 저장
# ============================================================

import importlib.util
import re
import subprocess
import sys
import os
import platform
import random
import math

# ============================================================
# Make result directory
# ============================================================
def make_result_dir():
    result_dir = "results"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        print(f"[+] Created result directory: {result_dir}")
    else:
        print(f"[+] Using existing directory: {result_dir}")
    return result_dir


# ============================================================
# Check ModelSim PATH
# ============================================================
def check_modelsim():
    system = platform.system().lower()

    def exists(cmd, checker):
        try:
            subprocess.check_output([checker, cmd], stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledError:
            return False

    if "windows" in system:
        vsim_ok = exists("vsim", "where")
        vlog_ok = exists("vlog", "where")
    else:
        vsim_ok = exists("vsim", "which")
        vlog_ok = exists("vlog", "which")

    if not vsim_ok or not vlog_ok:
        print("[ERROR] ModelSim vsim/vlog not found in PATH.")
        sys.exit(1)

    print("[+] ModelSim PATH OK.\n")


# ============================================================
# Extract module name
# ============================================================
def extract_module_name(vfile):
    text = open(vfile, "r", encoding="utf-8", errors="ignore").read()
    m = re.search(r"\bmodule\s+([a-zA-Z_][a-zA-Z0-9_]*)", text)
    if not m:
        print(f"[ERROR] Module name not found in {vfile}")
        sys.exit(1)
    return m.group(1)

# ============================================================
# Parse params
# ============================================================
def parse_parameters(vfile, module_name):

    text = open(vfile, "r", encoding="utf-8", errors="ignore").read()

    # 1) Remove comments only
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)

    params = []

    # 2) Extract module block (NO regex inside)
    m_start = text.find("module " + module_name)
    if m_start == -1:
        return params

    m_end = text.find("endmodule", m_start)
    if m_end == -1:
        m_end = len(text)

    body = text[m_start:m_end]

    # 3) Scan "parameter" token repeatedly
    search_pos = 0
    while True:
        p = body.find("parameter", search_pos)
        if p == -1:
            break

        # move cursor after "parameter"
        cur = p + len("parameter")

        # skip spaces / tabs
        while cur < len(body) and body[cur] in " \t":
            cur += 1

        # 4) find end token among  ',', ';', '\n', ')'
        candidates = []
        for sep in [",", ";", "\n", ")"]:
            s = body.find(sep, cur)
            if s != -1:
                candidates.append(s)

        if not candidates:
            break

        end = min(candidates)

        raw = body[cur:end].strip()
        # print("RAW=", raw)   # 디버깅용

        # raw 예: 
        #   "WIDTH = 8"
        #   "int SIZE = 4"
        #   "logic [7:0] X = 8'hF0"

        # 5) find '=' position manually
        eq = raw.find("=")
        if eq == -1:
            search_pos = end
            continue

        left = raw[:eq].strip()
        right = raw[eq+1:].strip()

        # remove type tokens in left
        # split by space, last token = name
        name = left.split()[-1]

        if name:     # 안전 체크
            params.append((name, right))

        # next search
        search_pos = end


    print("\nparams : ",params,"\n")
    return params


# ============================================================
# Parse ports
# ============================================================
def parse_ports(vfile, module_name):

    text = open(vfile, "r", encoding="utf-8", errors="ignore").read()

    # Extract module block (NO regex inside)
    m_start = text.find("module " + module_name)
    if m_start == -1:
        return ports

    m_end = text.find("endmodule", m_start)
    if m_end == -1:
        m_end = len(text)

    text = text[m_start:m_end]

    # 1) 라인 단위로만 분석 (정규식 X)
    ports = []

    direction_keywords = ("input", "output", "inout")

    i = 0
    N = len(text)

    while i < N:
        # 방향 찾기
        if text.startswith("input", i):
            direction = "input"
            start = i
            i += len("input")
        elif text.startswith("output", i):
            direction = "output"
            start = i
            i += len("output")
        elif text.startswith("inout", i):
            direction = "inout"
            start = i
            i += len("inout")
        else:
            i += 1
            continue

        # 2) declaration 끝 찾기
        #    → ',' OR ';' OR '\n' OR ')'
        end = i
        while end < N and text[end] not in ",;\n":
            end += 1

        full_decl = text[start:end].strip()

        # 3) name = 마지막 토큰
        tokens = full_decl.split()
        name = tokens[-1]

        ports.append({
            "dir": direction,
            "full": full_decl,
            "name": name
        })

        i = end + 1
    print("\nports : ",ports,"\n")

    return ports





# ============================================================
# Generate SystemVerilog TB to text
# ============================================================
def generate_tb_header(top, ports, params, case_id):

    tb = []

    # 1) Timescale + Module
    tb.append("`timescale 1ns / 1ps\n\n")
    tb.append(f"module tb_{top}_case{case_id};\n\n\n")

    # 2) Parameter block
    if params:
        for name, default in params:
            tb.append(f"    parameter {name} = {default};\n")
        tb.append("\n\n\n")

    # 3) Port declarations
    for p in ports:
        full = p["full"]
        name = p["name"]
        direction = p["dir"]

        # input → reg
        if direction == "input":
            # 이미 reg/wire/logic이 없다면 맨 앞에 reg 추가
            decl = full.replace("input", "").replace("wire", "").strip()
            if not any(tok in decl.split() for tok in ["reg", "wire", "logic"]):
                decl = "reg " + decl
            tb.append(f"    {decl};\n")

        # inout → reg
        elif direction == "inout":
            decl = full.replace("inout", "").strip()
            if not any(tok in decl.split() for tok in ["reg", "wire", "logic"]):
                decl = "reg " + decl
            tb.append(f"    {decl};\n")

        # output → wire
        else:
            decl = full.replace("output", "").replace("reg", "").strip()

            tokens = decl.split()
            has_type = any(tok in tokens for tok in ["reg", "wire", "logic"])

            if not has_type:
                # 타입이 없는 경우 wire 붙이기
                decl = "wire " + decl

            # output reg → "reg" 유지됨
            # output logic → "logic" 유지됨

            tb.append(f"    {decl};\n")

    tb.append("\n\n\n")

    # 4) DUT Instance — parameters
    if params:
        tb.append(f"    {top} #(\n")
        for i, (name, default) in enumerate(params):
            comma = "," if i < len(params) - 1 else ""
            tb.append(f"        .{name}({name}){comma}\n")
        tb.append(f"    ) uut (\n")
    else:
        tb.append(f"    {top} uut (\n")

    # 5) DUT Port mapping
    for i, p in enumerate(ports):
        name = p["name"]
        comma = "," if i < len(ports) - 1 else ""
        tb.append(f"        .{name} ({name}){comma}\n")

    tb.append("    );\n\n")
    # tb.append("endmodule\n")

    return "".join(tb)


# ============================================================
# gen one TB stimulus case
# ============================================================

def generate_stimulus(case_id, ports, params, cycles, clk_name, reset_name):

    input_ports  = [p["name"] for p in ports 
                    if p["dir"] == "input" and p["name"] not in (clk_name, reset_name)]
    output_ports = [p["name"] for p in ports if p["dir"] == "output"]

    stim = []

    # ===========================================
    # 글로벌 변수 생성 (TB 모듈 바로 아래에 위치)
    # ===========================================
    stim.append("\n    // Global variables for TB\n")
    stim.append("    integer fd[32];\n")      # push_back 불가 -> fixed array 사용
    stim.append("    integer fd_count = 0;\n")
    stim.append("    string fn;\n")
    stim.append("    string line;\n")
    stim.append("    integer cycle;\n\n")

    # ===========================================
    # CLOCK
    # ===========================================
    stim.append("    // ===============================================\n")
    stim.append("    // CLOCK GENERATION\n")
    stim.append("    // ===============================================\n")
    stim.append("    initial begin\n")
    stim.append(f"        {clk_name} = 0;\n")
    stim.append(f"        forever #(10/2) {clk_name} = ~{clk_name};\n")
    stim.append("    end\n\n")

    # ===========================================
    # TEST
    # ===========================================
    stim.append("    // ===============================================\n")
    stim.append(f"    // TEST STIMULUS : CASE {case_id}\n")
    stim.append("    // ===============================================\n\n")

    stim.append("    initial begin\n")
    stim.append(f"        $display(\"==== START CASE {case_id} ====\");\n\n")

    # RESET
    stim.append(f"        {reset_name} = 0;\n")
    stim.append(f"        repeat (3) @(posedge {clk_name});\n")
    stim.append(f"        {reset_name} = 1;\n")
    stim.append(f"        @(posedge {clk_name});\n\n")

    # OPEN ALL INPUT HEX FILES
    stim.append("        // ---- OPEN ALL INPUT HEX FILES ----\n")
    stim.append("        fd_count = 0;\n")

    for p in input_ports:
        stim.append(f"        fn = \"results/{p}_case{case_id}.hex\";\n")
        stim.append(f"        fd[fd_count] = $fopen(fn, \"r\");\n")
        stim.append("        if (fd[fd_count] == 0) begin\n")
        stim.append("            $display(\"ERROR: cannot open %s\", fn);\n")
        stim.append("            $finish;\n")
        stim.append("        end\n")
        stim.append("        fd_count = fd_count + 1;\n\n")

    # LOOP
    stim.append(f"        for (cycle = 0; cycle < {cycles}; cycle++) begin\n")
    stim.append(f"            @(posedge {clk_name});\n\n")

    # READ INPUTS
    stim.append("            // ---- Read one value per input port ----\n")
    for idx, p in enumerate(input_ports):
        stim.append(f"            if ($fgets(line, fd[{idx}])) begin\n")
        stim.append(f"                $sscanf(line, \"%h\", {p});\n")
        stim.append("            end\n\n")

    # PRINT OUTPUTS
    stim.append("            // ---- Display outputs ----\n")
    stim.append("            $display(\"[Cycle %0d]\", cycle);\n")
    for p in output_ports:
        stim.append(f"            $display(\"   {p} = %h\", {p});\n")

    stim.append("        end\n\n")

    # CLOSE FILES
    stim.append("        // ---- Close files ----\n")
    stim.append("        for (int i = 0; i < fd_count; i++) begin\n")
    stim.append("            $fclose(fd[i]);\n")
    stim.append("        end\n\n")

    stim.append("        $finish;\n")
    stim.append("    end\n")
    stim.append("endmodule\n")

    return "".join(stim)




# ============================================================
# build one whole tb case
# ============================================================
def build_tb_case(top, ports, params, case_id,cycles,clk_name,reset_name):

    header = generate_tb_header(top, ports, params, case_id)
    header = header.replace("{CASE_ID}", str(case_id))
    
    stim = generate_stimulus(case_id, ports, params,cycles,clk_name,reset_name)

    return header + stim


# ============================================================
# save SystemVerilog TB case into result directory
# ============================================================

def save_tb_case(top, tb_text, case_id):
    os.makedirs("results", exist_ok=True)
    path = f"results/tb_{top}_case{case_id}.sv"
    with open(path, "w", encoding="utf-8") as f:
        f.write(tb_text)
    print("[+] Saved", path)
    return path



# ============================================================
# Run command
# ============================================================
def run_cmd(cmd, log_path=None):
    print("[CMD]", " ".join(cmd))
    if log_path:
        with open(log_path, "a", encoding="utf-8", errors="ignore") as f:
            subprocess.run(cmd, stdout=f, stderr=f)
    else:
        subprocess.run(cmd)




# -----------------------------
# clog2 지원
# -----------------------------
def clog2(x):
    return math.ceil(math.log2(x))

# -----------------------------
# 포트 폭 계산
# -----------------------------
def calc_width(full_port, params_dict):
    """
    1D/2D width 계산 지원.
    예) [7:0][31:0] → 8 * 32 = 256 bit
    """
    brackets = re.findall(r"\[(.*?)\]", full_port)
    if not brackets:
        return 1

    env = {}
    env.update(params_dict)
    env["clog2"] = clog2

    total_width = 1

    for b in brackets:
        b = b.replace("$clog2", "clog2")
        hi, lo = [x.strip() for x in b.split(":")]
        hi = eval(hi, {}, env)
        lo = eval(lo, {}, env)

        w = abs(hi - lo) + 1
        total_width *= w

    return total_width

# ============================================================
# Generate HEX inputs for each case
# ============================================================
def generate_hex_inputs(ports, params, case_id, cycles, result_dir):
    """
    Generate hex input vectors based on port bit-width.
    clk / rst_n 제외한 모든 input port에 대해 생성
    """

    # 파라미터 dict 변환
    params_dict = {k:int(v) for (k,v) in params}

    # 입력 포트 필터링
    input_ports = [
        p for p in ports
        if p["dir"] == "input" and p["name"] not in ("clk", "rst_n")
    ]

    for p in input_ports:
        port_name = p["name"]
        full_decl = p["full"]

        # --- 포트 비트폭 계산 ---
        width = calc_width(full_decl, params_dict)

        # 필요한 hex 문자 수 (4bit = hex 1글자)
        hex_digits = (width + 3)//4

        # 출력 파일 생성
        hex_path = os.path.join(result_dir, f"{port_name}_case{case_id}.hex")
        with open(hex_path, "w") as f:
            for _ in range(cycles):
                val = random.getrandbits(width)
                f.write(f"{val:0{hex_digits}x}\n")

        print(f"[+] Generated HEX: {hex_path} (width {width} bits, {hex_digits} hex digits)")

# ============================================================
# 골든모델 로드
# ============================================================

def load_golden_model(golden_file_path):

    if not os.path.exists(golden_file_path):
        raise FileNotFoundError(f"Golden model file not found: {golden_file_path}")

    spec = importlib.util.spec_from_file_location("golden_module", golden_file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    candidate = None

    for attr in dir(module):
        obj = getattr(module, attr)

        # 오직 '클래스'만 허용
        if isinstance(obj, type):
            if candidate is not None:
                raise RuntimeError(f"Multiple classes found in {golden_file_path}")
            candidate = obj

    if candidate is None:
        raise RuntimeError(f"No class found in {golden_file_path}")

    return candidate




# ============================================================
# 골든모델 실행
# ============================================================
def run_golden_model(GoldenClass, params_dict, input_hex_map, save_path, cycles):
    """
    GoldenClass     : load_golden_model()이 리턴한 '클래스'
    params_dict     : {"INPUT_COUNT":8, "DATA_WIDTH":16} 등 파라미터
    input_hex_map   : {"i_data": ".../i_data_case0.hex", "sel":"..."}
    save_path       : 저장할 golden 출력 파일
    cycles          : 반복 횟수
    """

    # GoldenClass 인스턴스 생성
    golden = GoldenClass(params_dict)

    # 입력 파일들 오픈
    fds = {}
    for port, filepath in input_hex_map.items():
        fds[port] = open(filepath, "r")

    # 출력 파일 오픈
    fo = open(save_path, "w")

    # 골든모델 초기화
    golden.reset()

    # ---- 사이클 반복 ----
    for cycle in range(cycles):
        input_vals = {}

        # 모든 입력 포트에 대해 hex 읽기
        for port, fd in fds.items():
            line = fd.readline()

            if not line:          # EOF
                val = 0
            else:
                line = line.strip()
                if line == "":
                    val = 0
                else:
                    val = int(line, 16)

            input_vals[port] = val

        # 한 사이클 실행
        out_vals = golden.step(input_vals)

        # 출력 기록(JSON 비슷한 형태)
        fo.write(f"Cycle {cycle}: {out_vals}\n")

    # ---- 파일 닫기 ----
    for fd in fds.values():
        fd.close()
    fo.close()


# ============================================================
# Main
# ============================================================
def main():
    if len(sys.argv) < 2:
        print("Usage: python auto_vsim.py(not mandatory) golden_model.py file1.v file2.v ...")
        sys.exit(1)
    golden_file=None

    if sys.argv[1].endswith(".py"):
        golden_file = sys.argv[1]

        vfiles = sys.argv[2:]
    else:
        vfiles = sys.argv[1:]

    check_modelsim()
    result_dir = make_result_dir()

    # Extract module names
    print("\n=== Detected Modules ===")
    module_map = {vf: extract_module_name(vf) for vf in vfiles}
    for i, (vf, mn) in enumerate(module_map.items(), 1):
        print(f"{i}) {mn:20s}  (from {vf})")

    choice = int(input("\nSelect TOP module (number): "))
    if not 1 <= choice <= len(vfiles):
        print("Invalid selection")
        sys.exit(1)

    top_file = list(module_map.keys())[choice - 1]
    top_module = module_map[top_file]
    print(f"\n[+] Selected TOP module: {top_module}\n")

    ports = parse_ports(top_file, top_module)
    params=parse_parameters(top_file,top_module)

    cases_count = int(input("\nhow many cases do you want? (number): "))
    clk_name=str(input("\ntype clk name :"))
    reset_name=str(input("type reset name : "))
    cycles=int(input("type cycle count : "))
    tb_files=[]
    for case_id in range(cases_count):
        tb_text = build_tb_case(top_module, ports, params, case_id, cycles,clk_name,reset_name)
        tb_file = save_tb_case(top_module, tb_text, case_id)
        tb_files.append(tb_file)
        generate_hex_inputs(ports, params,case_id, cycles, result_dir)

    # ============================================================
    # ModelSim 작업 공간 생성
    # ============================================================
    work_dir = os.path.join(result_dir, "work")
    run_cmd(["vlib", work_dir])
    run_cmd(["vmap", "work", work_dir])

    # ============================================================
    # RTL 컴파일
    # ============================================================
    for vf in vfiles:
        run_cmd(["vlog", "-sv", vf])

    # ============================================================
    # 각 케이스별 TB 컴파일 → 시뮬레이션
    # ============================================================
    for case_id, tb_file in enumerate(tb_files):
        print(f"\n[=== SIMULATING CASE {case_id} ===]")

        # compile TB
        run_cmd(["vlog", "-sv", tb_file])

        # sim log path
        sim_log = os.path.join(result_dir, f"SIMresult_case{case_id}.txt")
        with open(sim_log, "w", encoding="utf-8") as f:
            f.write(f"==== Simulation Log for case {case_id} ====\n")
        # run simulation
        tb_modname = f"tb_{top_module}_case{case_id}"
        run_cmd(
            ["vsim", "-c", tb_modname, "-do", "run -all; quit;"],
            sim_log
        )

        print(f"[+] Simulation log saved: {sim_log}")

    print("\n[완료] All simulations finished.\n")

    ###########################################
    #여기서부터는 골든모델
    ###########################################
    if golden_file != None :
        # 1) Golden Model 클래스 로드
        GoldenClass = load_golden_model(golden_file)

        # 2) 파라미터 dict 준비
        params_dict = {k:int(v) for (k,v) in params}

        # 3) Golden Model 인스턴스 생성
        golden = GoldenClass(params_dict)

        # 4) 입력 HEX 파일 매핑 (clk / rst_n 제외)
        input_hex_map = {}
        for p in ports:
            if p["dir"] == "input" and p["name"] not in (clk_name, reset_name):
                hex_path = os.path.join(result_dir, f"{p['name']}_case{case_id}.hex")
                input_hex_map[p["name"]] = hex_path

        # 5) 출력 파일 경로
        golden_output_path = os.path.join(result_dir, f"golden_case{case_id}.txt")

        # 6) Golden Model 실행
        run_golden_model(
            golden,              # 반드시 인스턴스!
            params_dict,
            input_hex_map,       # {"i_data":"...", "sel":"..."}
            golden_output_path,  # 출력 파일
            cycles               # 사이클 수
        )
    


    ###########################################
    #여기까지 골든모델
    ###########################################

if __name__ == "__main__":
    main()
