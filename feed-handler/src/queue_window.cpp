#include "itch/queue_window.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <unordered_set>
#include <utility>

#include "itch/messages.hpp"
#include "itch/replay.hpp"

namespace itch::queue {
namespace {

[[noreturn]] void reject(std::string_view message) {
    throw std::invalid_argument(std::string(message));
}

std::string_view trim(std::string_view text) {
    const auto end = text.find_last_not_of(' ');
    return end == std::string_view::npos ? std::string_view{} : text.substr(0, end + 1);
}

std::optional<std::string_view> stock_text(Bytes message) {
    std::size_t offset = 0;
    switch (message[0]) {
    case 'R': case 'H': case 'Y': case 'K': case 'J': case 'h': case 'N': case 'O': offset = 11; break;
    case 'L': offset = 15; break;
    case 'A': case 'F': case 'P': offset = 24; break;
    case 'Q': offset = 19; break;
    case 'I': offset = 28; break;
    default: return std::nullopt;
    }
    return trim({reinterpret_cast<const char*>(message.data() + offset), 8});
}

struct Touch {
    std::uint32_t quantity{};
    std::uint32_t opposite_price{};
    std::uint32_t opposite_quantity{};
};

void validate_config(const WindowConfig& config, const L3Book::Config& book_config) {
    if (config.symbol.empty() || config.symbol.size() > 8 ||
        !std::all_of(config.symbol.begin(), config.symbol.end(), [](char c) {
            return (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
                   c == '.' || c == '-' || c == '^' || c == '/';
        })) reject("unsupported symbol: use 1..8 uppercase letters, digits or .-^/");
    if ((config.side != Side::Buy && config.side != Side::Sell) || config.price4 == 0 ||
        config.price4 > kValueLimit || config.start_ns >= config.end_ns ||
        config.end_ns >= (Time{1} << 48)) reject("invalid bounded window configuration");
    if (book_config.max_orders == 0 || book_config.max_levels == 0 ||
        book_config.max_orders > L3Book::Config{}.max_orders ||
        book_config.max_levels > L3Book::Config{}.max_levels)
        reject("window book capacity must be positive and no greater than the default bounded pools");
}

} // namespace

std::string_view name(ProjectionReason value) {
    switch (value) {
    case ProjectionReason::SeedBoundary: return "seed_boundary";
    case ProjectionReason::DisplayedAdd: return "displayed_add";
    case ProjectionReason::DisplayedCancel: return "displayed_cancel";
    case ProjectionReason::DisplayedExecution: return "displayed_execution";
    case ProjectionReason::OppositeQuote: return "opposite_quote";
    case ProjectionReason::NonDisplayedPrint: return "non_displayed_print";
    case ProjectionReason::UnrelatedBrokenTrade: return "unrelated_broken_trade";
    case ProjectionReason::NoRepresentedChange: return "no_represented_change";
    }
    reject("invalid projection reason");
}

struct WindowProjector::Impl {
    WindowResult result;
    BookBuilder builder;
    SeedEligibility current_eligibility;
    std::unordered_set<std::uint64_t> mapped_matches;
    std::array<bool, L3Book::kLocates> directory_seen{};
    SourcePoint previous;
    std::uint64_t consumed = 0;
    unsigned system_stage = 0;
    bool located = false, seeded = false, past_end = false, mwcb_seen = false;
    bool failed = false, finished = false;
    char trading = '?', last_cross = '?';
    Touch projected;

    Impl(WindowConfig config, const L3Book::Config& book_config) : builder(book_config) {
        result.config = std::move(config);
    }

    BookSide side() const { return result.config.side == Side::Buy ? BookSide::Bid : BookSide::Ask; }

    Touch touch() const {
        const auto bid = builder.book().best(result.locate, BookSide::Bid);
        const auto ask = builder.book().best(result.locate, BookSide::Ask);
        if (!bid || !ask || bid->shares == 0 || ask->shares == 0 || bid->price == 0 ||
            ask->price == 0 || bid->price >= ask->price || bid->price > kValueLimit ||
            ask->price > kValueLimit || bid->shares > kValueLimit || ask->shares > kValueLimit)
            reject("window needs two positive, bounded, uncrossed displayed quotes");
        const auto& same = result.config.side == Side::Buy ? *bid : *ask;
        const auto& opposite = result.config.side == Side::Buy ? *ask : *bid;
        if (same.price != result.config.price4)
            reject("window target is no longer the positive same-side best level");
        return {static_cast<std::uint32_t>(same.shares), opposite.price,
                static_cast<std::uint32_t>(opposite.shares)};
    }

