// Research-only matched direct / constrained-one-token / autoregressive-JSON helper.
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
#include <limits>
#include <iomanip>
#include <sstream>
extern "C" {
#include "sha256.h"
}

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

static std::string sha(const std::string & bytes) {
    unsigned char result[SHA256_DIGEST_SIZE];
    sha256_hash(result, reinterpret_cast<const unsigned char *>(bytes.data()), bytes.size());
    std::ostringstream stream;
    for (auto byte : result) stream << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(byte);
    return stream.str();
}

static std::string piece(const llama_vocab * vocab, llama_token token) {
    std::vector<char> buffer(128);
    int n = llama_token_to_piece(vocab, token, buffer.data(), buffer.size(), 0, false);
    if (n < 0) {
        buffer.resize(-n);
        n = llama_token_to_piece(vocab, token, buffer.data(), buffer.size(), 0, false);
    }
    if (n < 0) throw std::runtime_error("token piece conversion failed");
    return std::string(buffer.data(), n);
}

using Sampler = std::unique_ptr<llama_sampler, decltype(&llama_sampler_free)>;

static std::string grammar_for(const json & candidates, const std::string & kind) {
    std::string alternatives;
    for (const auto & candidate : candidates) {
        const auto value = candidate.get<std::string>();
        // Only safe label literals: the grammar is never supplied by callers.
        if (kind == "string") {
            if (value.size() != 1 || value[0] < 'A' || value[0] > 'Z')
                throw std::runtime_error("JSON string labels must be A-Z");
        } else if (kind == "number") {
            if (value.size() != 1 || value[0] < '0' || value[0] > '9')
                throw std::runtime_error("JSON numeric labels must be single digits");
        } else throw std::runtime_error("json_value_kind must be string or number");
        const std::string literal = kind == "string" ? json(value).dump() : value;
        if (!alternatives.empty()) alternatives += " | ";
        alternatives += json(literal).dump();
    }
    // Optional one ASCII space between punctuation; no unbounded or trailing
    // whitespace loop. Stop immediately after the complete allowed JSON object.
    return "root ::= \"{\" ws \"\\\"answer\\\"\" ws \":\" ws answer ws \"}\"\n"
           "ws ::= \" \"?\nanswer ::= " + alternatives + "\n";
}

