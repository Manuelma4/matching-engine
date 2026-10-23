// Direct C++ API example: literal synthetic inputs, unchanged queue-model kernel.
#include "itch/queue_sim.hpp"

#include <array>
#include <exception>
#include <iostream>
#include <optional>
#include <string_view>

namespace {

namespace queue = itch::queue;

constexpr std::array<queue::MarketEvent, 4> events{{
    {0, queue::MarketKind::Seed, 100, 10010},
    {20, queue::MarketKind::Add, 40, 0},
    {30, queue::MarketKind::Cancel, 50, 0},
    {40, queue::MarketKind::Trade, 80, 0},
}};

void account(std::string_view label, const queue::Account& value) {
    std::cout << label << ",filled=" << value.filled << ",position=" << value.position
              << ",cash4=" << value.cash4 << ",fees4=" << value.fees4 << '\n';
}

void scenario(queue::CancelModel model, queue::Time horizon) {
    const queue::Config config{
        .side = queue::Side::Buy,
        .cancel_model = model,
        .price4 = 10000,
        .quantity = 10,
        .fee4 = 0,
        .decision_ns = 10,
        .cancel_ns = std::nullopt,
        .horizon_ns = horizon,
        .feed_delay_ns = 0,
        .order_delay_ns = 0,
        .response_delay_ns = 5,
    };
    const auto result = queue::simulate(events, config);

    std::cout << "\nscenario=" << queue::name(model) << ",horizon_ns=" << horizon
              << ",side=" << queue::name(config.side) << ",price4=" << config.price4
              << ",quantity=" << config.quantity << ",fee4=" << config.fee4
              << ",decision_ns=" << config.decision_ns << ",cancel_ns=none"
              << ",feed_delay_ns=" << config.feed_delay_ns
              << ",order_delay_ns=" << config.order_delay_ns
              << ",response_delay_ns=" << config.response_delay_ns << '\n'
              << "time_ns,phase,event,external_qty,observed_qty,ahead,remaining,"
                 "known_remaining,exchange_state,local_state,exchange_filled,local_filled\n";
    for (const auto& row : result.trace) {
        std::cout << row.time_ns << ',' << row.phase << ',' << row.event << ','
                  << row.external_quantity << ',';
        if (row.observed) std::cout << row.observed_quantity;
        else std::cout << "unknown";
        std::cout << ',' << row.ahead << ',' << row.remaining << ',' << row.known_remaining
                  << ',' << queue::name(row.exchange_state) << ',' << queue::name(row.local_state)
                  << ',' << row.exchange.filled << ',' << row.local.filled << '\n';
    }
    std::cout << "final,exchange=" << queue::name(result.exchange_state)
              << ",local=" << queue::name(result.local_state)
              << ",ahead=" << result.ahead << ",remaining=" << result.remaining
              << ",known_remaining=" << result.known_remaining
              << ",pending_events=" << result.pending_events << '\n';
    account("exchange_account", result.exchange);
    account("local_account", result.local);
    std::cout << "local_marked_equity_twice4=";
    if (result.local_marked_equity_twice4) std::cout << *result.local_marked_equity_twice4;
    else std::cout << "unknown";
    std::cout << '\n';
}

} // namespace

int main(int argc, char**) {
    if (argc != 1) {
        std::cerr << "Usage: itch_queue_demo (no arguments; synthetic inputs are compiled in)\n";
        return 1;
    }
    try {
        std::cout.exceptions(std::ios::badbit | std::ios::failbit);
        std::cout << "Synthetic single-level shadow queue: no historical fill or priority claim.\n"
                     "Times are nanoseconds; prices and cash use Price(4).\n"
                     "External events exclude our hypothetical order and remain unchanged.\n\n"
                     "timestamp_ns,kind,quantity,opposite_price4\n";
        for (const auto& event : events)
            std::cout << event.timestamp_ns << ',' << queue::name(event.kind) << ','
                      << event.quantity << ',' << event.opposite_price4 << '\n';
        scenario(queue::CancelModel::Optimistic, 45);
        scenario(queue::CancelModel::Conservative, 45);
        scenario(queue::CancelModel::Optimistic, 44);
        std::cout.flush();
    } catch (const std::exception& error) {
        std::cerr << "itch_queue_demo: " << error.what() << '\n';
        return 1;
    }
}
