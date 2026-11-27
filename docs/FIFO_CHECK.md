# Check order priority across the five book variants

This synthetic trace uses the same price level for two resting sells. Increasing
order 101 from 10 to 12 moves it behind order 102. A market buy of 12 fills
order 102 first and takes two from order 101 at the resting price. The remaining
10 sit in order 101 until it is cancelled.

Run this from the repository root with CMake and a C++20 compiler. The example
uses the engine-only target and saves its source and executable under the
ignored build directory.

```bash
(
  set -euo pipefail
  cmake -S . -B build-fifo-check -DME_BUILD_BENCH=OFF
  cmake --build build-fifo-check --target me --parallel 2
  cat > build-fifo-check/check.cpp <<'CPP'
#include "me/book.hpp"
#include "me/book_v1.hpp"

#include <cassert>
#include <iostream>
#include <utility>
#include <vector>

template <class Book>
void check(const char* name) {
    Book book;
    std::vector<me::Trade> trades;
    constexpr me::Price price = 10000;
    using enum me::Side;

    assert(book.add_limit(101, Sell, price, 10, trades).resting == 10);
    assert(book.add_limit(102, Sell, price, 10, trades).resting == 10);
    assert(book.modify(101, price, 12, trades).resting == 12);
    assert(trades.empty());

    assert(book.add_market(201, Buy, 12, trades).filled == 12);
    assert(trades.size() == 2);
    assert(trades[0].sell_id == 102 && trades[0].price == price && trades[0].qty == 10);
    assert(trades[1].sell_id == 101 && trades[1].price == price && trades[1].qty == 2);
    assert(trades[0].buy_id == 201 && trades[1].buy_id == 201);

    std::vector<std::pair<me::OrderId, me::Quantity>> queue;
    book.for_each_order(Sell, price, [&](me::OrderId id, me::Quantity quantity) {
        queue.emplace_back(id, quantity);
    });
    assert((queue == std::vector<std::pair<me::OrderId, me::Quantity>>{{101, 10}}));
    assert(book.best_ask() == price && book.volume_at(Sell, price) == 10);
    assert(book.order_count() == 1);
    assert(book.cancel(101));
    assert(!book.best_ask() && book.order_count() == 0);
    std::cout << name << ": passed\n";
}

int main() {
    check<me::BookV1>("BookV1");
    check<me::BookMap>("BookMap");
    check<me::BookMapOA>("BookMapOA");
    check<me::BookVec>("BookVec");
    check<me::BookLadder>("BookLadder");
}
CPP
  c++ -std=c++20 -I include build-fifo-check/check.cpp build-fifo-check/libme.a -o build-fifo-check/check
  build-fifo-check/check
)
```

A successful run prints five lines ending in `passed`. The assertions compare the
fills, surviving queue, best ask and final empty book against the hand-worked
trace. This example covers one synthetic priority transition and does not
measure performance or historical feed reconstruction.
