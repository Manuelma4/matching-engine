#include <gtest/gtest.h>

#include "me/order_book.hpp"

using namespace me;

class OrderBookTest : public ::testing::Test {
protected:
    OrderBook book;
    std::vector<Trade> trades;

    ExecutionReport buy(OrderId id, Price price, Quantity qty) {
        return book.add_limit(id, Side::Buy, price, qty, trades);
    }
    ExecutionReport sell(OrderId id, Price price, Quantity qty) {
        return book.add_limit(id, Side::Sell, price, qty, trades);
    }
};

TEST_F(OrderBookTest, EmptyBookHasNoPrices) {
    EXPECT_FALSE(book.best_bid());
    EXPECT_FALSE(book.best_ask());
    EXPECT_EQ(book.order_count(), 0u);
}

TEST_F(OrderBookTest, NonCrossingOrdersRest) {
    buy(1, 100, 10);
    sell(2, 101, 5);
    EXPECT_TRUE(trades.empty());
    EXPECT_EQ(book.best_bid(), 100);
    EXPECT_EQ(book.best_ask(), 101);
    EXPECT_EQ(book.order_count(), 2u);
}

TEST_F(OrderBookTest, FullMatchAtRestingPrice) {
    sell(1, 100, 10);
    auto report = buy(2, 105, 10);

    ASSERT_EQ(trades.size(), 1u);
    EXPECT_EQ(trades[0].price, 100);  // the resting order sets the price
    EXPECT_EQ(trades[0].qty, 10u);
    EXPECT_EQ(trades[0].buy_id, 2u);
    EXPECT_EQ(trades[0].sell_id, 1u);
    EXPECT_EQ(trades[0].aggressor, Side::Buy);
    EXPECT_EQ(report.filled, 10u);
    EXPECT_EQ(report.resting, 0u);
    EXPECT_EQ(book.order_count(), 0u);
}

TEST_F(OrderBookTest, PartialFillRestsRemainder) {
    sell(1, 100, 4);
    auto report = buy(2, 100, 10);

    EXPECT_EQ(report.filled, 4u);
    EXPECT_EQ(report.resting, 6u);
    EXPECT_FALSE(book.best_ask());
    EXPECT_EQ(book.best_bid(), 100);
    EXPECT_EQ(book.volume_at(Side::Buy, 100), 6u);
}

TEST_F(OrderBookTest, SweepsMultipleLevelsBestFirst) {
    sell(1, 102, 5);
    sell(2, 100, 5);
    sell(3, 101, 5);
    auto report = buy(4, 101, 20);

    ASSERT_EQ(trades.size(), 2u);
    EXPECT_EQ(trades[0].price, 100);
    EXPECT_EQ(trades[1].price, 101);
    EXPECT_EQ(report.filled, 10u);
    EXPECT_EQ(report.resting, 10u);
    EXPECT_EQ(book.best_ask(), 102);
    EXPECT_EQ(book.best_bid(), 101);
}

TEST_F(OrderBookTest, TimePriorityWithinLevel) {
    sell(1, 100, 5);
    sell(2, 100, 5);
    sell(3, 100, 5);
    buy(4, 100, 7);

    ASSERT_EQ(trades.size(), 2u);
    EXPECT_EQ(trades[0].sell_id, 1u);
    EXPECT_EQ(trades[0].qty, 5u);
    EXPECT_EQ(trades[1].sell_id, 2u);
    EXPECT_EQ(trades[1].qty, 2u);
    EXPECT_EQ(book.volume_at(Side::Sell, 100), 8u);
}

TEST_F(OrderBookTest, CancelRemovesOrderAndEmptyLevel) {
    buy(1, 100, 10);
    buy(2, 99, 10);
    EXPECT_TRUE(book.cancel(1));
    EXPECT_EQ(book.best_bid(), 99);
    EXPECT_EQ(book.level_count(Side::Buy), 1u);
    EXPECT_FALSE(book.cancel(1));
    EXPECT_FALSE(book.cancel(42));
}

TEST_F(OrderBookTest, CancelKeepsQueuePositionOfOthers) {
    sell(1, 100, 5);
    sell(2, 100, 5);
    sell(3, 100, 5);
    book.cancel(2);
    buy(4, 100, 10);

    ASSERT_EQ(trades.size(), 2u);
    EXPECT_EQ(trades[0].sell_id, 1u);
    EXPECT_EQ(trades[1].sell_id, 3u);
}

TEST_F(OrderBookTest, FilledOrderCannotBeCancelled) {
    sell(1, 100, 5);
    buy(2, 100, 5);
    EXPECT_FALSE(book.cancel(1));
}

TEST_F(OrderBookTest, MarketOrderNeverRests) {
    sell(1, 100, 3);
    auto report = book.add_market(2, Side::Buy, 10, trades);

    EXPECT_EQ(report.filled, 3u);
    EXPECT_EQ(report.cancelled, 7u);
    EXPECT_EQ(report.resting, 0u);
    EXPECT_FALSE(book.best_bid());
}

TEST_F(OrderBookTest, MarketOrderOnEmptyBook) {
    auto report = book.add_market(1, Side::Sell, 10, trades);
    EXPECT_TRUE(report.accepted());
    EXPECT_EQ(report.filled, 0u);
    EXPECT_EQ(report.cancelled, 10u);
}

TEST_F(OrderBookTest, RejectsInvalidOrders) {
    EXPECT_EQ(buy(1, 100, 0).reject, RejectReason::InvalidQuantity);
    EXPECT_EQ(buy(1, 0, 10).reject, RejectReason::InvalidPrice);
    buy(1, 100, 10);
    EXPECT_EQ(sell(1, 101, 10).reject, RejectReason::DuplicateId);
    EXPECT_EQ(book.order_count(), 1u);
}
