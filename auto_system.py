# made by 이수찬(suchan lee)
#
# 작동을 위해 auto_system.py, auto_compare.py, auto_golden.py, auto_vsim.py 필요
# 사용방법 : 프로그램과 골든모델(.py)(선택사항), 베릴로그(.v) 파일들을 같은 디렉토리에 넣고
# 예시)  python auto_compare.py golden_model.py file1.v file2.v ... -> 이런식으로 실행하면
# hw모델과 sw모델을 반복실행하여 결과 비교함

import subprocess
import sys

if len(sys.argv) < 2:
    print("Usage: python auto_vsim.py golden_model.py file1.v file2.v ...")
    sys.exit(1)
golden_file=None

if sys.argv[1].endswith(".py"):
    golden_file = sys.argv[1]
    vfiles = sys.argv[2:]
else:
    print("Usage: python auto_vsim.py golden_model.py file1.v file2.v ...")
    sys.exit(1)


# 첫 번째 프로그램
print("auto_vsim 실행 중...")
r1 = subprocess.run(["python", "auto_vsim.py"]+vfiles)
print("auto_vsim 종료코드:", r1.returncode)

# 두 번째 프로그램
print("auto_golden 실행 중...")
r2 = subprocess.run(["python", "auto_golden.py"]+[golden_file])
print("auto_golden 종료코드:", r2.returncode)

# 둘 다 정상 종료 시
if r1.returncode == 0 and r2.returncode == 0:
    print("두 프로그램 모두 성공적으로 종료됨 → auto_compare 실행")
    print("auto_golden 실행 중...")
    r3 = subprocess.run(["python", "auto_compare.py"])
    print("auto_golden 종료코드:", r3.returncode)
else:
    print("오류 존재")