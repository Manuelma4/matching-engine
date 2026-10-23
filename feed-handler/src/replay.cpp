#include "itch/replay.hpp"

#include <algorithm>

namespace itch {

namespace {

class Fnv1a {
public:
    void add(std::uint64_t word) {
        for (int i = 0; i < 8; ++i) {
            h_ ^= (word >> (8 * i)) & 0xFF;
            h_ *= 0x100000001B3ull;
        }
    }
    [[nodiscard]] std::uint64_t value() const { return h_; }

private:
    std::uint64_t h_ = 0xCBF29CE484222325ull;
};

std::string_view trim(std::string_view s) {
    const auto end = s.find_last_not_of(' ');
    return end == std::string_view::npos ? std::string_view{} : s.substr(0, end + 1);
}

}  // namespace

BookBuilder::BookBuilder(const L3Book::Config& cfg)
    : book_(cfg), symbols_(L3Book::kLocates), volume_(L3Book::kLocates, 0) {}

void BookBuilder::on_directory(StockDirectory m) {
    symbols_[m.locate()] = std::string(trim(m.stock()));
    max_locate_ = std::max(max_locate_, m.locate());
}

void BookBuilder::on_add(AddOrder m) {
    if (!m.valid_side()) {
        ++invalid_messages_.invalid_side;
        return;
    }
    ++stats_.adds;
    max_locate_ = std::max(max_locate_, m.locate());
    book_.add(m.locate(), m.ref(), m.side(), m.shares(), m.price());
}

bool BookBuilder::matches_locate(Locate locate, Ref ref) {
    const BookOrder* order = book_.find(ref);
    if (order != nullptr && order->locate != locate) {
        ++invalid_messages_.locate_mismatch;
        return false;
    }
    // Unknown references are left to the L3 book, which counts them exactly once.
    return true;
}

void BookBuilder::on_execute(OrderExecuted m) {
    if (!matches_locate(m.locate(), m.ref())) {
        return;
    }
    ++stats_.executions;
    stats_.executed_shares += m.shares();
    volume_[m.locate()] += m.shares();
    book_.execute(m.ref(), m.shares());
}

void BookBuilder::on_execute_with_price(OrderExecutedWithPrice m) {
    if (!matches_locate(m.locate(), m.ref())) {
        return;
    }
    ++stats_.executions;
    if (m.printable()) {
        stats_.executed_shares += m.shares();
        volume_[m.locate()] += m.shares();
    } else {
        stats_.non_printable_shares += m.shares();
    }
    book_.execute(m.ref(), m.shares());
}

void BookBuilder::on_cancel(OrderCancel m) {
    if (matches_locate(m.locate(), m.ref())) {
        book_.cancel(m.ref(), m.shares());
    }
}

void BookBuilder::on_delete(OrderDelete m) {
    if (matches_locate(m.locate(), m.ref())) {
        book_.remove(m.ref());
    }
}

void BookBuilder::on_replace(OrderReplace m) {
    if (matches_locate(m.locate(), m.old_ref())) {
        book_.replace(m.old_ref(), m.new_ref(), m.shares(), m.price());
    }
}

void BookBuilder::on_trade(Trade m) {
    stats_.trade_shares += m.shares();
    volume_[m.locate()] += m.shares();
}

void BookBuilder::on_cross(CrossTrade m) {
    stats_.cross_shares += m.shares();
    volume_[m.locate()] += m.shares();
}

void BookBuilder::on_broken(BrokenTrade) { ++stats_.broken_trades; }

void BookBuilder::on_system(SystemEvent m) {
    if (m.event() == 'C') {
        stats_.end_of_messages = true;
    }
}

std::string_view BookBuilder::symbol(Locate locate) const { return symbols_[locate]; }

std::uint64_t BookBuilder::book_hash() const {
    Fnv1a hash;
    for (std::uint32_t locate = 0; locate <= max_locate_; ++locate) {
        for (BookSide side : {BookSide::Bid, BookSide::Ask}) {
            book_.visit(static_cast<Locate>(locate), side, [&](Price4 price, Ref ref, Shares shares) {
                hash.add(locate);
                hash.add(static_cast<std::uint64_t>(side));
                hash.add(price);
                hash.add(ref);
                hash.add(shares);
            });
        }
    }
    return hash.value();
}

std::uint64_t BookBuilder::state_hash() const {
    Fnv1a hash;
    hash.add(1);  // checkpoint fingerprint version
    hash.add(book_hash());
    hash.add(book_.order_count());
    hash.add(book_.peak_orders());
    hash.add(max_locate_);
    for (std::size_t locate = 0; locate < symbols_.size(); ++locate) {
        hash.add(symbols_[locate].size());
        for (char c : symbols_[locate]) hash.add(static_cast<unsigned char>(c));
        hash.add(volume_[locate]);
    }
    hash.add(stats_.adds);
    hash.add(stats_.executions);
    hash.add(stats_.executed_shares);
    hash.add(stats_.non_printable_shares);
    hash.add(stats_.trade_shares);
    hash.add(stats_.cross_shares);
    hash.add(stats_.broken_trades);
    hash.add(stats_.end_of_messages);
    hash.add(book_.anomalies().unknown_ref);
    hash.add(book_.anomalies().duplicate_ref);
    hash.add(book_.anomalies().share_underflow);
    hash.add(book_.anomalies().capacity);
    hash.add(invalid_messages_.invalid_side);
    hash.add(invalid_messages_.locate_mismatch);
    return hash.value();
}

}  // namespace itch
