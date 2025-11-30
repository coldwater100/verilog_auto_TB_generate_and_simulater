# -*- coding: utf-8 -*-

import json
import os
import sys
import importlib.util
import math
from base_golden_model import BaseGoldenModel


# ------------------------------------------------------------
# Golden Model Loader
# ------------------------------------------------------------
def load_golden_class(py_file):
    """Load a golden model class that inherits from BaseGoldenModel."""
    spec = importlib.util.spec_from_file_location("golden_module", py_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    golden_class = None
    for v in mod.__dict__.values():
        if isinstance(v, type) and issubclass(v, BaseGoldenModel) and v is not BaseGoldenModel:
            golden_class = v
            break

    if golden_class is None:
        raise RuntimeError("[ERROR] No valid GoldenModel class found in file")

    print(f"[+] Loaded Golden Model class: {golden_class.__name__}")
    return golden_class


# ------------------------------------------------------------
# HEX 파일 로더
# ------------------------------------------------------------
def read_hex_file(path):
    """Return list of hex strings."""
    lines = []
    with open(path, "r") as f:
        for ln in f:
            lines.append(ln.strip())
    return lines


# ------------------------------------------------------------
# 한 CASE 실행
# ------------------------------------------------------------
def run_single_case(golden_class, cfg):

    case_id = cfg["case_id"]
    cycles = cfg["cycles"]

    params = cfg["params"]
    input_ports = cfg["input_ports"]
    output_ports = cfg["output_ports"]
    hex_files = cfg["hex_files"]

    print(f"\n[+] Running Golden Model for CASE {case_id} (cycles={cycles})")

    gm = golden_class(params)
    gm.reset()

    # 입력 hex 읽기
    hex_map = {}
    for p in input_ports:
        hex_map[p] = read_hex_file(hex_files[p])

    # FINAL_WIDTH 계산
    if hasattr(gm, "FINAL_WIDTH"):
        FINAL_WIDTH = gm.FINAL_WIDTH
    else:
        INPUT_COUNT = params.get("INPUT_COUNT", 1)
        DATA_WIDTH  = params.get("DATA_WIDTH", 1)
        FINAL_WIDTH = DATA_WIDTH + math.ceil(math.log2(INPUT_COUNT))

    hex_len = (FINAL_WIDTH + 3) // 4

    # CSV 출력
    out_csv = f"results/golden_case{case_id}.csv"
    fp = open(out_csv, "w", encoding="utf-8")
    fp.write("cycle," + ",".join(output_ports) + "\n")

    # cycle loop
    for cycle in range(cycles):

        # ---- 입력 딕셔너리 구성 ----
        in_dict = {}

        # rst_n 자동 처리 (TB와 동일)
        port_names = [p["name"] for p in cfg["ports"]]
        if "rst_n" in port_names:
            in_dict["rst_n"] = 0 if cycle < 3 else 1

        # clk 자동 포함
        if "clk" in port_names:
            in_dict["clk"] = 1  # Golden에서는 의미 없음

        # 입력 포트 값 로드
        for p in input_ports:
            raw = hex_map[p][cycle]  # hex 문자열
            
            if raw == "" or all(ch.lower() == "x" for ch in raw):
                in_dict[p] = None
            else:
                in_dict[p] = int(raw, 16)

        # ---- GoldenModel 실행 ----
        out_vals = gm.step(in_dict)

        # ---- CSV 출력 ----
        line = f"{cycle}"
        for op in output_ports:
            val = out_vals.get(op, None)

            if val is None or isinstance(val, str) and val.lower().startswith("x"):
                line += "," + ("x" * hex_len)
            else:
                line += "," + f"{val:0{hex_len}x}"

        fp.write(line + "\n")

    fp.close()
    print(f"[+] Saved Golden CSV → {out_csv}")


# ------------------------------------------------------------
# 모든 CASE 실행
# ------------------------------------------------------------
def run_all_cases(golden_class):

    cfg_list = []
    for f in os.listdir("results"):
        if f.startswith("config_case") and f.endswith(".json"):
            cfg_list.append(os.path.join("results", f))

    cfg_list.sort()

    print("[+] Found config JSON files:")
    for f in cfg_list:
        print("   -", f)

    for cfg_path in cfg_list:
        with open(cfg_path, "r") as fp:
            cfg = json.load(fp)
        run_single_case(golden_class, cfg)


# ------------------------------------------------------------
# Entry
# ------------------------------------------------------------
if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python auto_golden.py <golden_model_name_without_py>")
        print("Example: python auto_golden.py golden_adder_tree")
        sys.exit(1)

    model_name = sys.argv[1]
    py_file = model_name

    if not os.path.exists(py_file):
        raise RuntimeError(f"[ERROR] Golden model file not found: {py_file}")

    GoldenClass = load_golden_class(py_file)
    run_all_cases(GoldenClass)