    void eligible() const {
        if (!located || system_stage != 3 || trading != 'T' || last_cross != 'O' || mwcb_seen ||
            current_eligibility.operational_action == 'H' ||
            (current_eligibility.retail_interest != '?' && current_eligibility.retail_interest != 'N'))
            reject("window lacks the required regular-session/trading/auction/status prerequisites");
    }

    void clean_book() const {
        const auto& a = builder.book().anomalies();
        const auto& d = builder.invalid_messages();
        if (a.unknown_ref || a.duplicate_ref || a.share_underflow || a.capacity ||
            d.invalid_side || d.locate_mismatch) reject("source reconstruction reports an anomaly");
    }

    void seed() {
        eligible();
        projected = touch();
        result.eligibility = current_eligibility; // future status cannot rewrite the seed
        result.events.push_back({result.config.start_ns, MarketKind::Seed,
                                 projected.quantity, projected.opposite_price});
        result.observations.push_back({previous, ProjectionReason::SeedBoundary, 0, 0, 0,
            projected.quantity, projected.opposite_price, projected.opposite_quantity,
            projected.quantity, projected.opposite_price, projected.opposite_quantity, 1});
        seeded = true;
    }

    void consume(Bytes message, std::uint64_t offset) {
        if (finished || failed) reject("projector is already finished or failed");
        if (offset != consumed || message.size() > 65'535 ||
            message.size() + 2 > std::numeric_limits<std::uint64_t>::max() - consumed)
            reject("non-contiguous or overflowing source frame offsets");
        consumed += message.size() + 2;
        if (message.empty()) {
            if (system_stage != 6 || result.source_end_records != 0)
                reject("invalid BinaryFILE end record");
            ++result.source_end_records;
            return;
        }
        if (result.source_end_records || system_stage == 6)
            reject("source contains a message after end of session");
        const auto expected = kMessageLength[message[0]];
        if (expected == 0 || message.size() != expected) reject("unknown or wrong-length source message");
        const Header header{message.data()};
        if (previous.sequence && header.timestamp() < previous.timestamp_ns)
            reject("source timestamps decrease; never sort observations into a different order");
        const SourcePoint point{++result.source_messages, offset, header.timestamp(),
                                static_cast<std::uint16_t>(message.size()), header.type()};
        ++result.source_type_counts[message[0]];
        if (point.sequence == 1 && (point.type != 'S' || message[11] != 'O'))
            reject("source must begin with system start-of-messages");
        if (!seeded && point.timestamp_ns > result.config.start_ns) seed();
        if (point.timestamp_ns > result.config.end_ns) past_end = true;
        const bool in_window = seeded && !past_end;

        if (point.type == 'R') {
            const StockDirectory directory{message.data()};
            const auto stock = trim(directory.stock());
            if (header.locate() == 0 || stock.empty() || directory_seen[header.locate()])
                reject("source directory has an empty, zero-locate or repeated mapping");
            directory_seen[header.locate()] = true;
            if (stock == result.config.symbol) {
                if (located || directory.authenticity() != 'P')
                    reject("selected symbol must have one unique production directory mapping");
                located = true;
                result.locate = header.locate();
                current_eligibility.directory = point;
            }
        }
        const auto embedded_stock = stock_text(message);
        // K is the specification's stock-named, zero-locate IPO announcement.
        // This first adapter excludes that context instead of mislabelling it as
        // a corrupt symbol/locate mapping or treating it as a regular quote.
        if (point.type == 'K') {
            if (header.locate() != 0) reject("IPO quoting announcement must use stock locate zero");
            if (embedded_stock && *embedded_stock == result.config.symbol && !past_end)
                reject("selected IPO quoting context is unsupported by this regular-window adapter");
        }
        if (point.type != 'K' && ((located && header.locate() == result.locate) ||
            (embedded_stock && *embedded_stock == result.config.symbol))) {
            if (!located || header.locate() != result.locate ||
                (embedded_stock && *embedded_stock != result.config.symbol))
                reject("selected symbol text and locate identity disagree");
        }
        const bool selected = located && header.locate() == result.locate;
        if (point.type == 'S') {
            constexpr std::string_view codes = "OSQMEC";
            if (header.locate() != 0 || message[11] != static_cast<unsigned char>(codes[system_stage]))
                reject("source system events must follow O/S/Q/M/E/C exactly");
            ++system_stage;
            if (message[11] == 'Q') current_eligibility.market_hours = point;
        }
        if (point.type == 'W') {
            if (header.locate() != 0 || message[11] < '1' || message[11] > '3')
                reject("invalid MWCB announcement");
            mwcb_seen = true; // v1 has no market-wide resumption interpretation
        }
        if (selected && point.type == 'H') {
            trading = static_cast<char>(message[19]);
            if (trading != 'H' && trading != 'P' && trading != 'Q' && trading != 'T')
                reject("unknown trading-action state");
            current_eligibility.trading_action = point;
        }
        if (selected && point.type == 'h') {
            const char market = static_cast<char>(message[19]);
            const char action = static_cast<char>(message[20]);
            if ((market != 'Q' && market != 'B' && market != 'X') || (action != 'H' && action != 'T'))
                reject("unknown operational halt fields");
            if (market == 'Q') {
                current_eligibility.operational = point;
                current_eligibility.operational_action = action;
            }
        }
        if (selected && point.type == 'N') {
            const char interest = static_cast<char>(message[19]);
            if (interest != 'N' && interest != 'B' && interest != 'S' && interest != 'A')
                reject("unknown retail-interest flag");
            current_eligibility.retail_interest = interest;
        }
        if (selected && point.type == 'Q') {
            last_cross = static_cast<char>(message[39]);
            if (last_cross == 'O') current_eligibility.opening_cross = point;
        }
        if (point.type == 'B' && mapped_matches.contains(BrokenTrade{message.data()}.match()))
            reject("a projected displayed execution is later broken; accounting correction unsupported");
        if (in_window && (point.type == 'S' || point.type == 'W')) eligible();

        WindowObservation observation;
        observation.source = point;
        observation.reason = ProjectionReason::NoRepresentedChange;
        std::optional<MarketKind> kind;
        std::uint32_t quantity = 0;
        if (selected && in_window) {
            if (result.observations.size() >= kMaxMarketEvents)
                reject("window exceeds 99999 selected messages plus one seed");
            eligible();
            const Touch before = touch();
            if (before.quantity != projected.quantity || before.opposite_price != projected.opposite_price ||
                before.opposite_quantity != projected.opposite_quantity)
                reject("normalised pre-state disagrees with the L3 replica");
            observation.before_quantity = before.quantity;
            observation.before_opposite_price4 = before.opposite_price;
            observation.before_opposite_quantity = before.opposite_quantity;
            if (point.type == 'C' || point.type == 'Q' || point.type == 'I' || point.type == 'K' ||
                point.type == 'J' || point.type == 'O' || point.type == 'R')
                reject("selected window contains unsupported priced execution, auction or directory event");
            if (point.type == 'A' || point.type == 'F') {
                const AddOrder add{message.data()};
                if (!add.valid_side() || add.shares() == 0) reject("invalid selected add");
                observation.reference = add.ref();
                if (add.side() == side() && add.price() == result.config.price4) {
                    kind = MarketKind::Add;
                    quantity = add.shares();
                    observation.reason = ProjectionReason::DisplayedAdd;
                }
            } else if (point.type == 'E' || point.type == 'X' || point.type == 'D' || point.type == 'U') {
                const Ref reference = load_be64(message.data() + 11);
                const BookOrder* found = builder.book().find(reference);
                if (!found || found->locate != result.locate) reject("selected mutation has no matching resting order");
                const BookOrder old = *found; // dispatch may remove/reuse the source slot
                observation.reference = reference;
                const bool at_target = old.side == side() && old.price == result.config.price4;
                if (point.type == 'U') {
                    const OrderReplace replace{message.data()};
                    observation.new_reference = replace.new_ref();
                    if (replace.shares() == 0 ||
                        (old.side == side() && (at_target || replace.price() == result.config.price4)))
                        reject("target-level replacement needs an atomic normalised interface; unsupported in v1");
                } else {
                    const auto amount = point.type == 'D' ? old.shares : load_be32(message.data() + 19);
                    if (amount == 0 || amount > old.shares) reject("invalid selected reduction");
                    if (point.type == 'E') {
                        const auto best = builder.book().best(result.locate, old.side);
                        if (!best || best->price != old.price) reject("selected execution is away from its displayed best price");
                        observation.match = OrderExecuted{message.data()}.match();
                        if (observation.match == 0) reject("zero execution match identity unsupported");
                    }
                    if (at_target) {
                        quantity = amount;
                        kind = point.type == 'E' ? MarketKind::Trade : MarketKind::Cancel;
                        observation.reason = point.type == 'E' ? ProjectionReason::DisplayedExecution
                                                               : ProjectionReason::DisplayedCancel;
                        if (point.type == 'E') {
                            if (!mapped_matches.insert(observation.match).second)
                                reject("projected execution match identity is repeated");
                            result.displayed_executed_shares += amount;
                        }
                    }
                }
            } else if (point.type == 'P') {
                observation.match = Trade{message.data()}.match();
                observation.reason = ProjectionReason::NonDisplayedPrint;
            } else if (point.type == 'B') {
                observation.match = BrokenTrade{message.data()}.match();
                observation.reason = ProjectionReason::UnrelatedBrokenTrade;
            }
        }

        (void)dispatch(message, builder);
        clean_book();
        if (selected && in_window) {
            eligible();
            const Touch after = touch();
            const bool quote_changed = after.opposite_price != projected.opposite_price;
            if (kind && quote_changed) reject("one source event would need an unsupported compound projection");
            if (!kind && quote_changed) {
                kind = MarketKind::Quote;
                observation.reason = ProjectionReason::OppositeQuote;
            }
            if (kind) {
                if (*kind == MarketKind::Add) {
                    if (quantity > kValueLimit - projected.quantity) reject("normalised quantity overflow");
                    projected.quantity += quantity;
                } else if (*kind == MarketKind::Cancel || *kind == MarketKind::Trade) {
                    if (quantity > projected.quantity) reject("normalised reduction exceeds its external state");
                    projected.quantity -= quantity;
                } else projected.opposite_price = after.opposite_price;
                result.events.push_back({point.timestamp_ns, *kind, quantity,
                    *kind == MarketKind::Quote ? after.opposite_price : 0});
                observation.normalised_row = static_cast<std::uint32_t>(result.events.size());
            }
            if (projected.quantity != after.quantity || projected.opposite_price != after.opposite_price)
                reject("normalised post-state disagrees with the L3 replica");
            projected.opposite_quantity = after.opposite_quantity;
            observation.after_quantity = after.quantity;
            observation.after_opposite_price4 = after.opposite_price;
            observation.after_opposite_quantity = after.opposite_quantity;
            result.observations.push_back(observation);
            ++result.reconciled_messages;
            ++result.window_type_counts[message[0]];
        }
        previous = point;
    }
};

WindowProjector::WindowProjector(WindowConfig config, const L3Book::Config& book_config)
{
    validate_config(config, book_config); // reject bad arguments before allocating large pools
    impl_ = std::make_unique<Impl>(std::move(config), book_config);
}
WindowProjector::~WindowProjector() = default;

void WindowProjector::consume(Bytes message, std::uint64_t frame_offset) {
    try { impl_->consume(message, frame_offset); }
    catch (...) { impl_->failed = true; throw; }
}

WindowResult WindowProjector::finish(std::uint64_t input_bytes) {
    if (impl_->failed || impl_->finished) reject("projector is already finished or failed");
    impl_->finished = true;
    if (impl_->consumed != input_bytes || impl_->system_stage != 6 ||
        !impl_->builder.stats().end_of_messages || impl_->builder.book().order_count() != 0 ||
        !impl_->seeded || !impl_->past_end) reject("incomplete source lifecycle, framing or window coverage");
    impl_->clean_book();
    impl_->result.source_bytes = input_bytes;
    impl_->result.final_quantity = impl_->projected.quantity;
    impl_->result.final_opposite_price4 = impl_->projected.opposite_price;
    impl_->result.final_opposite_quantity = impl_->projected.opposite_quantity;
    return std::move(impl_->result);
}

} // namespace itch::queue
