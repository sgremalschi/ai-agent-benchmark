import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from problems.inventory import Inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.inventory = Inventory()
        self.inventory.add_stock("apple", 10)
        self.inventory.add_stock("pear", 7)

    def run_concurrently(self, operation, workers=16):
        barrier = Barrier(workers)

        def run(index):
            barrier.wait(timeout=10)
            return operation(index)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(run, range(workers)))

    def test_unknown_sku_has_zero_stock(self):
        self.assertEqual(self.inventory.available("unknown"), 0)

    def test_add_stock_replaces_existing_quantity(self):
        self.inventory.add_stock("apple", 3)
        self.assertEqual(self.inventory.available("apple"), 3)

    def test_add_zero_stock(self):
        self.inventory.add_stock("apple", 0)
        self.assertEqual(self.inventory.available("apple"), 0)

    def test_invalid_stock_quantities_leave_stock_unchanged(self):
        for quantity in (-1, -1.5, 1.5, 2.0, "2", None, True, False):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    self.inventory.add_stock("apple", quantity)
                self.assertEqual(self.inventory.available("apple"), 10)
                self.assertEqual(self.inventory.available("pear"), 7)

    def test_invalid_stock_does_not_create_available_inventory(self):
        with self.assertRaises(ValueError):
            self.inventory.add_stock("unknown", -1)
        self.assertEqual(self.inventory.available("unknown"), 0)
        self.assertFalse(self.inventory.reserve("r", "unknown", 1))

    def test_reservation_deducts_quantity_once(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))
        self.assertEqual(self.inventory.available("apple"), 6)

    def test_can_reserve_exactly_available_stock(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 10))
        self.assertEqual(self.inventory.available("apple"), 0)
        self.assertFalse(self.inventory.reserve("next", "apple", 1))

    def test_insufficient_stock_does_not_create_reservation(self):
        self.assertFalse(self.inventory.reserve("r", "apple", 11))
        self.assertEqual(self.inventory.available("apple"), 10)
        self.assertFalse(self.inventory.release("r"))
        self.assertFalse(self.inventory.fulfill("r"))
        self.assertTrue(self.inventory.reserve("r", "apple", 2))

    def test_unknown_sku_cannot_be_reserved(self):
        self.assertFalse(self.inventory.reserve("r", "unknown", 1))
        self.assertEqual(self.inventory.available("unknown"), 0)
        self.assertFalse(self.inventory.release("r"))

    def test_invalid_reservation_quantities_leave_state_unchanged(self):
        for quantity in (-1, 0, -1.5, 1.5, 2.0, "2", None, True, False):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    self.inventory.reserve("invalid", "apple", quantity)
                self.assertEqual(self.inventory.available("apple"), 10)
                self.assertFalse(self.inventory.release("invalid"))
                self.assertFalse(self.inventory.fulfill("invalid"))
        self.assertTrue(self.inventory.reserve("invalid", "apple", 1))

    def test_zero_reservation_for_unknown_sku_is_invalid(self):
        with self.assertRaises(ValueError):
            self.inventory.reserve("r", "unknown", 0)
        self.assertEqual(self.inventory.available("unknown"), 0)

    def test_duplicate_id_preserves_original_reservation(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 3))
        with self.assertRaises(ValueError):
            self.inventory.reserve("r", "apple", 2)
        self.assertEqual(self.inventory.available("apple"), 7)
        self.assertTrue(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 10)

    def test_duplicate_id_on_another_sku_changes_neither_sku(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 3))
        with self.assertRaises(ValueError):
            self.inventory.reserve("r", "pear", 2)
        self.assertEqual(self.inventory.available("apple"), 7)
        self.assertEqual(self.inventory.available("pear"), 7)
        self.assertTrue(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 10)
        self.assertEqual(self.inventory.available("pear"), 7)

    def test_duplicate_id_raises_even_when_stock_is_insufficient(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 3))
        with self.assertRaises(ValueError):
            self.inventory.reserve("r", "unknown", 1)
        self.assertEqual(self.inventory.available("apple"), 7)
        self.assertTrue(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 10)

    def test_invalid_request_does_not_replace_active_reservation(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 3))
        with self.assertRaises(ValueError):
            self.inventory.reserve("r", "pear", -1)
        self.assertEqual(self.inventory.available("apple"), 7)
        self.assertEqual(self.inventory.available("pear"), 7)
        self.assertTrue(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 10)

    def test_release_restores_stock_exactly_once(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))
        self.assertTrue(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 10)
        self.assertFalse(self.inventory.release("r"))
        self.assertFalse(self.inventory.fulfill("r"))
        self.assertEqual(self.inventory.available("apple"), 10)

    def test_fulfill_consumes_reservation_without_restoring_stock(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))
        self.assertTrue(self.inventory.fulfill("r"))
        self.assertFalse(self.inventory.fulfill("r"))
        self.assertFalse(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 6)

    def test_unknown_reservation_operations_return_false(self):
        self.assertFalse(self.inventory.release("missing"))
        self.assertFalse(self.inventory.fulfill("missing"))
        self.assertEqual(self.inventory.available("apple"), 10)

    def test_id_can_be_reused_after_release(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))
        self.assertTrue(self.inventory.release("r"))
        self.assertTrue(self.inventory.reserve("r", "pear", 2))
        self.assertTrue(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 10)
        self.assertEqual(self.inventory.available("pear"), 7)

    def test_id_can_be_reused_after_fulfillment(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))
        self.assertTrue(self.inventory.fulfill("r"))
        self.assertTrue(self.inventory.reserve("r", "pear", 2))
        self.assertTrue(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 6)
        self.assertEqual(self.inventory.available("pear"), 7)

    def test_operations_on_one_sku_leave_other_sku_unchanged(self):
        self.assertTrue(self.inventory.reserve("pear-r", "pear", 3))
        self.inventory.add_stock("apple", 20)
        self.assertTrue(self.inventory.reserve("apple-r", "apple", 5))
        self.assertTrue(self.inventory.release("apple-r"))
        self.assertTrue(self.inventory.reserve("apple-r", "apple", 2))
        self.assertTrue(self.inventory.fulfill("apple-r"))
        self.assertEqual(self.inventory.available("pear"), 4)
        self.assertTrue(self.inventory.release("pear-r"))
        self.assertEqual(self.inventory.available("pear"), 7)

    def test_replacement_stock_and_active_reservation_are_independent(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))
        self.inventory.add_stock("apple", 2)
        self.assertEqual(self.inventory.available("apple"), 2)
        self.assertTrue(self.inventory.release("r"))
        self.assertEqual(self.inventory.available("apple"), 6)

    def test_multiple_reservations_have_independent_lifecycles(self):
        self.assertTrue(self.inventory.reserve("a", "apple", 3))
        self.assertTrue(self.inventory.reserve("b", "apple", 4))
        self.assertTrue(self.inventory.release("a"))
        self.assertTrue(self.inventory.fulfill("b"))
        self.assertEqual(self.inventory.available("apple"), 6)

    def test_concurrent_reservations_never_oversell(self):
        for round_number in range(10):
            with self.subTest(round_number=round_number):
                self.inventory.add_stock("apple", 11)
                results = self.run_concurrently(
                    lambda i: self.inventory.reserve(f"{round_number}-{i}", "apple", 2)
                )
                self.assertEqual(sum(results), 5)
                self.assertEqual(self.inventory.available("apple"), 1)
                for i, reserved in enumerate(results):
                    self.assertEqual(self.inventory.release(f"{round_number}-{i}"), reserved)
                self.assertEqual(self.inventory.available("apple"), 11)

    def test_concurrent_duplicate_ids_have_one_winner(self):
        self.inventory.add_stock("apple", 100)

        def reserve(_):
            try:
                return self.inventory.reserve("shared", "apple", 2)
            except ValueError:
                return "duplicate"

        results = self.run_concurrently(reserve)
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count("duplicate"), 15)
        self.assertEqual(self.inventory.available("apple"), 98)
        self.assertTrue(self.inventory.release("shared"))
        self.assertEqual(self.inventory.available("apple"), 100)

    def test_concurrent_releases_restore_stock_once(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))
        results = self.run_concurrently(lambda _: self.inventory.release("r"))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.inventory.available("apple"), 10)

    def test_concurrent_fulfillments_consume_reservation_once(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))
        results = self.run_concurrently(lambda _: self.inventory.fulfill("r"))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.inventory.available("apple"), 6)
        self.assertFalse(self.inventory.release("r"))

    def test_concurrent_release_and_fulfill_have_one_winner(self):
        self.assertTrue(self.inventory.reserve("r", "apple", 4))

        def finish(index):
            if index % 2:
                return "release", self.inventory.release("r")
            return "fulfill", self.inventory.fulfill("r")

        results = self.run_concurrently(finish)
        winners = [operation for operation, succeeded in results if succeeded]
        self.assertEqual(len(winners), 1)
        expected_stock = 10 if winners[0] == "release" else 6
        self.assertEqual(self.inventory.available("apple"), expected_stock)
        self.assertFalse(self.inventory.release("r"))
        self.assertFalse(self.inventory.fulfill("r"))