static int completed_answer(const std::string & text, const json & candidates, const std::string & kind) {
    const auto value = json::parse(text, nullptr, false);
    if (value.is_discarded()) return -1;
    if (!value.is_object() || value.size() != 1 || !value.contains("answer"))
        throw std::runtime_error("generated JSON does not match the single-answer schema");
    const auto & answer = value.at("answer");
    if ((kind == "string" && !answer.is_string()) || (kind == "number" && !answer.is_number_integer()))
        throw std::runtime_error("generated answer has wrong JSON type");
    const std::string label = kind == "string" ? answer.get<std::string>() : answer.dump();
    for (size_t i = 0; i < candidates.size(); ++i)
        if (candidates[i].get<std::string>() == label) return static_cast<int>(i);
    throw std::runtime_error("generated JSON answer is not an allowed label");
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
            std::cout << "llama-matched-helper --model FILE [--ctx 512] [--gpu-layers 99] [--threads 6]\n"
                         "CPU-only Jinja test: --render-only-template FILE\n"
                         "JSONL stdin: {id, messages:[{role,content}], candidates:[A,B], max_input_tokens:512}\n"
                         "Alternatively supply preformatted prompt in place of messages. Requests choose mode direct, one_token, or json.\n";
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
            std::cout << json({{"ready", true}, {"mode", "matched_native"}, {"ctx", llama_n_ctx(context)},
                               {"vocab_size", llama_vocab_n_tokens(vocab)}, {"gpu_layers", gpu_layers},
                               {"batch_strategy", "sequential_independent_requests"},
                               {"total_decode_count", 0}}).dump() << std::endl;
        }

        std::string line;
        while (std::getline(std::cin, line)) {
            if (line.empty()) continue;
            json id = nullptr;
            uint64_t request_decodes = 0;
            const auto total_start = Clock::now();
            try {
                const auto request = json::parse(line);
                if (!request.is_object()) throw std::runtime_error("request must be an object");
                id = request.value("id", json(nullptr));
                json timing;
                timing["parse_ms"] = milliseconds(total_start);
                const std::string mode = request.value("mode", std::string("direct"));
                // LMQL LMTP backend: true autoregressive sequence log probabilities.
                // Decode all but the final target token; obtain every predictive position.
                // The existing direct / one_token / json paths below are unmodified.
                if (mode == "lmql_score") {
                    if (!context) throw std::runtime_error("lmql_score requires loaded model");
                    auto all_tokens = request.at("input_token_ids").get<std::vector<llama_token>>();
                    if (all_tokens.size() < 2 || all_tokens.size() > ctx_size)
                        throw std::runtime_error("invalid lmql_score sequence length");
                    const int nv = llama_vocab_n_tokens(vocab);
                    for (auto t : all_tokens) if (t < 0 || t >= nv) throw std::runtime_error("token ID outside vocabulary");
                    auto prefix = all_tokens;
                    prefix.pop_back();
                    llama_memory_clear(llama_get_memory(context), true);
                    auto batch = llama_batch_init(static_cast<int>(prefix.size()), 0, 1);
                    batch.n_tokens = static_cast<int>(prefix.size());
                    for (size_t i = 0; i < prefix.size(); ++i) {
                        batch.token[i] = prefix[i]; batch.pos[i] = static_cast<llama_pos>(i);
                        batch.n_seq_id[i] = 1; batch.seq_id[i][0] = 0; batch.logits[i] = 1;
                    }
                    ++total_decode_count; ++request_decodes;
                    int rc = llama_decode(context, batch);
                    llama_batch_free(batch);
                    if (rc != 0) throw std::runtime_error("lmql_score decode failed");
                    std::vector<double> scores{0.0};
                    double final_lse = 0.0, final_logit = 0.0;
                    for (size_t j = 0; j < prefix.size(); ++j) {
                        const float * logits = llama_get_logits_ith(context, static_cast<int>(j));
                        if (!logits) throw std::runtime_error("all-position logits missing");
                        float largest = *std::max_element(logits, logits + nv);
                        double denom = 0.0;
                        for (int k = 0; k < nv; ++k) denom += std::exp(static_cast<double>(logits[k]) - largest);
                        const double lse = largest + std::log(denom);
                        const double value = logits[all_tokens[j + 1]] - lse;
                        if (!std::isfinite(value)) throw std::runtime_error("nonfinite lmql score");
                        scores.push_back(value); final_lse = lse; final_logit = logits[all_tokens[j + 1]];
                    }
                    std::cout << json({{"id",id},{"mode",mode},{"input_token_ids",all_tokens},
                        {"scores",scores},{"final_logit",final_logit},{"final_vocabulary_logsumexp",final_lse},
                        {"decode_count",request_decodes},{"total_decode_count",total_decode_count},
                        {"state_cleared",true},{"vocab_size",nv},{"elapsed_ms",milliseconds(total_start)}}).dump() << std::endl;
                    continue;
                }
                if (mode != "direct" && mode != "one_token" && mode != "json") throw std::runtime_error("unknown mode");
                auto tick = Clock::now();
                const std::string prompt = render_messages(templates.get(), request);
                timing["render_ms"] = milliseconds(tick);
                if (!render_template_file.empty()) {
                    std::cout << json({{"id", id}, {"prompt", prompt}, {"decode_count", 0}}).dump() << std::endl;
                    continue;
                }
                const int max_input = request.value("max_input_tokens", static_cast<int>(ctx_size));
                const int max_output = request.value("max_output_tokens", 32);
                const int max_request_ms = request.value("max_request_ms", 120000);
                if (max_input < 1 || max_input > static_cast<int>(ctx_size) || max_output < 1 || max_output > 32 || max_request_ms < 1 || max_request_ms > 300000)
                    throw std::runtime_error("invalid input/output/time limit");
                const auto & candidates = request.at("candidates");
                if (!candidates.is_array() || candidates.size() < 2 || candidates.size() > 26)
                    throw std::runtime_error("candidates must contain 2 to 26 labels");
                const std::string kind = request.value("json_value_kind", std::string("string"));
                if (mode == "json" && !request.value("assistant_prefix", std::string()).empty())
                    throw std::runtime_error("JSON mode generates the entire object; assistant_prefix must be empty");
                tick = Clock::now();
                auto input_tokens = tokenize(vocab, prompt, true, true);
                if (input_tokens.empty() || input_tokens.size() > static_cast<size_t>(max_input))
                    throw std::runtime_error("input token count outside limit; no truncation");
                std::vector<llama_token> candidate_ids;
                for (const auto & item : candidates) {
                    if (!item.is_string() || item.get<std::string>().empty()) throw std::runtime_error("empty/non-string label");
                    const auto isolated = tokenize(vocab, item.get<std::string>(), false, false);
                    if (isolated.size() != 1) throw std::runtime_error("label must have one isolated token");
                    if (mode != "json") {
                        const auto appended = tokenize(vocab, prompt + item.get<std::string>(), true, true);
                        auto expected = input_tokens;
                        expected.push_back(isolated[0]);
                        if (appended != expected) throw std::runtime_error("candidate boundary mismatch");
                    }
                    candidate_ids.push_back(isolated[0]);
                }
                if (std::set<llama_token>(candidate_ids.begin(), candidate_ids.end()).size() != candidates.size())
                    throw std::runtime_error("duplicate candidate token IDs");
                timing["tokenize_validate_ms"] = milliseconds(tick);
                const auto check_deadline = [&]() {
                    if (milliseconds(total_start) > max_request_ms) throw std::runtime_error("request deadline exceeded");
                };
                check_deadline();
                tick = Clock::now();
                llama_memory_clear(llama_get_memory(context), true);
                timing["state_reset_ms"] = milliseconds(tick);
                tick = Clock::now();
                auto batch = llama_batch_get_one(input_tokens.data(), static_cast<int32_t>(input_tokens.size()));
                ++total_decode_count; ++request_decodes;
                const int rc = llama_decode(context, batch);
                if (rc != 0) throw std::runtime_error("prefill decode failed: " + std::to_string(rc));
                const float * logits = llama_get_logits_ith(context, -1); // synchronization point
                if (!logits) throw std::runtime_error("prefill logits unavailable");
                timing["prefill_ms"] = milliseconds(tick);
                check_deadline();
                tick = Clock::now();
                std::vector<float> selected_logits;
                std::vector<double> probabilities;
                std::vector<int> max_indices;
                int label_index = -1;
                if (mode != "json") {
                    for (auto token : candidate_ids) {
                        if (!std::isfinite(logits[token])) throw std::runtime_error("nonfinite candidate logit");
                        selected_logits.push_back(logits[token]);
                    }
                    const auto largest = *std::max_element(selected_logits.begin(), selected_logits.end());
                    double denominator = 0;
                    for (size_t i = 0; i < selected_logits.size(); ++i) {
                        const double p = std::exp(static_cast<double>(selected_logits[i]) - largest);
                        probabilities.push_back(p); denominator += p;
                        if (selected_logits[i] == largest) max_indices.push_back(static_cast<int>(i));
                    }
                    for (auto & p : probabilities) p /= denominator;
                    label_index = max_indices.front();
                }
                timing["readout_ms"] = milliseconds(tick);
                tick = Clock::now();
                Sampler greedy(nullptr, llama_sampler_free), grammar(nullptr, llama_sampler_free);
                std::string grammar_text;
                if (mode != "direct") {
                    greedy.reset(llama_sampler_init_greedy());
                    if (!greedy) throw std::runtime_error("greedy sampler initialization failed");
                }
                if (mode == "json") {
                    grammar_text = grammar_for(candidates, kind);
                    grammar.reset(llama_sampler_init_grammar(vocab, grammar_text.c_str(), "root"));
                    if (!grammar) throw std::runtime_error("grammar initialization failed");
                }
                timing["sampler_setup_ms"] = milliseconds(tick);
                std::vector<llama_token> generated_ids;
                std::string generated_text;
                double sampling_ms = 0, decode_ms = 0, completion_check_ms = 0;
                if (mode != "direct") {
                    const int limit = mode == "one_token" ? 1 : max_output;
                    bool completed = false;
                    for (int step = 0; step < limit; ++step) {
                        check_deadline();
                        tick = Clock::now();
                        const int vocab_size = llama_vocab_n_tokens(vocab);
                        std::vector<llama_token_data> data;
                        data.reserve(vocab_size);
                        for (llama_token token = 0; token < vocab_size; ++token) {
                            const float score = mode == "one_token" ? -std::numeric_limits<float>::infinity() : logits[token];
                            data.push_back({token, score, 0.0f});
                        }
                        if (mode == "one_token") for (auto token : candidate_ids) data[token].logit = logits[token];
                        llama_token_data_array array{data.data(), data.size(), -1, false};
                        if (grammar) llama_sampler_apply(grammar.get(), &array);
                        llama_sampler_apply(greedy.get(), &array);
                        if (array.selected < 0 || static_cast<size_t>(array.selected) >= array.size || !std::isfinite(array.data[array.selected].logit))
                            throw std::runtime_error("no finite legal sampled token");
                        const auto token = array.data[array.selected].id;
                        if (llama_vocab_is_eog(vocab, token)) throw std::runtime_error("EOS before complete answer");
                        if (grammar) llama_sampler_accept(grammar.get(), token);
                        llama_sampler_accept(greedy.get(), token);
                        generated_ids.push_back(token);
                        generated_text += piece(vocab, token);
                        sampling_ms += milliseconds(tick);
                        tick = Clock::now();
                        if (mode == "one_token") {
                            const auto found = std::find(candidate_ids.begin(), candidate_ids.end(), token);
                            if (found == candidate_ids.end()) throw std::runtime_error("sampled token outside candidates");
                            label_index = static_cast<int>(found - candidate_ids.begin());
                            if (generated_text != candidates[label_index].get<std::string>()) throw std::runtime_error("sampled text differs from label");
                            completed = true;
                        } else {
                            label_index = completed_answer(generated_text, candidates, kind);
                            completed = label_index >= 0;
                        }
                        completion_check_ms += milliseconds(tick);
                        if (completed) break; // no EOS sampling and no needless final-token decode
                        if (step + 1 == limit) break;
                        if (input_tokens.size() + generated_ids.size() > llama_n_ctx(context)) throw std::runtime_error("generation exceeds context");
                        tick = Clock::now();
                        auto mutable_token = token;
                        auto next_batch = llama_batch_get_one(&mutable_token, 1);
                        ++total_decode_count; ++request_decodes;
                        const int next_rc = llama_decode(context, next_batch);
                        if (next_rc != 0) throw std::runtime_error("generation decode failed: " + std::to_string(next_rc));
                        logits = llama_get_logits_ith(context, -1); // synchronize each decoded token
                        if (!logits) throw std::runtime_error("generation logits unavailable");
                        decode_ms += milliseconds(tick);
                    }
                    if (!completed) throw std::runtime_error("output token limit reached before complete answer");
                }
                check_deadline();
                timing["sampling_ms"] = sampling_ms;
                timing["decode_ms"] = decode_ms;
                timing["completion_check_ms"] = completion_check_ms;
                tick = Clock::now();
                json response = {{"id", id}, {"mode", mode}, {"label_index", label_index},
                    {"answer", candidates.at(label_index)}, {"candidate_ids", candidate_ids},
                    {"candidate_ids_sha256", sha(json(candidate_ids).dump())},
                    {"prompt_sha256", sha(prompt)}, {"input_token_ids_sha256", sha(json(input_tokens).dump())},
                    {"input_tokens", input_tokens.size()}, {"output_tokens", generated_ids.size()},
                    {"generated_text", generated_text}, {"generated_token_ids", generated_ids},
                    {"decode_count", request_decodes}, {"total_decode_count", total_decode_count},
                    {"decode_count_semantics", "llama_decode_API_calls"}, {"state_cleared", true},
                    {"thinking_enabled", false}, {"projection", "full_vocabulary"},
                    {"candidate_boundary_checked", mode != "json"},
                    {"logits", mode == "json" ? json(nullptr) : json(selected_logits)},
                    {"probabilities", mode == "json" ? json(nullptr) : json(probabilities)},
                    {"max_logit_candidate_indices", max_indices},
                    {"argmax_tie", max_indices.size() > 1},
                    {"tie_policy", mode == "direct" ? "first_candidate_order" : "lowest_vocab_token_id"},
                    {"grammar_sha256", mode == "json" ? json(sha(grammar_text)) : json(nullptr)}};
                if (request.value("debug_input_tokens", false)) response["input_token_ids"] = input_tokens;
                if (request.value("debug_prompt", false)) response["prompt"] = prompt;
                timing["response_prepare_ms"] = milliseconds(tick);
                tick = Clock::now();
                std::string serialized = response.dump();
                timing["response_serialization_ms"] = milliseconds(tick);
                timing["native_total_ms"] = milliseconds(total_start);
                // Avoid serializing the large payload twice just to time it.
                // Small timing trailer and stdout delivery are excluded; the
                // parent measures complete pipe/HTTP wall time independently.
                serialized.pop_back();
                std::cout << serialized << ",\"timing_ms\":" << timing.dump() << "}" << std::endl;
            } catch (const std::exception & error) {
                // Generation errors cannot retain recurrent/KV state for the next request.
                if (context) { llama_synchronize(context); llama_memory_clear(llama_get_memory(context), true); }
                std::cout << json({{"id", id}, {"error", error.what()}, {"decode_count", request_decodes},
                    {"total_decode_count", total_decode_count}, {"state_cleared_on_error", context != nullptr}}).dump() << std::endl;
            }
        }
    } catch (const std::exception & error) {
        std::cerr << "llama-matched-helper: " << error.what() << std::endl;
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
