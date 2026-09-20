# Research-helper attribution

`llama_matched_helper.cpp` adapts this project's MIT-licensed `native/llama_decision_helper.cpp`. It is a separate research artifact and does not modify the released inference path.

The build uses the headers and dynamic libraries of [llama.cpp](https://github.com/ggml-org/llama.cpp/tree/f072b103714dfa1eee531f80b24512faf38e3dd2), licensed under MIT. The provided runtime's license files are copied into the separate compiled package. The upstream [SHA-256 implementation](https://github.com/ggml-org/llama.cpp/tree/f072b103714dfa1eee531f80b24512faf38e3dd2/vendor/hash/sha256) is public-domain code by Igor Pavlov; its C source is compiled directly from the verified source checkout, not vendored into this repository. The upstream nlohmann JSON header carries its own MIT license, supplied with the runtime's notices.

Compiled executables, libraries, model weights, and local logs remain outside this source repository. Model terms remain those of the original Qwen/GGUF artifacts. No upstream endorsement or reproduction of TypeSafe Jev is claimed.
