#include "workloads.hpp"

#include <array>
#include <cstdint>
#include <iostream>

int main() {
    // Seed 42, captured before sequencing the draws on Apple Clang. The prefix
    // includes the deep-book steady phase and the flash crash and recovery.
    constexpr std::size_t count = 105'000;
    constexpr std::array<std::uint64_t, bench::kRegimes.size()> expected{
        0x7373e452cb14eb50, 0xdfcc34916016e5b1, 0x5d67e7b449ed1411,
        0xec0210dc0f3bab36, 0x043fa153ef814c6f7,
    };
    for (std::size_t i = 0; i < bench::kRegimes.size(); ++i) {
        const auto regime = bench::kRegimes[i];
        const auto operations = bench::generate(regime, 42, count);
        std::uint64_t fingerprint = 14695981039346656037ULL;
        for (const auto& op : operations) {
            const std::array<std::uint64_t, 5> words{
                static_cast<std::uint64_t>(op.type), static_cast<std::uint64_t>(op.side),
                op.id, static_cast<std::uint64_t>(op.price), op.qty,
            };
            for (const auto word : words) {
                fingerprint = (fingerprint ^ word) * 1099511628211ULL;
            }
        }
        if (operations.size() != count || fingerprint != expected[i]) {
            std::cerr << bench::regime_name(regime) << " workload fingerprint changed\n";
            return 1;
        }
    }
}
