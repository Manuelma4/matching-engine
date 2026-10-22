#pragma once

#include <cstdint>

namespace bench {

// xoshiro256** seeded through splitmix64. Unlike std::uniform_int_distribution, whose
// algorithm is implementation-defined, this gives the same stream on every standard
// library, so a (regime, seed) pair names the same workload everywhere.
class Rng {
public:
    explicit Rng(std::uint64_t seed) {
        for (auto& word : s_) {
            seed += 0x9E3779B97F4A7C15ull;
            std::uint64_t z = seed;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
            word = z ^ (z >> 31);
        }
    }

    std::uint64_t next() {
        const std::uint64_t result = rotl(s_[1] * 5, 7) * 9;
        const std::uint64_t t = s_[1] << 17;
        s_[2] ^= s_[0];
        s_[3] ^= s_[1];
        s_[1] ^= s_[2];
        s_[0] ^= s_[3];
        s_[2] ^= t;
        s_[3] = rotl(s_[3], 45);
        return result;
    }

    // Uniform in [0, n). The modulo bias is below 2^-40 for the small n used here.
    std::uint64_t below(std::uint64_t n) { return next() % n; }

    // Uniform in [lo, hi].
    std::int64_t between(std::int64_t lo, std::int64_t hi) {
        return lo + static_cast<std::int64_t>(below(static_cast<std::uint64_t>(hi - lo) + 1));
    }

    bool percent(std::uint64_t p) { return below(100) < p; }

private:
    static std::uint64_t rotl(std::uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }

    std::uint64_t s_[4]{};
};

}  // namespace bench
