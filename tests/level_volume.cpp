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

template <class BookType>
void check_same_price_priority() {
    constexpr Price price = 100;
    BookType book(BookConfig{.max_orders = 8, .band_log2 = 8});
    std::vector<Trade> trades;

    require(book.add_limit(1, Side::Buy, price, 7, trades).resting == 7, "first order did not rest");
    require(book.add_limit(2, Side::Buy, price, 5, trades).resting == 5, "second order did not rest");
    require(book.add_limit(3, Side::Buy, price, 4, trades).resting == 4, "third order did not rest");

    require(book.modify(1, price, 4, trades).resting == 4, "size decrease did not rest");
    require(book.modify(1, price, 4, trades).resting == 4, "unchanged order did not rest");
    require(book.modify(2, price, 6, trades).resting == 6, "size increase did not rest");
    require(trades.empty(), "same-price modifications unexpectedly traded");
    require(book.volume_at(Side::Buy, price) == 14, "unexpected level volume after modifications");

    // Order 1 retains its place. Order 2 moves behind order 3.
    require(book.add_market(4, Side::Sell, 10, trades).filled == 10, "market order did not fill");
    require(trades.size() == 3, "unexpected number of trades");
    require(trades[0].buy_id == 1 && trades[0].qty == 4, "order 1 lost priority");
    require(trades[1].buy_id == 3 && trades[1].qty == 4, "order 2 did not move behind order 3");
    require(trades[2].buy_id == 2 && trades[2].qty == 2, "order 2 did not partially fill");
    require(book.order_count() == 1 && book.best_bid() == price &&
            book.volume_at(Side::Buy, price) == 4, "unexpected resting book after fills");
    require(book.cancel(2), "remaining order did not cancel");
    require(book.order_count() == 0 && !book.best_bid() &&
            book.volume_at(Side::Buy, price) == 0, "cancel did not clear the level");
}

template <class BookType>
void check_level() {
    check_level_volume<BookType>();
    check_same_price_priority<BookType>();
}

}  // namespace

int main() {
    const struct {
        const char* name;
        void (*check)();
    } variants[] = {
        {"BookV1", check_level<BookV1>},
        {"BookMap", check_level<BookMap>},
        {"BookMapOA", check_level<BookMapOA>},
        {"BookVec", check_level<BookVec>},
        {"BookLadder", check_level<BookLadder>},
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
        std::cout << "Level volume and FIFO checks passed for all five variants\n";
    }
    return failures == 0 ? 0 : 1;
}
