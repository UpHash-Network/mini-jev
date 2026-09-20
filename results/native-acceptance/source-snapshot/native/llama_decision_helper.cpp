// Direct next-token logits, never sampling or generating completion tokens.
#include "llama.h"
#include "chat.h"
#include "json.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <iterator>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using json = nlohmann::json;
using Clock = std::chrono::steady_clock;

static double milliseconds(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

static std::string render_messages(const common_chat_templates * templates, const json & request) {
    const bool has_prompt = request.contains("prompt");
    const bool has_messages = request.contains("messages");
    if (has_prompt == has_messages) {
        throw std::runtime_error("provide exactly one of prompt and messages");
    }
    if (has_prompt) {
        if (!request.at("prompt").is_string()) throw std::runtime_error("prompt must be a string");
        return request.at("prompt").get<std::string>();
    }
    const auto & messages = request.at("messages");
    if (!messages.is_array() || messages.empty()) throw std::runtime_error("messages must be a nonempty array");
    common_chat_templates_inputs inputs;
    inputs.use_jinja = true;
    inputs.enable_thinking = false;
    inputs.add_generation_prompt = true;
    inputs.chat_template_kwargs["enable_thinking"] = "false";
    for (const auto & entry : messages) {
        common_chat_msg message;
        message.role = entry.at("role").get<std::string>();
        message.content = entry.at("content").get<std::string>();
        if (message.role != "system" && message.role != "user" && message.role != "assistant") {
            throw std::runtime_error("only system/user/assistant text messages are supported");
        }
        inputs.messages.push_back(std::move(message));
    }
    auto result = common_chat_templates_apply(templates, inputs);
    const auto open = result.prompt.rfind("<think>");
    const auto close = result.prompt.rfind("</think>");
    if (open != std::string::npos && (close == std::string::npos || close < open)) {
        throw std::runtime_error("chat template left an open thinking block despite enable_thinking=false");
    }
    // A fixed assistant prefix is input text, not generated text. Candidate
    // tokenization below validates the actual boundary after this prefix.
    const std::string prefix = request.value("assistant_prefix", std::string());
    if (prefix.size() > 1024) throw std::runtime_error("assistant_prefix is too long");
    return result.prompt + prefix;
}

static std::vector<llama_token> tokenize(const llama_vocab * vocab, const std::string & text,
                                        bool add_special, bool parse_special) {
    int32_t n = llama_tokenize(vocab, text.data(), static_cast<int32_t>(text.size()),
                               nullptr, 0, add_special, parse_special);
    if (n == 0) return {};
    if (n > 0) throw std::runtime_error("unexpected tokenizer sizing result");
    std::vector<llama_token> tokens(static_cast<size_t>(-n));
    n = llama_tokenize(vocab, text.data(), static_cast<int32_t>(text.size()), tokens.data(),
                       static_cast<int32_t>(tokens.size()), add_special, parse_special);
    if (n < 0) throw std::runtime_error("tokenizer failed after sizing");
    tokens.resize(static_cast<size_t>(n));
    return tokens;
}

int main(int argc, char ** argv) {
    std::string model_path;
    std::string render_template_file;
    uint32_t ctx_size = 512;
    int gpu_layers = 99;
    int threads = 6;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--help") {
            std::cout << "llama-decision-helper --model FILE [--ctx 512] [--gpu-layers 99] [--threads 6]\n"
                         "CPU-only Jinja test: --render-only-template FILE\n"
                         "JSONL stdin: {id, messages:[{role,content}], candidates:[A,B], max_input_tokens:512}\n"
                         "Alternatively supply preformatted prompt in place of messages. No sampling is performed.\n";
            return 0;
        }
        if (i + 1 == argc) throw std::runtime_error("missing CLI value");
        const std::string value = argv[++i];
        if (arg == "--model") model_path = value;
        else if (arg == "--render-only-template") render_template_file = value;
        else if (arg == "--ctx") ctx_size = static_cast<uint32_t>(std::stoul(value));
        else if (arg == "--gpu-layers") gpu_layers = std::stoi(value);
        else if (arg == "--threads") threads = std::stoi(value);
        else throw std::runtime_error("unknown CLI flag: " + arg);
    }
    if (ctx_size < 1 || ctx_size > 32768 || threads < 1) throw std::runtime_error("invalid ctx/threads");

    llama_model * model = nullptr;
    llama_context * context = nullptr;
    common_chat_templates_ptr templates;
    const llama_vocab * vocab = nullptr;
    uint64_t total_decode_count = 0;
    bool backend_initialized = false;
    try {
        if (!render_template_file.empty()) {
            std::ifstream file(render_template_file);
            if (!file) throw std::runtime_error("could not open template file");
            const std::string source((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
            templates = common_chat_templates_init(nullptr, source, "", "<|im_end|>");
            std::cout << json({{"ready", true}, {"mode", "render_only"}, {"gpu_initialized", false}}).dump() << std::endl;
        } else {
            if (model_path.empty()) throw std::runtime_error("--model is required");
            llama_backend_init();
            backend_initialized = true;
            auto model_params = llama_model_default_params();
            model_params.n_gpu_layers = gpu_layers;
            model_params.load_mode = LLAMA_LOAD_MODE_MMAP;
            model = llama_model_load_from_file(model_path.c_str(), model_params);
            if (!model) throw std::runtime_error("model load failed; inspect stderr for tensor/architecture compatibility");
            auto context_params = llama_context_default_params();
            context_params.n_ctx = ctx_size;
            context_params.n_batch = ctx_size;
            context_params.n_ubatch = ctx_size;
            context_params.n_seq_max = 1;
            context_params.n_threads = threads;
            context_params.n_threads_batch = threads;
            context_params.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_ENABLED;
            context = llama_init_from_model(model, context_params);
            if (!context) throw std::runtime_error("context creation failed");
            vocab = llama_model_get_vocab(model);
            templates = common_chat_templates_init(model, "");
            std::cout << json({{"ready", true}, {"mode", "direct_logits"}, {"ctx", llama_n_ctx(context)},
                               {"vocab_size", llama_vocab_n_tokens(vocab)}, {"gpu_layers", gpu_layers},
                               {"batch_strategy", "sequential_independent_requests"},
                               {"total_decode_count", 0}}).dump() << std::endl;
        }

        std::string line;
        while (std::getline(std::cin, line)) {
            if (line.empty()) continue;
            json request;
            json id = nullptr;
            uint64_t request_decodes = 0;
            const auto total_start = Clock::now();
            try {
                request = json::parse(line);
                if (!request.is_object()) throw std::runtime_error("request must be an object");
                id = request.value("id", json(nullptr));
                const std::string prompt = render_messages(templates.get(), request);
                if (!render_template_file.empty()) {
                    std::cout << json({{"id", id}, {"prompt", prompt}, {"thinking_enabled", false},
                                       {"decode_count", 0}, {"total_decode_count", 0}}).dump() << std::endl;
                    continue;
                }
                const int max_input = request.value("max_input_tokens", static_cast<int>(ctx_size));
                if (max_input < 1 || max_input > static_cast<int>(ctx_size)) {
                    throw std::runtime_error("max_input_tokens must be in [1, configured ctx]");
                }
                const auto & candidates = request.at("candidates");
                if (!candidates.is_array() || candidates.size() < 2 || candidates.size() > 26) {
                    throw std::runtime_error("candidates must contain 2 to 26 strings");
                }
                auto input_tokens = tokenize(vocab, prompt, true, true);
                if (input_tokens.empty() || input_tokens.size() > static_cast<size_t>(max_input)) {
                    throw std::runtime_error("input token count outside limit; no truncation applied");
                }
                std::vector<llama_token> candidate_ids;
                for (const auto & item : candidates) {
                    if (!item.is_string() || item.get<std::string>().empty()) throw std::runtime_error("candidate must be a nonempty string");
                    const auto text = item.get<std::string>();
                    const auto isolated = tokenize(vocab, text, false, false);
                    if (isolated.size() != 1) throw std::runtime_error("candidate is not exactly one isolated token");
                    const auto appended = tokenize(vocab, prompt + text, true, true);
                    auto expected = input_tokens;
                    expected.push_back(isolated.front());
                    if (appended != expected) throw std::runtime_error("candidate does not append as exactly one token at prompt boundary");
                    candidate_ids.push_back(isolated.front());
                }
                if (std::set<llama_token>(candidate_ids.begin(), candidate_ids.end()).size() != candidate_ids.size()) {
                    throw std::runtime_error("candidate token ids are not unique");
                }
                const auto model_start = Clock::now();
                // Clear both KV and recurrent state. No prefix reuse between requests.
                llama_memory_clear(llama_get_memory(context), true);
                auto batch = llama_batch_get_one(input_tokens.data(), static_cast<int32_t>(input_tokens.size()));
                ++total_decode_count;
                ++request_decodes;
                const int result = llama_decode(context, batch);
                if (result != 0) throw std::runtime_error("llama_decode failed with code " + std::to_string(result));
                const float * full_logits = llama_get_logits_ith(context, -1);
                if (!full_logits) throw std::runtime_error("final logits unavailable");
                // llama_get_logits_ith synchronizes GPU work before returning.
                std::vector<float> logits;
                for (const auto token_id : candidate_ids) {
                    const float value = full_logits[token_id];
                    if (!std::isfinite(value)) throw std::runtime_error("non-finite candidate logit");
                    logits.push_back(value);
                }
                const double model_ms = milliseconds(model_start);
                json response = {{"id", id}, {"candidate_ids", candidate_ids}, {"logits", logits},
                    {"input_tokens", input_tokens.size()}, {"output_tokens", 0},
                    {"decode_count", request_decodes}, {"total_decode_count", total_decode_count},
                    {"decode_count_semantics", "llama_decode_API_calls"},
                    {"model_ms", model_ms}, {"latency_ms", milliseconds(total_start)},
                    {"projection", "full_vocab_then_candidate_gather"},
                    {"state_cleared", true}, {"template_applied", request.contains("messages")},
                    {"thinking_enabled", request.contains("messages") ? json(false) : json(nullptr)}};
                if (request.value("debug_prompt", false)) {
                    response["prompt"] = prompt;
                }
                // Local numerical audit only. The normal path neither copies nor serializes
                // the full vocabulary. The caller must not expose this through HTTP.
                if (request.value("debug_full_logits", false)) {
                    response["full_logits"] = std::vector<float>(
                        full_logits, full_logits + llama_vocab_n_tokens(vocab));
                }
                std::cout << response.dump() << std::endl;
            } catch (const std::exception & error) {
                std::cout << json({{"id", id}, {"error", error.what()}, {"decode_count", request_decodes},
                                   {"total_decode_count", total_decode_count}}).dump() << std::endl;
            }
        }
    } catch (const std::exception & error) {
        std::cerr << "llama-decision-helper: " << error.what() << std::endl;
        std::cout << json({{"ready", false}, {"error", error.what()}}).dump() << std::endl;
        if (context) llama_free(context);
        if (model) llama_model_free(model);
        if (backend_initialized) llama_backend_free();
        return 2;
    }
    templates.reset();
    if (context) llama_free(context);
    if (model) llama_model_free(model);
    if (backend_initialized) llama_backend_free();
    return 0;
}
