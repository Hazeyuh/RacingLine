#!/usr/bin/env python3
"""Bootstrap official Fastest-lap and patch its drifting logger dependency."""
from pathlib import Path
import os, subprocess, sys, shutil, json
ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'upstream/fastest-lap'
REV='0660208aaeea956c9d833cb32a0ae6b4d959ecb9'
def call(args,**kw):return subprocess.run(args,cwd=ROOT,**kw).returncode
if not shutil.which('gfortran'):
    sys.exit('缺少 Fortran 编译器；macOS 请先运行 brew install gcc')
if not UP.exists():
    UP.parent.mkdir(exist_ok=True)
    if call(['git','clone','https://github.com/juanmanzanero/fastest-lap.git',str(UP)]):sys.exit(1)
    if call(['git','-C',str(UP),'checkout',REV]):sys.exit(1)
patch=ROOT/'patches/rental-kart-engine.patch'
if patch.exists():
    if subprocess.run(['git','apply','--check',str(patch)],cwd=UP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
        subprocess.run(['git','apply',str(patch)],cwd=UP,check=True)
    elif subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=UP,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0:
        sys.exit('卡丁车动力补丁与上游文件冲突')
env=os.environ.copy();env['FC']=shutil.which('gfortran');env['CMAKE_BUILD_PARALLEL_LEVEL']='8';env['MAKEFLAGS']='-j8'
args=['cmake','-S',str(UP),'-B',str(UP/'build'),'-G','Ninja','-DENABLE_TESTS=OFF','-DCMAKE_BUILD_TYPE=Release']
versions=json.loads((ROOT/'docs/upstream-versions.json').read_text())
gtest=UP/'cmake/third-party/gtest.cmake'
gtest.write_text(gtest.read_text().replace('GIT_TAG main','GIT_TAG '+versions['googletest']))
for attempt in range(3):
    logger=UP/'build/lion/source/cmake/third-party/loggercpp.cmake'
    if logger.exists():
        for name,old in [('loggercpp','main'),('lapack','master'),('tinyxml','master')]:
            file=logger.parent/(name+'.cmake')
            file.write_text(file.read_text().replace('GIT_TAG '+old,'GIT_TAG '+versions[name]))
        file=logger.parent/'ipopt.cmake'
        file.write_text(file.read_text().replace('GIT_TAG stable/3.14','GIT_TAG '+versions['ipopt']).replace('GIT_TAG releases/3.0.2','GIT_TAG '+versions['mumps']))
    if call(args,env=env)==0:break
    if not logger.exists():sys.exit('依赖配置失败，请检查输出日志。')
else:sys.exit('三次配置均失败，请检查输出日志。')
# The retained logger API uses an MSVC-only formatting call.
for header in [UP/'build/thirdparty/include/lion/thirdparty/include/logger.hpp',UP/'build/lion/build/lion/thirdparty/include/logger.hpp']:
    if header.exists(): header.write_text(header.read_text().replace('sprintf_s(buffer,','snprintf(buffer,sizeof(buffer),'))
from patch_iterations import patch as patch_iterations
patch_iterations()
sys.exit(call(['cmake','--build',str(UP/'build'),'--target','fastestlapc','-j','8'],env=env))
