#include "me/book.hpp"
#include "me/book_v1.hpp"

#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {

using namespace me;

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <class BookType>
void check_level_volume() {
    constexpr auto cap = std::numeric_limits<Quantity>::max();
    constexpr Price price = 100;
    BookType book(BookConfig{.max_orders = 8, .band_log2 = 8});
    std::vector<Trade> trades;

    require(book.add_limit(1, Side::Buy, price, cap, trades).resting == cap, "large order did not rest");
    require(book.add_limit(2, Side::Buy, price, 3, trades).resting == 3, "second order did not rest");
    require(book.volume_at(Side::Buy, price) == cap, "level volume wrapped instead of saturating");

    require(book.add_market(3, Side::Sell, 4, trades).filled == 4, "market order did not fill");
    require(trades.size() == 1 && trades.front().buy_id == 1 && trades.front().qty == 4, "FIFO changed");
    require(book.volume_at(Side::Buy, price) == cap - 1, "partial fill did not restore exact volume");

    require(book.modify(2, price, cap, trades).resting == cap, "size increase did not rest");
    require(book.add_limit(4, Side::Buy, price, cap, trades).resting == cap, "third large order did not rest");
    require(book.volume_at(Side::Buy, price) == cap, "second carry was lost");
    require(book.cancel(4), "cancel failed");
    require(book.volume_at(Side::Buy, price) == cap, "cancel cleared saturation too soon");
    require(book.modify(2, price, 1, trades).resting == 1, "size decrease did not rest");
    require(book.volume_at(Side::Buy, price) == cap - 3, "size decrease did not restore exact volume");

    require(book.modify(2, price, cap, trades).resting == cap, "second size increase did not rest");
    require(book.modify(2, price + 1, cap, trades).resting == cap, "repriced order did not rest");
    require(book.volume_at(Side::Buy, price) == cap - 4, "old level kept repriced volume");
    require(book.volume_at(Side::Buy, price + 1) == cap, "new level lost repriced volume");
    require(book.cancel(1) && book.cancel(2), "final cancels failed");
    require(book.volume_at(Side::Buy, price) == 0, "empty level retained volume");
    require(book.add_limit(5, Side::Buy, price, 7, trades).resting == 7, "reinsert failed");
    require(book.volume_at(Side::Buy, price) == 7, "reused level retained old volume");
}

}  // namespace

int main() {
    const struct {
        const char* name;
        void (*check)();
    } variants[] = {
        {"BookV1", check_level_volume<BookV1>},
        {"BookMap", check_level_volume<BookMap>},
        {"BookMapOA", check_level_volume<BookMapOA>},
        {"BookVec", check_level_volume<BookVec>},
        {"BookLadder", check_level_volume<BookLadder>},
    };
    int failures = 0;
    for (const auto& variant : variants) {
        try {
            variant.check();
        } catch (const std::runtime_error& error) {
            std::cerr << variant.name << ": " << error.what() << '\n';
            ++failures;
        }
    }
    if (failures == 0) {
        std::cout << "Level volume checks passed for all five variants\n";
    }
    return failures == 0 ? 0 : 1;
}
