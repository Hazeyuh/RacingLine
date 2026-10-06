#!/usr/bin/env python3
"""Opt-in original-coordinate iterate export from Ipopt's intermediate callback."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CODE=r'''
       // RacingLine: optional snapshots; disabled has no file I/O.
       const char* output = std::getenv("RACINGLINE_ITERATIONS");
       if (output && *output) {
           const size_t points = std::strtoul((std::getenv("RACINGLINE_POINTS") ? std::getenv("RACINGLINE_POINTS") : "0"), nullptr, 10);
           const size_t stride = std::strtoul((std::getenv("RACINGLINE_STRIDE") ? std::getenv("RACINGLINE_STRIDE") : "0"), nullptr, 10);
           const size_t lateral = std::strtoul((std::getenv("RACINGLINE_LATERAL") ? std::getenv("RACINGLINE_LATERAL") : "0"), nullptr, 10);
           const size_t velocity = std::strtoul((std::getenv("RACINGLINE_VELOCITY") ? std::getenv("RACINGLINE_VELOCITY") : "0"), nullptr, 10);
           std::vector<double> values(nx_);
           if (points > 0 && stride > lateral && stride > velocity && points*stride == nx_ && this->get_curr_iterate(ip_data,ip_cq,false,nx_,values.data(),nullptr,nullptr,ng_,nullptr,nullptr)) {
               bool finite = std::isfinite(obj_value) && std::isfinite(inf_pr);
               for (size_t i=0;i<points;++i) finite = finite && std::isfinite(values[i*stride+lateral]) && std::isfinite(values[i*stride+velocity]);
               if (finite) {
                   std::ofstream stream(output, std::ios::app);
                   stream << std::setprecision(16) << "{\"iteration\":" << iter << ",\"objective\":" << obj_value << ",\"constraint_error\":" << inf_pr << ",\"restoration\":" << (mode==Ipopt::RestorationPhaseMode ? "true":"false") << ",\"offset\":[";
                   for (size_t i=0;i<points;++i) {if(i) stream << ',';stream << values[i*stride+lateral];}
                   stream << "],\"velocity\":[";
                   for (size_t i=0;i<points;++i) {if(i) stream << ',';stream << values[i*stride+velocity];}
                   stream << "]}\n";
               }
           }
       }
'''
def patch():
 count=0
 for p in (ROOT/'upstream/fastest-lap').rglob('ipopt_cppad_handler.hpp'):
  s=p.read_text()
  if '// RacingLine: optional snapshots' in s:continue
  s=s.replace('#include <cppad/cppad.hpp>','#include <cppad/cppad.hpp>\n#include <fstream>\n#include <cstdlib>\n#include <iomanip>\n#include <cmath>')
  start=s.index('    virtual bool intermediate_callback(')
  pos=s.index('       return true;',start)
  s=s[:pos]+CODE+s[pos:];p.write_text(s);count+=1
 print('Iteration callback patched:',count)
if __name__=='__main__':patch()
