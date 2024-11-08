1. Compile ONNX from scratch with Cuda

1. Edit Camera Path to /dev/videoX (0,1)


1. install pocl with

https://largo.lip6.fr/monolithe/admin_pocl/

```bash
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-funroll-loops -march=native" -DCMAKE_C_FLAGS="-funroll-loops -march=native" -DWITH_LLVM_CONFIG=/usr/lib/llvm-13/bin/llvm-config -DSTATIC_LLVM=ON -DENABLE_CUDA=ON .. -DLLC_HOST_CPU=cortex-a78
```