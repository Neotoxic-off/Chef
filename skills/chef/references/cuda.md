# CUDA

Read with `cpp.md`; all its rules apply to host and device code. Build with CMake (`project(app LANGUAGES CXX CUDA)`), C++20. Written in Nov 2026 (not benchmarked): CUDA Toolkit 13.5 is current; check with `nvcc --version` and the CUDA Toolkit release notes.

## Build, warnings, lint

```cmake
set(CMAKE_CUDA_STANDARD 20)
set(CMAKE_CUDA_ARCHITECTURES native)  # CI and releases list real targets, e.g. "80;90"
target_compile_options(kernels PRIVATE
  $<$<COMPILE_LANGUAGE:CUDA>:--Werror=all-warnings,cross-execution-space-call,default-stream-launch
    -Xcompiler=-Wall,-Wextra -lineinfo>)
```

- `-lineinfo` gives sanitizer and profiler reports source lines without disabling optimizations.
- `default-stream-launch` makes every `<<<...>>>` launch name its stream.
- clang-format and clang-tidy as in `cpp.md`. Not verified: how well clang-tidy parses `.cu` files from an nvcc compilation database in your setup; if it cannot, run it on the host `.cpp` files and tell the user.

## Code

- Explicit types: `const unsigned int threadIndex = blockIdx.x * blockDim.x + threadIdx.x;`, `dim3 block{kThreadsPerBlock};`. `auto` only as in `cpp.md`: when the type is spelled on the right side or cannot be named.
- Check every runtime call and every launch. One host helper, not a macro per call site:
  ```cpp
  void check(cudaError_t status, std::source_location where = std::source_location::current()) {
      if (status != cudaSuccess) {
          throw CudaError(status, where);
      }
  }

  scale<<<grid, block, kNoSharedMemory, stream>>>(input, output, count);
  check(cudaGetLastError());
  ```
- Own device memory with RAII (`std::unique_ptr` with a `cudaFree` deleter, or a small buffer class). No raw `cudaMalloc`/`cudaFree` pairs in business code.
- Use CCCL (Thrust, CUB, libcu++) and cuBLAS/cuFFT before writing your own reduction, scan, sort or GEMM.
- Kernels: grid-stride loops, bounds check on every index, `const T* __restrict__` inputs, coalesced access, no host calls.
- Name launch shapes and tuning values (`constexpr int kThreadsPerBlock = 256;`); size from `cudaOccupancyMaxPotentialBlockSize` where it matters.
- Streams and `cudaMallocAsync` for overlap; synchronize only where the host needs the result.
- Kernels cannot throw: report errors through a status buffer the host checks.
- Profile with Nsight Systems (timeline) then Nsight Compute (kernel) before optimizing. Keep a CPU reference implementation for every kernel.

## Tests

- GoogleTest on the host. Test names state the behavior: `TEST(ScaleKernel, MultipliesEveryElementByFactor)`.
- Compare each kernel with its CPU reference on edge sizes: 0, 1, one block, block + 1, not a multiple of the warp size.
- Floats: compare with a named tolerance (`EXPECT_NEAR(actual, expected, kTolerance)`), never `==`.
- Run the test binary under Compute Sanitizer in CI, failing on any report:
  ```sh
  compute-sanitizer --tool memcheck --leak-check full --error-exitcode 1 ./build/tests
  compute-sanitizer --tool racecheck --error-exitcode 1 ./build/tests
  ```
  Also `--tool initcheck` and `--tool synccheck`.
- Coverage: gcov/llvm-cov measure host code only; device code is covered by the reference comparisons. Gate host coverage at 90%.
- GPU CI needs a runner with a GPU; mark GPU tests with a CTest label so CPU-only runners skip them explicitly.

Order before done: format, build (warnings are errors), tests, Compute Sanitizer.
